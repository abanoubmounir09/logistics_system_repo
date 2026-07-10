# Copyright (c) 2026, Logistics System
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class DeliveryRun(Document):
	# ------------------------------------------------------------------ #
	# Standard controller hooks
	# ------------------------------------------------------------------ #
	def validate(self):
		self.recalculate_total_cash_collected()

	def recalculate_total_cash_collected(self):
		total = 0
		for stop in self.delivery_stops:
			if stop.stop_status == "Delivered":
				total += stop.cash_amount or 0
		self.total_cash_collected = total

	# ------------------------------------------------------------------ #
	# 1. Build Delivery Run
	# ------------------------------------------------------------------ #
	@frappe.whitelist()
	def build_run(self, driver: str, order_names: list | None = None):
		"""
		Assign a set of Open orders to a driver as an ordered list of stops.
		If order_names is not provided, the oldest Open orders (by priority,
		then creation) up to the driver's max_stops_per_run are auto-selected.
		"""
		if self.run_status != "Draft" or self.delivery_stops:
			frappe.throw(_("This run has already been built."))

		driver_doc = frappe.get_doc("Driver", driver)
		self._validate_driver_available(driver_doc)

		orders = self._select_orders_for_run(driver_doc, order_names)
		if not orders:
			frappe.throw(_("No eligible Open orders found to build this run."))

		self.driver = driver_doc.name
		self.delivery_stops = []
		for idx, order in enumerate(orders, start=1):
			self.append("delivery_stops", {
				"related_order": order.name,
				"stop_sequence": idx,
				"customer_name": order.customer_name,
				"address": order.address,
				"cash_amount": order.cash_amount,
				"stop_status": "Assigned",
			})

		self.run_status = "Assigned"
		self.save()

		for order in orders:
			order_doc = frappe.get_doc("Order", order.name)
			order_doc.status = "Assigned"
			order_doc.assigned_driver = driver_doc.name
			order_doc.delivery_run = self.name
			order_doc.save()

		frappe.msgprint(_("Run {0} built with {1} stop(s) for driver {2}.").format(
			self.name, len(orders), driver_doc.driver_name
		))
		return self

	def _validate_driver_available(self, driver_doc):
		if not driver_doc.active:
			frappe.throw(_("Driver {0} is inactive and cannot be assigned to a new run.").format(
				driver_doc.driver_name))
		if driver_doc.status == "On Run":
			frappe.throw(_("Driver {0} is already on an active run.").format(driver_doc.driver_name))
		if driver_doc.max_stops_per_run <= 0:
			frappe.throw(_("Driver {0} has an invalid Max Stops Per Run configuration.").format(
				driver_doc.driver_name))

	def _select_orders_for_run(self, driver_doc, order_names):
		limit = driver_doc.max_stops_per_run

		if order_names:
			if len(order_names) > limit:
				frappe.throw(_("Cannot assign {0} orders: driver's max stops per run is {1}.").format(
					len(order_names), limit
				))
			orders = [frappe.get_doc("Order", name) for name in order_names]
			for order in orders:
				if order.status != "Open":
					frappe.throw(_("Order {0} is not Open (current status: {1}) and cannot be assigned.").format(
						order.name, order.status
					))
			return orders

		# Auto-select: High priority first, then oldest created
		priority_order = {"High": 0, "Medium": 1, "Low": 2}
		open_orders = frappe.get_all(
			"Order",
			filters={"status": "Open"},
			fields=["name", "customer_name", "address", "cash_amount", "priority", "created_date"],
			limit_page_length=0,
		)
		open_orders.sort(key=lambda o: (priority_order.get(o.priority, 1), o.created_date or ""))
		return open_orders[:limit]

	# ------------------------------------------------------------------ #
	# 2. Start Delivery Run
	# ------------------------------------------------------------------ #
	@frappe.whitelist()
	def start_run(self):
		if self.run_status != "Assigned":
			frappe.throw(_("Only a run in 'Assigned' status can be started. Current status: {0}").format(
				self.run_status
			))
		if not self.delivery_stops:
			frappe.throw(_("Cannot start a run with no delivery stops."))

		self.run_status = "En Route"
		self.started_date = now_datetime()
		for stop in self.delivery_stops:
			stop.stop_status = "En Route"
		self.save()

		for stop in self.delivery_stops:
			order_doc = frappe.get_doc("Order", stop.related_order)
			order_doc.status = "En Route"
			order_doc.save()

		driver_doc = frappe.get_doc("Driver", self.driver)
		driver_doc.status = "On Run"
		driver_doc.save()

		frappe.msgprint(_("Run {0} started. Driver {1} dispatched.").format(self.name, driver_doc.driver_name))
		return self

	# ------------------------------------------------------------------ #
	# 3. Mark Stop as Delivered / Failed
	# ------------------------------------------------------------------ #
	@frappe.whitelist()
	def mark_stop_delivered(self, stop_name: str):
		stop = self._get_stop(stop_name)
		self._validate_run_en_route()
		self._validate_stop_actionable(stop)

		stop.stop_status = "Delivered"
		stop.delivered_date = now_datetime()
		self.save()

		order_doc = frappe.get_doc("Order", stop.related_order)
		order_doc.status = "Delivered"
		order_doc.delivered_date = stop.delivered_date
		order_doc.save()

		frappe.msgprint(_("Stop for order {0} marked as Delivered.").format(stop.related_order))
		return self

	@frappe.whitelist()
	def mark_stop_failed(self, stop_name: str, failed_reason: str):
		if not failed_reason or not failed_reason.strip():
			frappe.throw(_("Failed Reason is required to mark a stop as Failed."))

		stop = self._get_stop(stop_name)
		self._validate_run_en_route()
		self._validate_stop_actionable(stop)

		stop.stop_status = "Failed"
		stop.failed_reason = failed_reason
		self.save()

		order_doc = frappe.get_doc("Order", stop.related_order)
		order_doc.status = "Failed"
		order_doc.save()

		frappe.msgprint(_("Stop for order {0} marked as Failed: {1}").format(stop.related_order, failed_reason))
		return self

	def _get_stop(self, stop_name):
		for stop in self.delivery_stops:
			if stop.name == stop_name:
				return stop
		frappe.throw(_("Stop {0} not found on run {1}.").format(stop_name, self.name))

	def _validate_run_en_route(self):
		if self.run_status != "En Route":
			frappe.throw(_("Stops can only be updated while the run is En Route. Current status: {0}").format(
				self.run_status
			))

	def _validate_stop_actionable(self, stop):
		if stop.stop_status in ("Delivered", "Failed"):
			frappe.throw(_("Stop for order {0} has already been resolved ({1}).").format(
				stop.related_order, stop.stop_status
			))

	# ------------------------------------------------------------------ #
	# 4. Complete Delivery Run
	# ------------------------------------------------------------------ #
	@frappe.whitelist()
	def complete_run(self):
		if self.run_status != "En Route":
			frappe.throw(_("Only a run that is En Route can be completed. Current status: {0}").format(
				self.run_status
			))

		unresolved = [s for s in self.delivery_stops if s.stop_status not in ("Delivered", "Failed")]
		if unresolved:
			frappe.throw(_(
				"Cannot complete run: {0} stop(s) are still not marked as Delivered or Failed."
			).format(len(unresolved)))

		self.run_status = "Completed"
		self.completed_date = now_datetime()
		self.save()

		driver_doc = frappe.get_doc("Driver", self.driver)
		driver_doc.status = "Available"
		driver_doc.save()

		frappe.msgprint(_("Run {0} completed. Driver {1} is now available.").format(
			self.name, driver_doc.driver_name
		))
		return self

	# ------------------------------------------------------------------ #
	# 5. Bank Cash
	# ------------------------------------------------------------------ #
	@frappe.whitelist()
	def bank_cash(self, cash_banked_location: str):
		if self.run_status != "Completed":
			frappe.throw(_("Cash can only be banked for a Completed run. Current status: {0}").format(
				self.run_status
			))
		if not cash_banked_location or not cash_banked_location.strip():
			frappe.throw(_("Cash Banked Location is required."))

		self.run_status = "Cash Banked"
		self.cash_banked_date = now_datetime()
		self.cash_banked_location = cash_banked_location
		self.save()

		for stop in self.delivery_stops:
			if stop.stop_status == "Delivered":
				order_doc = frappe.get_doc("Order", stop.related_order)
				order_doc.status = "Cash Banked"
				order_doc.save()

		frappe.msgprint(_("Cash for run {0} banked at {1}. Total: {2}").format(
			self.name, cash_banked_location, self.total_cash_collected
		))
		return self
