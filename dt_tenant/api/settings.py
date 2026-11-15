import frappe

# Only these fields may be set remotely. Everything else on Tenant Settings
# (capability snapshot, restriction state, sync timestamps) is derived state.
CONFIGURABLE_FIELDS = {"master_url", "api_key", "api_secret", "enable_capability_sync"}


@frappe.whitelist(methods=["POST"])
def configure(**kwargs):
    frappe.only_for("System Manager")

    values = {k: v for k, v in kwargs.items() if k in CONFIGURABLE_FIELDS}
    if not values:
        frappe.throw("No configurable Tenant Settings fields supplied")

    settings = frappe.get_single("Tenant Settings")
    for fieldname, value in values.items():
        settings.set(fieldname, value)
    settings.save(ignore_permissions=True)

    return {"updated": sorted(values)}
