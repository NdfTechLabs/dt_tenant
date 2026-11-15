import frappe


PROTECTED_ROLES = {"System Manager", "Tenant Manager"}
DESK_ROLES = {"All", "Desk User", "Tenant Manager"}
ALLOWED_SYSTEM_MODULES = {"Desk", "Dt Tenant"}
RESTRICTED_TENANT_ROLES = {"Tenant Manager", "Tenant User"}
RESTRICTED_TENANT_MODULES = {"Desk", "Dt Tenant"}

SYNCING_STATES = {"active", "grace"}

# ---------------------------------------------------------------------
# RESTRICTION STATE
#
# What a restriction changed is recorded in Tenant Settings so that lifting it
# undoes exactly that, and survives cache flushes and restarts:
#   disabled_users : users this app disabled
#   roles          : {user: [system roles held before restriction]}
#   tenant_roles   : {user: [Tenant Roles rows removed]}
#   tenant_modules : {user: [Tenant Modules rows removed]}
# ---------------------------------------------------------------------

STATE_FIELD = "restriction_state"
LEGACY_CACHE_KEY = "tenant_roles_backup:{user}"


def _empty_state():
    return {"disabled_users": [], "roles": {}, "tenant_roles": {}, "tenant_modules": {}}


def _load_state():
    raw = frappe.db.get_single_value("Tenant Settings", STATE_FIELD)
    state = _empty_state()
    if raw:
        state.update(frappe.parse_json(raw) or {})
    return state


def _save_state(state):
    has_content = any(state.get(key) for key in _empty_state())
    frappe.db.set_single_value(
        "Tenant Settings",
        STATE_FIELD,
        frappe.as_json(state) if has_content else None,
        update_modified=False,
    )


def _restrict_system_modules(user):

    modules = frappe.get_all(
        "Module Def",
        pluck="name"
    )

    for module in modules:

        if module in ALLOWED_SYSTEM_MODULES:
            continue

        frappe.db.delete(
            "User Permission",
            {
                "user": user,
                "allow": "Module Def",
                "for_value": module
            }
        )


def _restrict_tenant_manager(user, roles, state):

    tenant_roles = frappe.get_all(
        "Tenant User Role",
        filters={"parent": user, "parenttype": "User"},
        pluck="role"
    )
    tenant_modules = frappe.get_all(
        "Tenant Allowed Module",
        filters={"parent": user, "parenttype": "User"},
        pluck="module"
    )

    # Record the pre-restriction state once. A second pass over an already
    # restricted site must not replace it with the stripped-down state.
    if user not in state["roles"]:
        state["roles"][user] = sorted(roles)
        state["tenant_roles"][user] = [r for r in tenant_roles if r not in RESTRICTED_TENANT_ROLES]
        state["tenant_modules"][user] = [m for m in tenant_modules if m not in RESTRICTED_TENANT_MODULES]

    # keep minimal desk roles
    for role in roles:
        if role not in DESK_ROLES:
            frappe.db.delete(
                "Has Role",
                {"parent": user, "parenttype": "User", "role": role}
            )

    _restrict_system_modules(user)

    for role in tenant_roles:
        if role not in RESTRICTED_TENANT_ROLES:
            frappe.db.delete(
                "Tenant User Role",
                {"parent": user, "parenttype": "User", "role": role}
            )

    for module in tenant_modules:
        if module not in RESTRICTED_TENANT_MODULES:
            frappe.db.delete(
                "Tenant Allowed Module",
                {"parent": user, "parenttype": "User", "module": module}
            )

    frappe.clear_cache(user=user)


def _disable_non_admin_users():

    state = _load_state()

    users = frappe.get_all(
        "User",
        filters={"enabled": 1, "name": ["not in", ["Administrator", "Guest"]]},
        pluck="name"
    )

    for user in users:

        roles = set(frappe.get_roles(user))

        # System Manager untouched
        if "System Manager" in roles:
            continue

        if "Tenant Manager" in roles:
            _restrict_tenant_manager(user, roles, state)
            continue

        # all other users disabled
        frappe.db.set_value("User", user, "enabled", 0)
        if user not in state["disabled_users"]:
            state["disabled_users"].append(user)

    _save_state(state)


def _legacy_role_backups(state):
    """Role backups written to the cache by releases that kept them only there."""
    backups = {}
    tenant_managers = frappe.get_all(
        "Has Role",
        filters={"role": "Tenant Manager", "parenttype": "User"},
        pluck="parent"
    )
    for user in tenant_managers:
        if user in state["roles"]:
            continue
        saved = frappe.cache().get_value(LEGACY_CACHE_KEY.format(user=user))
        if saved:
            backups[user] = list(saved)
    return backups


def _restore_tenant_manager(user, saved_roles, state, allowed_roles):

    if not frappe.db.exists("User", user):
        return

    doc = frappe.get_doc("User", user)

    have_tenant_roles = {row.role for row in doc.get("custom_tenant_roles") or []}
    for role in state["tenant_roles"].get(user, []):
        if role not in have_tenant_roles and frappe.db.exists("Tenant Roles", role):
            doc.append("custom_tenant_roles", {"role": role})

    have_tenant_modules = {row.module for row in doc.get("custom_tenant_allowed_modules") or []}
    for module in state["tenant_modules"].get(user, []):
        if module not in have_tenant_modules and frappe.db.exists("Tenant Modules", module):
            doc.append("custom_tenant_allowed_modules", {"module": module})

    have_roles = {row.role for row in doc.get("roles") or []}
    for role in saved_roles:
        if role in allowed_roles and role not in have_roles and frappe.db.exists("Role", role):
            doc.append("roles", {"role": role})

    # The User before_save hook derives the final system roles from the
    # restored tenant assignments.
    doc.save(ignore_permissions=True)


def _lift_restriction(caps):
    """Undo what a previous restriction recorded. A no-op on a site that was never restricted."""

    state = _load_state()
    allowed_roles = set(caps.get("allowed_roles", []))

    for user in state["disabled_users"]:
        if frappe.db.exists("User", user):
            frappe.db.set_value("User", user, "enabled", 1)

    role_backups = dict(state["roles"])
    legacy = _legacy_role_backups(state)
    role_backups.update(legacy)

    for user, saved_roles in role_backups.items():
        _restore_tenant_manager(user, saved_roles, state, allowed_roles)

    for user in legacy:
        frappe.cache().delete_value(LEGACY_CACHE_KEY.format(user=user))

    _save_state(_empty_state())


def enforce_lifecycle(caps):
    status = caps.get("subscription_status")

    if status in ("Unpaid", "Completed"):
        # Scheduled sync stays enabled: it is what notices a later payment.
        _disable_non_admin_users()
        return "restricted"

    if status == "Grace Period":
        # still allow access but show banner in UI
        _lift_restriction(caps)
        return "grace"

    if status in ("Active", "Trialing", "Cancelled"):
        _lift_restriction(caps)
        return "active"

    return "unknown"
