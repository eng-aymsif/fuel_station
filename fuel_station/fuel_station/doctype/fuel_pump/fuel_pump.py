import frappe
from frappe import _
from frappe.model.document import Document


class FuelPump(Document):
	def validate(self):
		if self.tank and frappe.db.exists("Fuel Tank", self.tank):
			tank_doc = frappe.get_doc("Fuel Tank", self.tank)
			if tank_doc.station != self.station:
				frappe.throw(_("Tank {0} does not belong to Station {1}.").format(self.tank, self.station))
			if not self.item:
				self.item = tank_doc.item
			elif self.item != tank_doc.item:
				frappe.throw(_("Pump item ({0}) must match linked Tank item ({1}).").format(self.item, tank_doc.item))
			if not self.warehouse:
				self.warehouse = tank_doc.warehouse
			elif self.warehouse != tank_doc.warehouse:
				frappe.throw(_("Pump warehouse ({0}) must match linked Tank warehouse ({1}).").format(self.warehouse, tank_doc.warehouse))

		if self.item and not self.fuel_grade:
			self.fuel_grade = frappe.db.get_value("Item", self.item, "fuel_grade")
