import frappe
from frappe.model.document import Document
from frappe.utils import flt


class FuelTankReconciliation(Document):
	def validate(self):
		if self.tank and frappe.db.exists("Fuel Tank", self.tank):
			tank_doc = frappe.get_doc("Fuel Tank", self.tank)
			if not self.warehouse:
				self.warehouse = tank_doc.warehouse
			if not self.item:
				self.item = tank_doc.item

		if self.warehouse and self.item:
			actual_qty = frappe.db.get_value("Bin", {"warehouse": self.warehouse, "item_code": self.item}, "actual_qty")
			self.book_quantity = flt(actual_qty)

		self.variance_quantity = flt(flt(self.physical_dip_quantity) - flt(self.book_quantity), 4)
		if self.status == "Draft":
			self.status = "Calculated"
