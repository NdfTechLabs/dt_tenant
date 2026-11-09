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


---

# DT Master and NDF integration

## M4.0 — Agreed architecture

**Status: Completed (2026-11-09).**

DT Tenant is the tenant-facing companion to DT Master. The M4 architecture preserves that boundary:

- DT Tenant provides marketplace and subscription self-service to tenant users.
- DT Tenant submits application installation, upgrade and removal requests to DT Master through authenticated APIs.
- DT Master owns the App Installation Request record, validates the tenant/site and entitlement, determines whether a Bench rebuild is needed, and owns orchestration status.
- DT Tenant displays or receives request progress; it does not provision Bench Environments or operate Docker.
- Tenant Installed App remains a site-level inventory. It records what is installed on this particular site, not everything available in the shared Bench.
- Bench Environment Application is the separate Bench-level inventory owned by DT Master.
- A Tenant Site belongs to one Bench Environment. Infrastructure Node owns infrastructure and may host multiple Bench Environments.

NDF Frappe Docker supplies immutable images and deployment artifacts to DT Master. DT Tenant does not call NDF directly.

## M4.1 — Integration contract and architecture

**Status: In progress.**  
**Implementation status: Not started under M4.1 approval.**

DT Tenant's M4.1 responsibilities are to define and document:

1. The authenticated request contract sent to DT Master for app installation, upgrade and removal.
2. Request identifiers and the status information returned to the tenant UI.
3. How subscription entitlements and marketplace approvals are presented to DT Master for authoritative validation.
4. How asynchronous progress and terminal failures are communicated back to the tenant.
5. How retries and duplicate submissions are handled without creating duplicate operations.
6. Which tenant-side records remain authoritative and which status fields are synchronized from DT Master.

### Ownership rules

- DT Tenant remains responsible for customer-facing self-service and tenant-local access control.
- DT Master remains authoritative for infrastructure, Bench Environment, deployment candidates, builds, deployment execution and App Installation Request lifecycle.
- NDF Frappe Docker remains authoritative for image composition, dependency resolution, image validation and deployment artifact production.
- Tenant Installed App must not be repurposed as the Bench application inventory.
- Tenant Modules and Tenant Allowed Module continue to represent Frappe module/user-access configuration; they are not application-runtime inventory.

### Cross-repository architecture records

- [DT Master M4 architecture](https://github.com/NdfTechLabs/dt_master# m4--ndf-frappe-docker-integration)
- [NDF Frappe Docker M4 architecture](https://github.com/NdfTechLabs/frappe_docker/blob/main/images/ndf/README.md)

The API payloads, authentication scopes, status model and retry/idempotency rules remain M4.1 design deliverables. This document does not claim that those contracts have already been implemented.
