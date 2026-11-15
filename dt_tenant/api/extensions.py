import requests
import frappe

from dt_tenant.controllers.capabilities import CapabilitySyncError, get_master_connection, get_tenant_fqdn


def normalize_version(version):
    if not version:
        return [0, 0, 0]

    # Remove anything after first hyphen (dev, beta, rc, etc.)
    clean = version.split("-")[0]

    parts = clean.split(".")

    normalized = []
    for part in parts:
        try:
            normalized.append(int(part))
        except ValueError:
            normalized.append(0)

    return normalized

@frappe.whitelist()
def get_marketplace_extensions(tab=None, limit=12, offset=0):

    try:
        master_url, auth_headers = get_master_connection()
    except CapabilitySyncError as e:
        frappe.throw(str(e))

    fqdn = get_tenant_fqdn()

    frappe_version = frappe.__version__
    normalized_frappe_version=normalize_version(frappe_version)
    frappe_major = normalized_frappe_version[0]
    frappe_minor = normalized_frappe_version[1]
    frappe_patch = normalized_frappe_version[2]

    response = requests.get(
        f"{master_url}/api/method/dt_master.api.extensions.get_extensions",
        headers=auth_headers,
        params={
            "tab": tab,
            "limit": limit,
            "offset": offset,
            "fqdn": fqdn,
            "frappe_major": frappe_major,
            "frappe_minor": frappe_minor,
            "frappe_patch": frappe_patch
        },
        timeout=10,
    )

    response.raise_for_status()

    return response.json().get("message")