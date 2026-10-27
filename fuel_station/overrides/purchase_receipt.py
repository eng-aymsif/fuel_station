import frappe
from frappe import _
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt


class CustomPurchaseReceipt(PurchaseReceipt):
	def validate(self):
		super().validate()
		self.validate_fuel_delivery()

	def validate_fuel_delivery(self):
		if self.get("fuel_station") and self.get("source_key"):
			existing = frappe.db.get_value(
				"Purchase Receipt",
				{"source_key": self.source_key, "name": ["!=", self.name or ""], "docstatus": ["!=", 2]},
				"name",
			)
			if existing:
				frappe.throw(_("Duplicate Fuel Purchase Receipt detected for source key {0}: {1}").format(self.source_key, existing))

