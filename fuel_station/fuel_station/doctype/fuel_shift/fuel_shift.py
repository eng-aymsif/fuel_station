import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime
from fuel_station.services.business_logic import add_pump_sales_automatically, log_audit_event
from fuel_station.services.settings_service import get_effective_settings


class FuelShift(Document):
	def validate(self):
		settings = get_effective_settings(station=self.station)
		old_doc = self.get_doc_before_save() if not self.is_new() else None

		if old_doc and old_doc.status == "Closed":
			if self.status != "Reopened With Approval":
				frappe.throw(_("Closed shift {0} cannot be modified directly. Use Reopened With Approval with a valid reason and manager approval.").format(self.name))
			if not cint(settings.allow_reopen_closed_shift):
				frappe.throw(_("Reopening closed shifts is disabled in settings."))
			if not self.reopen_reason or not self.approved_by:
				frappe.throw(_("Reopen Reason and Approved By are required to reopen a closed shift."))
			roles = frappe.get_roles(frappe.session.user)
			if "Fuel Attendant" in roles and not any(r in roles for r in ("Station Manager", "Fuel Operations Manager", "System Manager", "System Administrator")):
				frappe.throw(_("Only a Manager can reopen a closed shift."))
			self.reopened_at = now_datetime()
			log_audit_event(
				"Shift Reopened",
				"Fuel Shift",
				self.name,
				station=self.station,
				previous_value="Closed",
				new_value="Reopened With Approval",
				reason=self.reopen_reason,
			)

		if self.is_new() or (old_doc and old_doc.status == "Planned" and self.status in ("Open", "In Operation")):
			self._validate_opening(settings)

		if self.status == "Closed" and (not old_doc or old_doc.status != "Closed"):
			self._validate_closing(settings)

	def _validate_opening(self, settings):
		if not self.opened_at:
			self.opened_at = now_datetime()
		# Check conflicting open shifts for the same station
		conflicting = frappe.get_all(
			"Fuel Shift",
			filters={
				"station": self.station,
				"name": ["!=", self.name or ""],
				"status": ["in", ["Open", "In Operation", "Pending Closing"]],
			},
			pluck="name",
		)
		if conflicting and not (cint(self.allow_exceptional_open) and self.exceptional_open_reason):
			frappe.throw(_("Cannot open shift for station {0} while shift {1} is still open.").format(self.station, ", ".join(conflicting)))

	def _validate_closing(self, settings):
		# 1. Check open pump assignments
		open_assignments = frappe.get_all(
			"Fuel Pump Assignment",
			filters={"shift": self.name, "status": "Active"},
			pluck="name",
		)
		if open_assignments:
			frappe.throw(_("Cannot close shift while pump assignments are still active: {0}").format(", ".join(open_assignments)))

		# 2. Check uncounted/open cash boxes
		open_boxes = frappe.get_all(
			"Fuel Cash Box",
			filters={"shift": self.name, "status": ["in", ["Open", "Pending Count"]]},
			pluck="name",
		)
		if open_boxes:
			frappe.throw(_("Cannot close shift while cash boxes are not counted/closed: {0}").format(", ".join(open_boxes)))

		# 3. Check unclassified dispense events
		if cint(settings.block_close_with_unclassified_events):
			unclassified = frappe.get_all(
				"Fuel Dispense Event",
				filters={"shift": self.name, "status": ["in", ["Draft", "Exception"]]},
				pluck="name",
			)
			if unclassified:
				frappe.throw(_("Cannot close shift with unclassified or exception dispense events: {0}").format(", ".join(unclassified)))

		# 4. Check unapproved reconciliation variances
		unapproved_recons = frappe.get_all(
			"Fuel Pump Reconciliation",
			filters={"shift": self.name, "status": ["in", ["Pending Review", "Rejected"]]},
			pluck="name",
		)
		if unapproved_recons:
			frappe.throw(_("Cannot close shift with unapproved pump reconciliations: {0}").format(", ".join(unapproved_recons)))

		self.closed_at = now_datetime()
		self.closing_status = "Closed"
		if not self.first_closed_at:
			self.first_closed_at = self.closed_at

		if cint(settings.create_invoice_drafts_on_close):
			add_pump_sales_automatically(
				station=self.station,
				business_date=self.business_date,
				shift=self.name,
				create_invoices=True,
			)


@frappe.whitelist()
def generate_shift_sales_invoices(shift_name):
	"""Batch generate all un-invoiced Sales Invoices for this shift."""
	shift = frappe.get_doc("Fuel Shift", shift_name)
	res = add_pump_sales_automatically(
		station=shift.station,
		business_date=shift.business_date,
		shift=shift.name,
		create_invoices=True,
	)
	return res or []
