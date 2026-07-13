# Copyright (c) 2026, Logistics System
# License: MIT

import frappe

ROLES = ["Logistics Manager", "Logistics Dispatcher", "Driver"]


def after_install():
	create_roles()
	frappe.db.commit()


def create_roles():
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({
				"doctype": "Role",
				"role_name": role,
				"desk_access": 1,
			}).insert(ignore_permissions=True)
