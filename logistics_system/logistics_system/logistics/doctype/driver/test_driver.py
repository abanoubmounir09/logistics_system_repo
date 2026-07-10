# Copyright (c) 2026, Logistics System
# License: MIT

import frappe
from frappe.tests.utils import FrappeTestCase


class TestDriver(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_requires_phone_number(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({
				"doctype": "Driver",
				"driver_name": "No Phone Driver",
				"max_stops_per_run": 3,
			}).insert(ignore_permissions=True)

	def test_max_stops_must_be_positive(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({
				"doctype": "Driver",
				"driver_name": "Zero Stops Driver",
				"phone_number": "01011111111",
				"max_stops_per_run": 0,
			}).insert(ignore_permissions=True)
