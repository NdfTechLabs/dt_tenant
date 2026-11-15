"""Move Tenant Settings.api_secret from plaintext into encrypted storage.

The field became a Password field; a value saved before that is still stored
as plaintext in the Singles table. Idempotent: a masked value is skipped.
"""

import frappe
from frappe.utils.password import set_encrypted_password

DOCTYPE = "Tenant Settings"
FIELDNAME = "api_secret"


def execute():
	rows = frappe.db.sql(
		"select `value` from `tabSingles` where `doctype` = %s and `field` = %s",
		(DOCTYPE, FIELDNAME),
	)
	value = rows[0][0] if rows else None
	if not value or set(value) == {"*"}:
		return

	set_encrypted_password(DOCTYPE, DOCTYPE, value, FIELDNAME)
	frappe.db.set_single_value(DOCTYPE, FIELDNAME, "*" * len(value), update_modified=False)
