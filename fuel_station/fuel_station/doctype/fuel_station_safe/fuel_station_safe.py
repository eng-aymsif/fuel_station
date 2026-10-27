import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime
from fuel_station.services.business_logic import log_audit_event
from fuel_station.services.settings_service import get_effective_settings


class FuelStationSafe(Document):
	def validate(self):
		settings = get_effective_settings(station=self.station)
		old = self.get_doc_before_save() if not self.is_new() else None

		if old and old.status == "Closed":
			if self.status != "Reopened With Approval":
				frappe.throw(_("Closed Station Safe {0} cannot be modified directly. Reopen with approval first.").format(self.name))
			if not cint(settings.allow_reopen_closed_safe):
				frappe.throw(_("Reopening closed safes is disabled in settings."))
			if not self.reopen_reason or not self.approved_by:
				frappe.throw(_("Reopen Reason and Approved By are required to reopen a closed Station Safe."))
			self.reopened_at = now_datetime()
			log_audit_event(
				"Station Safe Reopened",
				"Fuel Station Safe",
				self.name,
				station=self.station,
				previous_value="Closed",
				new_value="Reopened With Approval",
				reason=self.reopen_reason,
			)

		# Expected safe balance formula (§30.13):
		# opening_balance + cash_received_from_boxes + approved_receipts - cash_deposited_to_bank - cash_transferred_to_other_safe - approved_expenses - refunds
		self.expected_safe_balance = flt(
			flt(self.opening_balance)
			+ flt(self.cash_received_from_boxes)
			+ flt(self.approved_receipts)
			- flt(self.cash_deposited_to_bank)
			- flt(self.cash_transferred_to_other_safe)
			- flt(self.approved_expenses)
			- flt(self.refunds),
			2,
		)

		if self.denominations:
			total = 0.0
			for row in self.denominations:
				row.subtotal = flt(flt(row.banknote_or_coin) * cint(row.quantity), 2)
				total += row.subtotal
			self.counted_safe_balance = flt(total, 2)
			self.last_counted_at = now_datetime()

		self.variance = flt(flt(self.counted_safe_balance) - flt(self.expected_safe_balance), 2)

		if self.status == "Closed" and (not old or old.status != "Closed"):
			roles = frappe.get_roles(frappe.session.user)
			if "Fuel Attendant" in roles and not any(
				r in roles for r in ("Shift Supervisor", "Station Manager", "Fuel Operations Manager", "Accountant", "System Manager", "System Administrator")
			):
				frappe.throw(_("Fuel Attendant is not permitted to close the Station Safe."))

			# Verify all cash boxes for this station + shift/date are closed or transferred
			box_filters = {"station": self.station, "status": ["in", ["Open", "Pending Count", "Counted", "Pending Review"]]}
			if self.shift:
				box_filters["shift"] = self.shift
			elif self.business_date:
				box_filters["business_date"] = self.business_date
			open_boxes = frappe.get_all("Fuel Cash Box", filters=box_filters, pluck="name")
			if open_boxes:
				frappe.throw(_("Cannot close Station Safe before all Cash Boxes are closed or transferred: {0}").format(", ".join(open_boxes)))

			if abs(self.variance) > flt(settings.cash_variance_tolerance_amount) and not self.approved_by:
				frappe.throw(_("Safe variance ({0}) exceeds tolerance. Approval required.").format(self.variance))
			if abs(self.variance) > 0 and not self.variance_policy_status:
				self.variance_policy_status = (
					"Within Tolerance"
					if abs(self.variance) <= flt(settings.cash_variance_tolerance_amount)
					else "Needs Investigation"
				)
			if not self.first_closed_at:
				self.first_closed_at = now_datetime()


@frappe.whitelist()
def make_bank_deposit(safe_name, bank_account=None, amount=None):
	"""Create standard ERPNext Payment Entry transferring vault cash to company bank."""
	safe = frappe.get_doc("Fuel Station Safe", safe_name)
	dep_amount = flt(amount) or flt(safe.counted_safe_balance or safe.expected_safe_balance)
	if dep_amount <= 0:
		frappe.throw(_("Deposit amount must be positive."))

	company = frappe.db.get_value("Fuel Station", safe.station, "company") or frappe.db.get_single_value("Global Defaults", "default_company")
	if not bank_account:
		bank_account = frappe.db.get_value("Account", {"company": company, "account_type": "Bank", "is_group": 0}, "name")

	pe = frappe.get_doc({
		"doctype": "Payment Entry",
		"payment_type": "Internal Transfer",
		"company": company,
		"posting_date": safe.business_date or frappe.utils.nowdate(),
		"paid_from": safe.cash_account or frappe.db.get_value("Account", {"company": company, "account_type": "Cash", "is_group": 0}, "name"),
		"paid_to": bank_account,
		"paid_amount": dep_amount,
		"received_amount": dep_amount,
		"reference_no": f"SAFE-DEP-{safe.name}",
		"reference_date": frappe.utils.nowdate(),
	})
	pe.insert(ignore_permissions=True)
	safe.db_set("bank_deposit_payment_entry", pe.name)
	safe.db_set("cash_deposited_to_bank", flt(safe.cash_deposited_to_bank) + dep_amount)
	return pe.name
