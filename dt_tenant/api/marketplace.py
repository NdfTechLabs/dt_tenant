import requests
import frappe

from dt_tenant.controllers.capabilities import CapabilitySyncError, get_master_connection, get_tenant_fqdn


def _master_api_call(path, payload):

    try:
        master_url, auth_headers = get_master_connection()
    except CapabilitySyncError as e:
        frappe.throw(str(e))

    url = f"{master_url}{path}"

    headers = {**auth_headers, "Content-Type": "application/json"}

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )

    response.raise_for_status()
    return response.json().get("message")

@frappe.whitelist()
def install_extension(extension_name):

    fqdn = get_tenant_fqdn()

    return _master_api_call(
        "/api/method/dt_master.api.marketplace.install_extension_for_tenant",
        {
            "extension_name": extension_name,
            "fqdn": fqdn
        }
    )

@frappe.whitelist()
def upgrade_extension(extension_name):

    fqdn = get_tenant_fqdn()

    return _master_api_call(
        "/api/method/dt_master.api.marketplace.upgrade_extension_for_tenant",
        {
            "extension_name": extension_name,
            "fqdn": fqdn
        }
    )

@frappe.whitelist()
def uninstall_extension(extension_name):

    fqdn = get_tenant_fqdn()

    return _master_api_call(
        "/api/method/dt_master.api.marketplace.uninstall_extension_for_tenant",
        {
            "extension_name": extension_name,
            "fqdn": fqdn
        }
    )

@frappe.whitelist()
def publish_install_update(extension, status, action_status, error=None, site=None):

    frappe.publish_realtime(
        event="extension_install_update",
        message={
            "extension": extension,
            "status": status,
            "action_status": action_status,
            "error": error,
            "site": site
        },
        after_commit=True
    )