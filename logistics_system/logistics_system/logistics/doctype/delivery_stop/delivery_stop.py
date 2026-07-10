# Copyright (c) 2026, Logistics System
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document


class DeliveryStop(Document):
	def validate(self):
		if self.cash_amount is not None and self.cash_amount < 0:
			frappe.throw(_("Cash Amount cannot be negative for stop {0}.").format(self.customer_name))
		if self.stop_status == "Failed" and not (self.failed_reason and self.failed_reason.strip()):
			frappe.throw(_("Failed Reason is required when a stop is marked as Failed."))
