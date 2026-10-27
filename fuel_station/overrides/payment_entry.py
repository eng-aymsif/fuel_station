import frappe
from frappe import _
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry


class CustomPaymentEntry(PaymentEntry):
	def validate(self):
		super().validate()
		self.validate_fuel_payment_entry()

	def validate_fuel_payment_entry(self):
		if self.get("fuel_station") and self.get("source_key"):
			existing = frappe.db.get_value(
				"Payment Entry",
				{"source_key": self.source_key, "name": ["!=", self.name or ""], "docstatus": ["!=", 2]},
				"name",
			)
			if existing:
				frappe.throw(_("Duplicate Fuel Payment Entry detected for source key {0}: {1}").format(self.source_key, existing))

