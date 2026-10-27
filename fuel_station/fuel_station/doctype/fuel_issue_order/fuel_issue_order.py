import secrets
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt
from fuel_station.services.settings_service import get_effective_settings


class FuelIssueOrder(Document):
	def validate(self):
		if not self.requester:
			self.requester = frappe.session.user
		if not self.print_token:
			self.print_token = "PRT-" + secrets.token_urlsafe(12)
		if not self.qr_code:
			self.qr_code = "FIO-" + secrets.token_urlsafe(16)

		settings = get_effective_settings(station=self.station)
		if cint(settings.require_cost_center) and self.treatment_type == "Internal" and not self.cost_center:
			if self.station:
				self.cost_center = frappe.db.get_value("Fuel Station", self.station, "default_cost_center")
		if cint(settings.require_vehicle) and not (self.vehicle or self.plate_number):
			frappe.throw(_("Vehicle or Plate Number is required for Fuel Issue Order."))
		if cint(settings.require_employee) and not self.employee:
			frappe.throw(_("Employee is required for Fuel Issue Order."))
		if cint(settings.require_department) and not self.requesting_department:
			frappe.throw(_("Requesting Department is required for Fuel Issue Order."))

		if self.vehicle and not self.plate_number and frappe.db.exists("Customer Vehicle", self.vehicle):
			self.plate_number = frappe.db.get_value("Customer Vehicle", self.vehicle, "plate_number")

		# Prevent Fuel Attendant from approving Issue Orders (§29.8)
		if not self.is_new():
			old = self.get_doc_before_save()
			if old and old.approval_status != "Approved" and self.approval_status == "Approved":
				roles = frappe.get_roles(frappe.session.user)
				if "Fuel Attendant" in roles and not any(
					r in roles for r in ("Shift Supervisor", "Station Manager", "Fuel Operations Manager", "System Manager", "System Administrator")
				):
					frappe.throw(_("Fuel Attendant is not permitted to approve Fuel Issue Orders."))
				if not self.approved_by:
					self.approved_by = frappe.session.user

		self.remaining_quantity = max(0.0, flt(self.quantity_limit) - flt(self.used_quantity))


@frappe.whitelist()
def make_stock_entry(issue_order_name):
	"""Generate a standard ERPNext Stock Entry (Material Issue) for a Fuel Issue Order."""
	doc = frappe.get_doc("Fuel Issue Order", issue_order_name)
	from fuel_station.services.business_logic import create_stock_entry_from_internal_issue
	qty = flt(doc.remaining_quantity) or flt(doc.quantity_limit)
	se = create_stock_entry_from_internal_issue(doc, quantity=qty, submit=False)
	if se:
		doc.db_set("stock_entry", se.name)
		return se.name
	return None
