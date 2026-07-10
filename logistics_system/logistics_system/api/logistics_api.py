# Copyright (c) 2026, Logistics System
# License: MIT
#
# All endpoints are exposed at:
#   /api/method/logistics_system.api.logistics_api.<function_name>
#
# Every endpoint:
#   - requires the caller to be logged in (Frappe handles this at the
#     framework level for whitelisted methods)
#   - relies on Frappe's standard DocType permission system (see each
#     DocType's json "permissions" + permission_query_conditions in
#     logistics_system/permissions/driver_permissions.py) for RBAC
#   - runs inside Frappe's implicit request-scoped DB transaction, which is
#     committed on a 200 response and rolled back automatically if any
#     exception (e.g. frappe.throw) is raised - so a failed action never
#     leaves data half-updated.

import frappe
from frappe import _


def _json_response(data=None, message=None):
	frappe.local.response["http_status_code"] = 200
	return {"success": True, "message": message, "data": data}


@frappe.whitelist(methods=["POST"])
def build_delivery_run(driver: str, order_names=None):
	"""Create a new Delivery Run and assign Open orders to the given driver."""
	if isinstance(order_names, str):
		order_names = frappe.parse_json(order_names)

	if not frappe.has_permission("Delivery Run", "create"):
		frappe.throw(_("Not permitted to create Delivery Runs."), frappe.PermissionError)

	run = frappe.new_doc("Delivery Run")
	run.driver = driver
	run.run_status = "Draft"
	run.insert()
	run.build_run(driver=driver, order_names=order_names)

	return _json_response(data=run.as_dict(), message=f"Run {run.name} built successfully.")


@frappe.whitelist(methods=["POST"])
def start_delivery_run(run_name: str):
	run = frappe.get_doc("Delivery Run", run_name)
	run.check_permission("write")
	run.start_run()
	return _json_response(data=run.as_dict(), message=f"Run {run.name} started.")


@frappe.whitelist(methods=["POST"])
def mark_stop_delivered(run_name: str, stop_name: str):
	run = frappe.get_doc("Delivery Run", run_name)
	run.check_permission("write")
	_validate_driver_owns_stop(run)
	run.mark_stop_delivered(stop_name=stop_name)
	return _json_response(data=run.as_dict(), message="Stop marked as Delivered.")


@frappe.whitelist(methods=["POST"])
def mark_stop_failed(run_name: str, stop_name: str, failed_reason: str):
	run = frappe.get_doc("Delivery Run", run_name)
	run.check_permission("write")
	_validate_driver_owns_stop(run)
	run.mark_stop_failed(stop_name=stop_name, failed_reason=failed_reason)
	return _json_response(data=run.as_dict(), message="Stop marked as Failed.")


@frappe.whitelist(methods=["POST"])
def complete_delivery_run(run_name: str):
	run = frappe.get_doc("Delivery Run", run_name)
	run.check_permission("write")
	run.complete_run()
	return _json_response(data=run.as_dict(), message=f"Run {run.name} completed.")


@frappe.whitelist(methods=["POST"])
def bank_cash(run_name: str, cash_banked_location: str):
	run = frappe.get_doc("Delivery Run", run_name)
	run.check_permission("write")
	# Only Manager/Dispatcher should bank cash, not the driver themselves
	if _current_user_role() == "Driver":
		frappe.throw(_("Drivers are not permitted to bank cash."), frappe.PermissionError)
	run.bank_cash(cash_banked_location=cash_banked_location)
	return _json_response(data=run.as_dict(), message=f"Cash banked for run {run.name}.")


def _current_user_role():
	roles = frappe.get_roles(frappe.session.user)
	if "Logistics Manager" in roles:
		return "Logistics Manager"
	if "Logistics Dispatcher" in roles:
		return "Logistics Dispatcher"
	if "Driver" in roles:
		return "Driver"
	return None


def _validate_driver_owns_stop(run):
	"""If the caller is a Driver (and not also a Manager/Dispatcher),
	they may only update stops on runs assigned to their own Driver record."""
	roles = frappe.get_roles(frappe.session.user)
	if "Logistics Manager" in roles or "Logistics Dispatcher" in roles:
		return
	if "Driver" in roles:
		driver_name = frappe.db.get_value("Driver", {"user": frappe.session.user}, "name")
		if not driver_name or run.driver != driver_name:
			frappe.throw(_("You may only update stops on your own delivery run."), frappe.PermissionError)


# ---------------------------------------------------------------------- #
# Bonus: Dashboard summary
# ---------------------------------------------------------------------- #
@frappe.whitelist(methods=["GET"])
def dashboard_summary():
	from frappe.utils import today

	open_orders = frappe.db.count("Order", {"status": "Open"})
	active_drivers = frappe.db.count("Driver", {"active": 1, "status": ["!=", "Inactive"]})
	runs_en_route = frappe.db.count("Delivery Run", {"run_status": "En Route"})

	cash_today = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(total_cash_collected), 0)
		FROM `tabDelivery Run`
		WHERE run_status = 'Cash Banked' AND DATE(cash_banked_date) = %s
		""",
		(today(),),
	)[0][0]

	active_runs = frappe.get_all(
		"Delivery Run",
		filters={"run_status": ["in", ["Assigned", "En Route"]]},
		fields=["name", "driver", "run_status", "total_cash_collected", "started_date"],
		order_by="creation desc",
		limit_page_length=20,
	)

	return _json_response(data={
		"open_orders": open_orders,
		"active_drivers": active_drivers,
		"runs_en_route": runs_en_route,
		"cash_collected_today": cash_today,
		"active_runs": active_runs,
	})
