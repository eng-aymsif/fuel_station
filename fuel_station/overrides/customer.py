import frappe
from frappe import _
from erpnext.selling.doctype.customer.customer import Customer


class CustomCustomer(Customer):
	def validate(self):
		super().validate()
		self.validate_fuel_customer()

	def validate_fuel_customer(self):
		if self.get("fuel_customer_type") == "Credit":
			if self.get("credit_days") and int(self.credit_days) < 0:
				frappe.throw(_("Credit days cannot be negative."))

