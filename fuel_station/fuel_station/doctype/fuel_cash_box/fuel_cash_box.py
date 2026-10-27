import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime
from fuel_station.services.business_logic import log_audit_event
from fuel_station.services.settings_service import get_effective_settings


class FuelCashBox(Document):
	def validate(self):
		settings = get_effective_settings(station=self.station)
		old = self.get_doc_before_save() if not self.is_new() else None

		# Prevent direct edits after Closed unless Reopened With Approval (§30.17, §30.22 #19, #20)
		if old and old.status == "Closed":
			if self.status != "Reopened With Approval":
				frappe.throw(_("Closed Cash Box {0} cannot be modified directly. Reopen with approval first.").format(self.name))
			if not cint(settings.allow_reopen_closed_cash_box):
				frappe.throw(_("Reopening closed cash boxes is disabled in settings."))
			if not self.reopen_reason or not self.approved_by:
				frappe.throw(_("Reopen Reason and Approved By are required to reopen a closed Cash Box."))
			roles = frappe.get_roles(frappe.session.user)
			if "Fuel Attendant" in roles and not any(
				r in roles for r in ("Station Manager", "Fuel Operations Manager", "System Manager", "System Administrator")
			):
				frappe.throw(_("Fuel Attendant cannot reopen a closed Cash Box."))
			self.reopened_at = now_datetime()
			log_audit_event(
				"Cash Box Reopened",
				"Fuel Cash Box",
				self.name,
				station=self.station,
				previous_value="Closed",
				new_value="Reopened With Approval",
				reason=self.reopen_reason,
			)

		# Prevent user from opening two active cash boxes simultaneously (§30.5, §30.9, §30.22 #5)
		if self.status == "Open" and not cint(self.allow_multiple_active_boxes):
			user_filter = self.assigned_user or (
				frappe.db.get_value("Employee", self.assigned_employee, "user_id") if self.assigned_employee else None
			)
			if user_filter:
				active_boxes = frappe.get_all(
					"Fuel Cash Box",
					filters={
						"assigned_user": user_filter,
						"status": "Open",
						"name": ["!=", self.name or ""],
					},
					pluck="name",
				)
				if active_boxes:
					frappe.throw(_("User {0} already has an active open Cash Box: {1}").format(user_filter, ", ".join(active_boxes)))
			elif self.assigned_employee:
				active_boxes = frappe.get_all(
					"Fuel Cash Box",
					filters={
						"assigned_employee": self.assigned_employee,
						"status": "Open",
						"name": ["!=", self.name or ""],
					},
					pluck="name",
				)
				if active_boxes:
					frappe.throw(_("Employee {0} already has an active open Cash Box: {1}").format(self.assigned_employee, ", ".join(active_boxes)))

		# Approved expenses require a valid document reference if > 0 (§30.15)
		if flt(self.approved_expenses) > 0 and not self.expense_reference_name:
			frappe.throw(_("Approved expenses cannot be deducted without a linked expense document reference."))

		# Calculate expected cash (§30.8):
		# opening_float + cash_sales + approved_receipts + cash_transfers_in - approved_expenses - refunds - cash_transfers_out
		# Card sales and unapproved expenses are strictly excluded!
		self.expected_cash = flt(
			flt(self.opening_float)
			+ flt(self.cash_sales)
			+ flt(self.approved_receipts)
			+ flt(self.cash_transfers_in)
			- flt(self.approved_expenses)
			- flt(self.refunds)
			- flt(self.cash_transfers_out),
			2,
		)

		# Denomination count calculation (§30.11)
		if self.denominations:
			total_counted = 0.0
			for row in self.denominations:
				row.subtotal = flt(flt(row.banknote_or_coin) * cint(row.quantity), 2)
				if not row.counted_by:
					row.counted_by = self.counted_by or frappe.session.user
				if not row.counted_at:
					row.counted_at = now_datetime()
				total_counted += row.subtotal
			self.counted_cash = flt(total_counted, 2)

		self.variance = flt(flt(self.counted_cash) - flt(self.expected_cash), 2)

		# Prevent modifying count after approval unless reopened
		if old and old.status in ("Variance Approved", "Transferred", "Closed") and self.status not in ("Reopened With Approval", "Transferred", "Closed"):
			if flt(old.counted_cash) != flt(self.counted_cash):
				frappe.throw(_("Cannot modify cash count after approval without reopening."))

		# Attendant cannot approve variances (§30.21)
		if self.status in ("Variance Approved", "Closed"):
			roles = frappe.get_roles(frappe.session.user)
			is_attendant_only = "Fuel Attendant" in roles and not any(
				r in roles for r in ("Shift Supervisor", "Station Manager", "Fuel Operations Manager", "System Manager", "System Administrator")
			)
			if is_attendant_only and (self.status == "Variance Approved" or abs(self.variance) > 0):
				frappe.throw(_("Fuel Attendant is not permitted to approve cash box variances."))

		# Closing checks (§30.10)
		if self.status == "Closed" and (not old or old.status != "Closed"):
			self._validate_closing(settings)

	def _validate_closing(self, settings):
		# Block closing if unclassified dispense events exist for this employee/shift
		if cint(settings.block_close_with_unclassified_events) and (self.shift or self.assigned_employee):
			ev_filters = {"station": self.station, "status": ["in", ["Draft", "Exception"]]}
			if self.shift:
				ev_filters["shift"] = self.shift
			if self.assigned_employee:
				ev_filters["employee"] = self.assigned_employee
			unclassified = frappe.get_all("Fuel Dispense Event", filters=ev_filters, pluck="name")
			if unclassified:
				frappe.throw(_("Cannot close Cash Box while unclassified dispense events exist: {0}").format(", ".join(unclassified)))

		tol_amt = flt(settings.cash_variance_tolerance_amount)
		if abs(self.variance) > tol_amt:
			if cint(settings.variance_requires_approval) and not self.approved_by:
				frappe.throw(
					_("Cash Box variance ({0}) exceeds tolerance ({1}). Supervisor/Manager approval is required.").format(
						self.variance, tol_amt
					)
				)
		if not self.first_closed_at:
			self.first_closed_at = now_datetime()


@frappe.whitelist()
def make_safe_transfer(cash_box_name, target_safe=None, amount=None):
	"""Transfer physical cash from an attendant till to the station safe."""
	box = frappe.get_doc("Fuel Cash Box", cash_box_name)
	transfer_amt = flt(amount) or flt(box.counted_cash or box.expected_cash)
	if transfer_amt <= 0:
		frappe.throw(_("Transfer amount must be positive."))

	if not target_safe:
		target_safe = frappe.db.get_value("Fuel Station Safe", {"station": box.station, "status": ["in", ["Open", "Counted"]]}, "name")
		if not target_safe:
			target_safe = frappe.db.get_value("Fuel Station Safe", {"station": box.station}, "name")

	# Create Cash Transfer record
	ct = frappe.get_doc({
		"doctype": "Cash Transfer",
		"station": box.station,
		"business_date": box.business_date or frappe.utils.nowdate(),
		"shift": box.shift,
		"from_cash_box": box.name,
		"to_safe": target_safe,
		"amount": transfer_amt,
		"status": "Pending Receiver Confirmation",
	})
	ct.insert(ignore_permissions=True)
	return ct.name
