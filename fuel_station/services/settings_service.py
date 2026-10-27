import frappe
from frappe.utils import cint, flt

DEFAULT_SETTINGS = {
	"invoice_creator_mode": "ACCOUNTANT",
	"invoice_submitter_mode": "ACCOUNTANT",
	"invoice_timing": "PER_PUMP_SHIFT",
	"transaction_capture_timing": "DURING_DISPENSE",
	"stock_posting_timing": "ON_INVOICE_SUBMIT",
	"group_by_station": 1,
	"group_by_pump": 1,
	"group_by_shift": 1,
	"group_by_attendant": 0,
	"group_by_item": 1,
	"group_by_rate": 1,
	"group_by_payment_method": 1,
	"group_by_customer": 0,
	"group_by_cost_center": 0,
	"meter_source": "MANUAL",
	"require_opening_reading": 1,
	"require_closing_reading": 1,
	"allow_meter_correction": 1,
	"meter_correction_requires_approval": 1,
	"allowed_variance_liters": 5.0,
	"allowed_variance_percent": 0.5,
	"meter_variance_tolerance_quantity": 5.0,
	"enable_fuel_issue_orders": 1,
	"internal_issue_requires_order": 1,
	"enable_qr_authorization": 1,
	"require_vehicle": 0,
	"require_employee": 0,
	"require_department": 0,
	"require_cost_center": 1,
	"allow_emergency_issue": 1,
	"emergency_issue_approval_hours": 24,
	"allow_partial_issue": 1,
	"allow_over_issue_with_approval": 0,
	"allow_cash": 1,
	"allow_card": 1,
	"allow_credit": 1,
	"allow_prepaid": 1,
	"credit_requires_authorization": 1,
	"card_requires_reference": 1,
	"cash_custody_mode": "ATTENDANT_CASH_BOX",
	"attendant_can_submit": 0,
	"attendant_max_invoice_amount": 5000.0,
	"attendant_max_invoice_quantity": 1000.0,
	"cash_inference_mode": "METER_RESIDUAL",
	"unclassified_quantity_policy": "CREATE_CASH_DRAFT",
	"negative_cash_quantity_policy": "HOLD_FOR_REVIEW",
	"selling_price_tax_mode": "TAX_EXCLUSIVE",
	"default_sales_tax_template": None,
	"default_purchase_tax_template": None,
	"default_tax_category": None,
	"prices_include_tax": 0,
	"tax_rounding_method": "INVOICE_LEVEL",
	"tax_rounding_precision": 2,
	"allowed_rounding_difference": 0.05,
	"discount_application_order": "BEFORE_TAX",
	"allow_line_discount": 1,
	"allow_invoice_discount": 1,
	"allow_manual_discount": 1,
	"allow_attendant_discount": 0,
	"attendant_discount_requires_reason": 1,
	"manual_discount_requires_approval": 1,
	"attendant_discount_limit": 2.0,
	"supervisor_discount_limit": 10.0,
	"discount_account": None,
	"discount_cost_center": None,
	"credit_note_requires_approval": 1,
	"e_invoice_required": 0,
	"e_invoice_submission_mode": "ON_SUBMIT",
	"advance_is_tax_event": 0,
	"shift_mode_enabled": 1,
	"shift_opening_requires_supervisor": 1,
	"shift_closing_requires_supervisor": 1,
	"allow_multiple_attendants_per_pump": 0,
	"handover_requires_meter_reading": 1,
	"handover_requires_cash_count": 1,
	"cash_box_required": 1,
	"safe_required": 1,
	"opening_float_required": 1,
	"cash_count_by_denominations": 1,
	"cash_transfer_requires_receiver_confirmation": 1,
	"cash_variance_tolerance_amount": 10.0,
	"cash_variance_tolerance_percentage": 1.0,
	"variance_requires_approval": 1,
	"variance_requires_supervisor_approval": 1,
	"variance_requires_manager_approval": 1,
	"supervisor_variance_limit_amount": 100.0,
	"allow_reopen_closed_shift": 1,
	"allow_reopen_closed_cash_box": 1,
	"allow_reopen_closed_safe": 1,
	"close_shift_only": 1,
	"create_invoice_drafts_on_close": 1,
	"submit_invoices_on_close": 0,
	"post_stock_on_invoice_submit": 1,
	"create_payment_entries_on_close": 0,
	"block_close_with_unclassified_events": 1,
	"block_close_with_open_issue_orders": 1,
	"migration_cutover_date": None,
	"offline_mode_enabled": 0,
	"integration_log_retention_days": 90,
}


def get_effective_settings(
	company=None,
	station=None,
	pump=None,
	customer=None,
	operation_type=None,
	role=None,
):
	"""Return effective Fuel Operations Settings with hierarchical scope overrides:
	Company -> Station -> Pump -> Customer -> Operation Type -> Role.
	"""
	result = frappe._dict(DEFAULT_SETTINGS.copy())
	if not frappe.db.exists("DocType", "Fuel Operations Settings"):
		return result

	try:
		doc = frappe.get_single("Fuel Operations Settings")
	except Exception:
		return result

	for key in DEFAULT_SETTINGS:
		val = getattr(doc, key, None)
		if val is not None and val != "":
			result[key] = val

	if not company and station and frappe.db.exists("Fuel Station", station):
		company = frappe.db.get_value("Fuel Station", station, "company")

	rules = getattr(doc, "scope_rules", []) or []
	# Apply in order of specificity: Company, Station, Pump, Customer, Operation Type, Role
	priority_order = ["Company", "Station", "Pump", "Customer", "Operation Type", "Role"]
	override_fields = [
		"invoice_creator_mode",
		"invoice_submitter_mode",
		"invoice_timing",
		"transaction_capture_timing",
		"stock_posting_timing",
	]

	for scope_level in priority_order:
		for rule in rules:
			if not cint(rule.active) or rule.scope_type != scope_level:
				continue
			matched = False
			if scope_level == "Company" and company and rule.company == company:
				matched = True
			elif scope_level == "Station" and station and rule.station == station:
				matched = True
			elif scope_level == "Pump" and pump and rule.pump == pump:
				matched = True
			elif scope_level == "Customer" and customer and rule.customer == customer:
				matched = True
			elif scope_level == "Operation Type" and operation_type and rule.operation_type == operation_type:
				matched = True
			elif scope_level == "Role" and role and rule.role == role:
				matched = True

			if matched:
				for fld in override_fields:
					rval = getattr(rule, fld, None)
					if rval:
						result[fld] = rval
				if getattr(rule, "shift_mode_enabled", None) in ("0", "1", 0, 1):
					result["shift_mode_enabled"] = cint(rule.shift_mode_enabled)

	return result

