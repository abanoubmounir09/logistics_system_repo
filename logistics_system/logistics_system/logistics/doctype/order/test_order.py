# Copyright (c) 2026, Logistics System
# License: MIT

import frappe
from frappe.tests.utils import FrappeTestCase


class TestOrder(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_requires_address_and_customer_name(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({
				"doctype": "Order",
				"customer_name": "",
				"address": "",
			}).insert(ignore_permissions=True)

	def test_default_status_is_open(self):
		order = frappe.get_doc({
			"doctype": "Order",
			"customer_name": "Jane Doe",
			"address": "123 Test St",
			"cash_amount": 50,
		}).insert(ignore_permissions=True)
		self.assertEqual(order.status, "Open")
