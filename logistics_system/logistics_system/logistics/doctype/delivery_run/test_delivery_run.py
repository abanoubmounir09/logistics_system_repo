# Copyright (c) 2026, Logistics System
# License: MIT

import frappe
from frappe.tests.utils import FrappeTestCase


class TestDeliveryRun(FrappeTestCase):
	def setUp(self):
		self.driver = frappe.get_doc({
			"doctype": "Driver",
			"driver_name": "Test Driver A",
			"phone_number": "01000000000",
			"active": 1,
			"max_stops_per_run": 2,
		}).insert(ignore_permissions=True)

		self.orders = []
		for i in range(3):
			order = frappe.get_doc({
				"doctype": "Order",
				"customer_name": f"Customer {i}",
				"address": f"Address {i}",
				"cash_amount": 100 + i,
				"priority": "Medium",
			}).insert(ignore_permissions=True)
			self.orders.append(order)

	def tearDown(self):
		frappe.db.rollback()

	def test_full_lifecycle(self):
		run = frappe.new_doc("Delivery Run")
		run.driver = self.driver.name
		run.run_status = "Draft"
		run.insert(ignore_permissions=True)

		run.build_run(driver=self.driver.name, order_names=[self.orders[0].name, self.orders[1].name])
		self.assertEqual(run.run_status, "Assigned")
		self.assertEqual(len(run.delivery_stops), 2)

		run.start_run()
		self.assertEqual(run.run_status, "En Route")
		self.assertEqual(frappe.db.get_value("Driver", self.driver.name, "status"), "On Run")

		stop1, stop2 = run.delivery_stops[0], run.delivery_stops[1]
		run.mark_stop_delivered(stop_name=stop1.name)
		run.mark_stop_failed(stop_name=stop2.name, failed_reason="Customer not available")

		run.complete_run()
		self.assertEqual(run.run_status, "Completed")
		self.assertEqual(frappe.db.get_value("Driver", self.driver.name, "status"), "Available")

		run.bank_cash(cash_banked_location="Main Office Safe")
		self.assertEqual(run.run_status, "Cash Banked")
		self.assertEqual(
			frappe.db.get_value("Order", self.orders[0].name, "status"), "Cash Banked"
		)
		self.assertEqual(
			frappe.db.get_value("Order", self.orders[1].name, "status"), "Failed"
		)

	def test_cannot_build_run_for_inactive_driver(self):
		self.driver.active = 0
		self.driver.status = "Inactive"
		self.driver.save(ignore_permissions=True)

		run = frappe.new_doc("Delivery Run")
		run.driver = self.driver.name
		run.run_status = "Draft"
		run.insert(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):
			run.build_run(driver=self.driver.name, order_names=[self.orders[0].name])

	def test_cannot_exceed_max_stops_per_run(self):
		run = frappe.new_doc("Delivery Run")
		run.driver = self.driver.name
		run.run_status = "Draft"
		run.insert(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):
			run.build_run(
				driver=self.driver.name,
				order_names=[o.name for o in self.orders],  # 3 orders > max_stops_per_run (2)
			)

	def test_negative_cash_amount_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({
				"doctype": "Order",
				"customer_name": "Bad Order",
				"address": "Nowhere",
				"cash_amount": -50,
			}).insert(ignore_permissions=True)

	def test_complete_run_requires_all_stops_resolved(self):
		run = frappe.new_doc("Delivery Run")
		run.driver = self.driver.name
		run.run_status = "Draft"
		run.insert(ignore_permissions=True)
		run.build_run(driver=self.driver.name, order_names=[self.orders[0].name])
		run.start_run()

		with self.assertRaises(frappe.ValidationError):
			run.complete_run()
