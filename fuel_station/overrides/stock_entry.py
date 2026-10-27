import frappe
from frappe import _
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry


class CustomStockEntry(StockEntry):
	def validate(self):
		super().validate()
		self.validate_fuel_stock_entry()

	def validate_fuel_stock_entry(self):
		if self.get("fuel_station") and self.get("source_key"):
			existing = frappe.db.get_value(
				"Stock Entry",
				{"source_key": self.source_key, "name": ["!=", self.name or ""], "docstatus": ["!=", 2]},
				"name",
			)
			if existing:
				frappe.throw(_("Duplicate Fuel Stock Entry detected for source key {0}: {1}").format(self.source_key, existing))

