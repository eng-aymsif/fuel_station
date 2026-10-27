import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate


class FuelCalibrationEvent(Document):
	def validate(self):
		if flt(self.current_reading) < flt(self.previous_reading):
			frappe.throw(_("Current reading cannot be less than previous reading in Calibration Event."))
		self.quantity = flt(flt(self.current_reading) - flt(self.previous_reading), 4)

		if self.pump and frappe.db.exists("Fuel Pump", self.pump):
			pump_doc = frappe.get_doc("Fuel Pump", self.pump)
			if not self.item:
				self.item = pump_doc.item
			if not self.tank:
				self.tank = pump_doc.tank
			if not self.warehouse:
				self.warehouse = pump_doc.warehouse

	def on_update(self):
		if self.pump and self.status in ("Approved", "Posted"):
			updates = {"current_meter_reading": flt(self.current_reading), "last_calibration_date": self.business_date or nowdate()}
			if self.next_calibration_date:
				updates["next_calibration_date"] = self.next_calibration_date
			frappe.db.set_value("Fuel Pump", self.pump, updates)

		if self.status == "Approved" and self.stock_treatment == "Waste Expense" and not self.stock_entry and flt(self.quantity) > 0:
			station_doc = frappe.get_doc("Fuel Station", self.station)
			company = station_doc.company
			expense_acc = (
				self.waste_account
				or station_doc.default_waste_account
				or station_doc.default_expense_account
				or frappe.db.get_value("Company", company, "default_expense_account")
			)
			cc = self.cost_center or station_doc.default_cost_center or frappe.db.get_value("Company", company, "cost_center")
			se = frappe.get_doc(
				{
					"doctype": "Stock Entry",
					"stock_entry_type": "Material Issue",
					"purpose": "Material Issue",
					"company": company,
					"posting_date": self.business_date or nowdate(),
					"fuel_station": self.station,
					"fuel_calibration_event": self.name,
					"source_key": f"CAL-SE-{self.name}",
					"items": [
						{
							"item_code": self.item,
							"s_warehouse": self.warehouse,
							"qty": flt(self.quantity),
							"uom": "Liter",
							"expense_account": expense_acc,
							"cost_center": cc,
						}
					],
				}
			)
			se.flags.ignore_permissions = True
			se.insert(ignore_permissions=True)
			se.submit()
			self.db_set("stock_entry", se.name)
			self.db_set("status", "Posted")
