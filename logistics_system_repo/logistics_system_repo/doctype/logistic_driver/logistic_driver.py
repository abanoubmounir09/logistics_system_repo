# Copyright (c) 2026, abanoub.mounir001@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document



class LogisticDriver(Document):
	def validate(self):
		self.validate_phone_number()
		self.validate_max_stops_per_run()

	def validate_phone_number(self):
		if not self.phone_number or not self.phone_number.strip():
			frappe.throw(_("Phone Number is required for a Driver."))

	def validate_max_stops_per_run(self):
		if self.max_stops_per_run is None or self.max_stops_per_run <= 0:
			frappe.throw(_("Max Stops Per Run must be greater than zero."))

	def before_save(self):
		# Inactive drivers should never be left in an "On Run" state
		if not self.active and self.status == "On Run":
			frappe.throw(
				_("Cannot deactivate {0}: driver currently has an active run.").format(self.driver_name)
			)
		if not self.active and self.status != "Inactive":
			self.status = "Inactive"
		if self.active and self.status == "Inactive":
			self.status = "Available"
