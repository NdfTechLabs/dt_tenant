# dt_tenant — Tenant Capabilities and Self-Service

The customer-site companion to `dt_master`, published by **NDF Technology Labs Solutions LTD**.

`dt_tenant` connects a Frappe/ERPNext site to its management site for subscription capabilities, role/module synchronization, extension management, and billing self-service. Infrastructure provisioning and billing execution remain in `dt_master`.

## Features

- **Master connection:** authenticated calls to the management site, capability snapshots, and synchronization audit logs.
- **Permission synchronization:** tenant roles, modules, and role profiles; User hooks assign roles and synchronize permissions.
- **Scheduled capability refresh:** a cron hook runs every six hours. It requires explicit enablement and API credentials, and applies a cooldown after recent failures.
- **Subscription lifecycle handling:** capability synchronization applies the subscription state, including restricting non-administrator users for `Unpaid` or `Completed` subscriptions.
- **Subscription self-service:** the Tenant Subscription page and APIs expose available plans, billing history, invoice download, plan changes, gateways, payment methods, and invoice payment through the master.
- **Add-ons:** marketplace browsing and install/upgrade/uninstall requests sent to the management site, with realtime update support.

## Requirements

- A compatible Frappe/ERPNext bench; both apps are declared in `required_apps`.
- `pyproject.toml` declares Python **3.10 or later**. Use the runtime required by your chosen Frappe release; this minimum alone does not establish release compatibility.
- A reachable management site running `dt_master`, with a **Tenant Site** record matching this site's effective FQDN and a configured customer/subscription/capability profile.
- Management-site API credentials with access to the required APIs, and a correctly configured site URL.
- Working scheduler/background workers for scheduled synchronization and asynchronous workflows.
- Payment integrations configured on the management site for billing actions. The hooks also advertise **Flutterwave Settings**, but do not install the gateway app.

## Installation

Install Frappe and ERPNext first. From the tenant bench directory:

```bash
bench get-app https://github.com/Dhana-Developers/dt_tenant.git
bench --site <tenant-site> install-app dt_tenant
bench --site <tenant-site> migrate
bench build --app dt_tenant
bench --site <tenant-site> clear-cache
```

Choose an app branch compatible with your deployment. Install `dt_master` on the separate management site, not merely on this tenant bench as a substitute for configuring the connection.

## Configuration

1. Register the tenant FQDN and its customer/subscription in `dt_master`. Configure the subscription's allowed roles/modules on the master.
2. Set **Tenant Settings** → `master_url`, `api_key`, and `api_secret` to the management URL and credentials. Protect access to these settings; never put credentials in documentation or source control.
3. Confirm the tenant's effective site URL resolves to the FQDN registered on the master. Capability requests derive the tenant identity from that URL.
4. Review the lifecycle and permission effects below, then run an initial synchronization on a test site:

   ```bash
   bench --site <tenant-site> execute dt_tenant.controllers.capability_sync.resync_capabilities
   ```

5. Inspect **Capability Sync Log** and the settings snapshot. Enable `enable_capability_sync` only after the connection and returned capabilities are correct.
6. Use the **Tenant Subscription** and **Add Ons** Desk pages after configuring their corresponding master-side services.

## Permission and lifecycle cautions

Synchronization is not read-only: it replaces synchronized users' roles and blocked modules, removes obsolete tenant role/module records and references, and preserves specific built-in roles/modules defined in the controller. `Administrator` is excluded from the main user-application loop. Back up and test the permission model before enabling synchronization for existing users.

The current lifecycle code treats `Active`, `Trialing`, and `Cancelled` as active; `Grace Period` has a separate path; `Unpaid` and `Completed` restrict users and disable automatic synchronization. After a restriction, do not assume the disabled scheduler will detect a later payment automatically—review the state and trigger synchronization/re-enable it as appropriate.

Lifecycle enforcement is invoked during capability synchronization. The presence of `security/subscription_guard.py` does not mean a global per-request subscription guard is registered in `hooks.py`.

## Source map

| Path | Purpose |
| --- | --- |
| `dt_tenant/api/` | Master-facing settings, marketplace, subscription, and system endpoints |
| `dt_tenant/controllers/` | Capability fetching/synchronization, lifecycle handling, user permissions, and audit logging |
| `dt_tenant/dt_tenant/doctype/` | Tenant settings, role/module overlays, profiles, and sync logs |
| `dt_tenant/dt_tenant/page/` | Add-ons and subscription Desk interfaces |
| `dt_tenant/fixtures/` | App-owned User custom fields |
| `dt_tenant/hooks.py` | User events, six-hour scheduler, fixtures, and gateway-settings registration |

## Development

From this repository:

```bash
pre-commit install
pre-commit run --all-files
```

Configured checks include Ruff, ESLint, Prettier, and file-validation hooks. Workflow definitions are in `.github/workflows/`.

## License

AGPL-3.0. See [`license.txt`](license.txt).
