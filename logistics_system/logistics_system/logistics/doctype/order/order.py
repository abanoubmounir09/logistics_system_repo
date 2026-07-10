# Copyright (c) 2026, Logistics System
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


class Order(Document):
	def validate(self):
		self.validate_required_fields()
		self.validate_cash_amount()
		if not self.created_date:
			self.created_date = today()

	def validate_required_fields(self):
		if not self.customer_name or not self.customer_name.strip():
			frappe.throw(_("Customer Name is required."))
		if not self.address or not self.address.strip():
			frappe.throw(_("Address is required."))

	def validate_cash_amount(self):
		if self.cash_amount is not None and self.cash_amount < 0:
			frappe.throw(_("Order Cash Amount cannot be negative."))

	def on_trash(self):
		if self.status != "Open":
			frappe.throw(
				_("Only Open orders can be deleted. This order is currently '{0}'.").format(self.status)
			)
