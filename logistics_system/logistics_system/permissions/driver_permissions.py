# Copyright (c) 2026, Logistics System
# License: MIT
#
# These functions are registered in hooks.py under permission_query_conditions
# and has_permission. They ensure that a user with ONLY the "Driver" role can
# see and act on delivery runs / orders / stops that belong to them, while
# Logistics Manager / Logistics Dispatcher retain full visibility (Frappe's
# standard doctype permissions already grant them access; we only add
# restrictions for the Driver role).

import frappe


def _is_pure_driver(user):
	roles = frappe.get_roles(user)
	if "Logistics Manager" in roles or "Logistics Dispatcher" in roles:
		return False
	return "Driver" in roles


def _driver_name_for_user(user):
	return frappe.db.get_value("Driver", {"user": user}, "name")


def delivery_run_query_conditions(user):
	user = user or frappe.session.user
	if not _is_pure_driver(user):
		return ""
	driver_name = _driver_name_for_user(user)
	if not driver_name:
		return "1=0"
	return f"""`tabDelivery Run`.driver = {frappe.db.escape(driver_name)}"""


def delivery_run_has_permission(doc, ptype, user):
	user = user or frappe.session.user
	if not _is_pure_driver(user):
		return True
	driver_name = _driver_name_for_user(user)
	return bool(driver_name) and doc.driver == driver_name


def order_query_conditions(user):
	user = user or frappe.session.user
	if not _is_pure_driver(user):
		return ""
	driver_name = _driver_name_for_user(user)
	if not driver_name:
		return "1=0"
	return f"""`tabOrder`.assigned_driver = {frappe.db.escape(driver_name)}"""


def order_has_permission(doc, ptype, user):
	user = user or frappe.session.user
	if not _is_pure_driver(user):
		return True
	driver_name = _driver_name_for_user(user)
	return bool(driver_name) and doc.assigned_driver == driver_name
