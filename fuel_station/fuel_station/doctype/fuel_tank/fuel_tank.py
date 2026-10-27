import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt
from fuel_station.services.business_logic import log_audit_event


class FuelTank(Document):
	def validate(self):
		if self.station and not self.company:
			self.company = frappe.db.get_value("Fuel Station", self.station, "company")

		# Validate item is a Fuel Item
		if self.item:
			is_fuel = cint(frappe.db.get_value("Item", self.item, "is_fuel_item"))
			item_group = frappe.db.get_value("Item", self.item, "item_group")
			if not is_fuel and item_group not in ("Fuel", "Fuel Related Stock Items"):
				frappe.throw(_("Item {0} must be marked as a Fuel Item (is_fuel_item=1) or belong to Fuel item group.").format(self.item))

		# Validate warehouse belongs to company
		if self.warehouse and self.company:
			wh_company = frappe.db.get_value("Warehouse", self.warehouse, "company")
			if wh_company and wh_company != self.company:
				frappe.throw(_("Warehouse {0} belongs to company {1}, not {2}.").format(self.warehouse, wh_company, self.company))

		# Prevent changing warehouse after transactions exist unless approved override
		if not self.is_new():
			old_wh = frappe.db.get_value("Fuel Tank", self.name, "warehouse")
			if old_wh and old_wh != self.warehouse:
				has_sle = frappe.db.exists("Stock Ledger Entry", {"warehouse": old_wh, "is_cancelled": 0})
				has_events = frappe.db.exists("Fuel Dispense Event", {"tank": self.name, "status": ["!=", "Cancelled"]})
				if (has_sle or has_events) and not (cint(self.allow_warehouse_change_override) and self.warehouse_change_reason):
					frappe.throw(_("Cannot change warehouse of Fuel Tank {0} after stock movements exist without an approved correction override and reason.").format(self.name))
				if has_sle or has_events:
					log_audit_event(
						"Fuel Tank Warehouse Changed",
						"Fuel Tank",
						self.name,
						station=self.station,
						previous_value=old_wh,
						new_value=self.warehouse,
						reason=self.warehouse_change_reason,
					)
