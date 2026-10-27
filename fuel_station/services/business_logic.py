import hashlib
import json
import secrets
import uuid

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime, nowdate

from fuel_station.services.settings_service import get_effective_settings


def log_audit_event(
	event_type,
	reference_doctype=None,
	reference_name=None,
	station=None,
	previous_value=None,
	new_value=None,
	reason=None,
	source_device="Server",
):
	"""Record an immutable audit entry in Fuel Audit Log (§17.3)."""
	if not frappe.db.exists("DocType", "Fuel Audit Log"):
		return None
	try:
		log = frappe.get_doc(
			{
				"doctype": "Fuel Audit Log",
				"event_type": event_type,
				"reference_doctype": reference_doctype,
				"reference_name": str(reference_name) if reference_name else None,
				"station": station,
				"user": frappe.session.user,
				"event_timestamp": now_datetime(),
				"source_device": source_device,
				"previous_value": json.dumps(previous_value, ensure_ascii=False, default=str)
				if isinstance(previous_value, (dict, list))
				else (str(previous_value) if previous_value is not None else None),
				"new_value": json.dumps(new_value, ensure_ascii=False, default=str)
				if isinstance(new_value, (dict, list))
				else (str(new_value) if new_value is not None else None),
				"reason": reason,
			}
		)
		log.flags.ignore_permissions = True
		log.insert(ignore_permissions=True)
		return log.name
	except Exception:
		return None


def validate_meter_sequence(
	pump,
	reading_value,
	previous_reading=None,
	reading_type="Closing",
	is_meter_reset=0,
	correction_reason=None,
	approved_by=None,
	station=None,
):
	"""Validate meter reading sequence (§10, §17.2, §30.7).
	Prevents reading < previous_reading unless documented meter reset or approved Correction.
	"""
	settings = get_effective_settings(station=station, pump=pump)
	if previous_reading is None and pump and frappe.db.exists("Fuel Pump", pump):
		previous_reading = flt(frappe.db.get_value("Fuel Pump", pump, "current_meter_reading"))

	prev = flt(previous_reading)
	curr = flt(reading_value)

	if curr < prev:
		if reading_type == "Correction" or cint(is_meter_reset):
			if not cint(settings.allow_meter_correction) and not cint(is_meter_reset):
				frappe.throw(_("Meter correction is disabled in Fuel Operations Settings."))
			if not correction_reason:
				frappe.throw(_("Correction reason is required when reading is less than previous reading."))
			if cint(settings.meter_correction_requires_approval) and not approved_by:
				frappe.throw(_("Supervisor/Manager approval is required for meter correction or reset."))
		else:
			frappe.throw(
				_("Current meter reading ({0}) cannot be less than previous reading ({1}) for pump {2}.").format(
					curr, prev, pump
				)
			)
	return True


def calculate_meter_quantity(opening_reading, closing_reading, is_meter_reset=0, max_meter_value=0):
	"""Calculate dispensed quantity from meter readings: Q_meter = Closing - Opening (§10.1, §17.2)."""
	open_val = flt(opening_reading)
	close_val = flt(closing_reading)
	if close_val < open_val:
		if cint(is_meter_reset) and flt(max_meter_value) > open_val:
			return flt(max_meter_value - open_val + close_val, 4)
		frappe.throw(
			_("Closing reading ({0}) cannot be less than opening reading ({1}).").format(close_val, open_val)
		)
	return flt(close_val - open_val, 4)


def classify_dispense_event(event_or_name, payment_method=None, customer=None, issue_order=None, authorization=None):
	"""Classify a Fuel Dispense Event and validate its references (§17.2)."""
	doc = (
		frappe.get_doc("Fuel Dispense Event", event_or_name)
		if isinstance(event_or_name, str)
		else event_or_name
	)
	if payment_method:
		doc.payment_method = payment_method
	if customer:
		doc.customer = customer
	if issue_order:
		doc.issue_order = issue_order
	if authorization:
		doc.authorization = authorization

	settings = get_effective_settings(
		station=doc.station,
		pump=doc.pump,
		customer=doc.customer,
		operation_type=doc.payment_method,
	)

	if doc.payment_method == "Card" and cint(settings.card_requires_reference) and not doc.payment_reference:
		frappe.throw(_("Payment Reference is required for Card transactions."))

	if doc.payment_method == "Credit":
		if not doc.customer:
			frappe.throw(_("Customer is required for Credit transactions."))
		if cint(settings.credit_requires_authorization) and not (
			doc.authorization or doc.issue_order or doc.contract or doc.fuel_card
		):
			frappe.throw(_("Credit sale requires an active Authorization, Issue Order, Contract, or Fuel Card."))

	if doc.payment_method == "Internal Issue":
		if cint(settings.internal_issue_requires_order) and not doc.issue_order:
			frappe.throw(_("Internal fuel issue requires an approved Fuel Issue Order."))

	if doc.status in ("Draft", "Recorded"):
		doc.status = "Classified"

	if not doc.is_new():
		doc.save(ignore_permissions=True)

	return doc


def calculate_cash_residual(
	opening_reading,
	closing_reading,
	card_quantity=0,
	credit_quantity=0,
	internal_quantity=0,
	issue_order_quantity=0,
	coupon_quantity=0,
	calibration_quantity=0,
	waste_quantity=0,
):
	"""Calculate expected cash quantity from meter residual (§10.1, §10.2, §17.2):
	Q_meter = Closing - Opening
	Q_cash = Q_meter - Q_card - Q_credit - Q_internal - Q_issue_order_non_cash - Q_coupon - Q_calibration - Q_waste
	"""
	q_meter = calculate_meter_quantity(opening_reading, closing_reading)
	classified_non_cash = flt(
		flt(card_quantity)
		+ flt(credit_quantity)
		+ flt(internal_quantity)
		+ flt(issue_order_quantity)
		+ flt(coupon_quantity)
		+ flt(calibration_quantity)
		+ flt(waste_quantity),
		4,
	)
	q_cash = flt(q_meter - classified_non_cash, 4)
	return frappe._dict(
		{
			"meter_quantity": q_meter,
			"classified_quantity": classified_non_cash,
			"cash_quantity": q_cash,
		}
	)


def check_customer_credit_and_contract(
	customer,
	requested_amount,
	requested_quantity=0,
	company=None,
	station=None,
	item=None,
	vehicle=None,
	driver=None,
	contract=None,
	posting_date=None,
	override_approved_by=None,
	override_reason=None,
	validate_requirements=True,
):
	"""Perform real credit limit & contract validation against ERPNext GL/Sales Invoice balances (§26.6).
	available_credit = credit_limit - current_outstanding - pending_credit_commitments
	"""
	posting_date = getdate(posting_date or nowdate())
	cust_doc = frappe.get_doc("Customer", customer)

	if cint(cust_doc.disabled) or (
		hasattr(cust_doc, "active_fuel_customer")
		and cust_doc.get("active_fuel_customer") is not None
		and not cint(cust_doc.get("active_fuel_customer"))
	):
		return frappe._dict({"status": "Customer Inactive", "allowed": False, "message": _("Customer is inactive.")})

	if not company and station and frappe.db.exists("Fuel Station", station):
		company = frappe.db.get_value("Fuel Station", station, "company")
	if not company:
		company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
			"Global Defaults", "default_company"
		)

	# Check vehicle & driver requirements on Customer
	if validate_requirements:
		if cint(cust_doc.get("vehicle_required")) and not vehicle:
			frappe.throw(_("Vehicle is required for customer {0}.").format(customer))
		if vehicle and frappe.db.exists("Customer Vehicle", vehicle):
			veh_doc = frappe.get_doc("Customer Vehicle", vehicle)
			if not cint(veh_doc.active):
				frappe.throw(_("Vehicle {0} is inactive.").format(vehicle))
			if veh_doc.customer and veh_doc.customer != customer:
				frappe.throw(_("Vehicle {0} does not belong to customer {1}.").format(vehicle, customer))

		if cint(cust_doc.get("driver_required")) and not driver:
			frappe.throw(_("Driver is required for customer {0}.").format(customer))

	# Check contract if linked or active contract for customer
	contract_doc = None
	if contract and frappe.db.exists("Fuel Customer Contract", contract):
		contract_doc = frappe.get_doc("Fuel Customer Contract", contract)
	else:
		active_contracts = frappe.get_all(
			"Fuel Customer Contract",
			filters={"customer": customer, "status": "Active"},
			fields=["name"],
			limit=1,
		)
		if active_contracts:
			contract_doc = frappe.get_doc("Fuel Customer Contract", active_contracts[0].name)

	policy = cust_doc.get("credit_control_policy") or cust_doc.get("credit_policy") or "BLOCK"
	credit_limit = 0.0
	daily_limit = flt(cust_doc.get("daily_fuel_limit"))
	monthly_limit = flt(cust_doc.get("monthly_fuel_limit"))

	# Standard ERPNext Customer Credit Limit child table
	for row in cust_doc.get("credit_limits", []) or []:
		if not company or row.company == company:
			credit_limit = flt(row.credit_limit)
			break

	if contract_doc:
		if getdate(contract_doc.start_date) > posting_date or getdate(contract_doc.end_date) < posting_date:
			return frappe._dict(
				{"status": "Contract Expired", "allowed": False, "message": _("Customer contract is expired or not yet active.")}
			)
		if contract_doc.allowed_items and item:
			allowed = [x.strip() for x in contract_doc.allowed_items.split(",") if x.strip()]
			if allowed and item not in allowed:
				frappe.throw(_("Item {0} is not allowed under contract {1}.").format(item, contract_doc.name))
		if contract_doc.allowed_stations and station:
			allowed_st = [x.strip() for x in contract_doc.allowed_stations.split(",") if x.strip()]
			if allowed_st and station not in allowed_st:
				frappe.throw(_("Station {0} is not allowed under contract {1}.").format(station, contract_doc.name))
		if contract_doc.allowed_vehicles and vehicle:
			allowed_vh = [x.strip() for x in contract_doc.allowed_vehicles.split(",") if x.strip()]
			if allowed_vh and vehicle not in allowed_vh:
				frappe.throw(_("Vehicle {0} is not registered in contract {1}.").format(vehicle, contract_doc.name))
		if flt(contract_doc.credit_limit) > 0:
			credit_limit = flt(contract_doc.credit_limit)
		if flt(contract_doc.daily_limit) > 0:
			daily_limit = flt(contract_doc.daily_limit)
		if flt(contract_doc.monthly_limit) > 0:
			monthly_limit = flt(contract_doc.monthly_limit)
		if contract_doc.credit_control_policy:
			policy = contract_doc.credit_control_policy

	if cust_doc.get("fuel_customer_type") == "Cash" or policy == "Credit Not Allowed":
		return frappe._dict({"status": "Credit Not Allowed", "allowed": False, "message": _("Credit is not allowed for this customer.")})

	# Calculate current_outstanding from ERPNext Sales Invoice / GL Entry
	outstanding_rows = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(outstanding_amount), 0) as total_out,
		       COALESCE(SUM(CASE WHEN due_date < %s AND outstanding_amount > 0 THEN outstanding_amount ELSE 0 END), 0) as overdue_out
		FROM `tabSales Invoice`
		WHERE customer = %s AND docstatus = 1
		"""
		+ (" AND company = %s" if company else ""),
		([posting_date, customer, company] if company else [posting_date, customer]),
		as_dict=True,
	)
	current_outstanding = flt(outstanding_rows[0].total_out) if outstanding_rows else 0.0
	overdue_outstanding = flt(outstanding_rows[0].overdue_out) if outstanding_rows else 0.0

	# Pending draft sales invoices + uninvoiced credit dispense events
	draft_inv = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(grand_total), 0) as draft_amt
		FROM `tabSales Invoice`
		WHERE customer = %s AND docstatus = 0
		""",
		(customer,),
		as_dict=True,
	)
	pending_draft_amount = flt(draft_inv[0].draft_amt) if draft_inv else 0.0

	uninvoiced_events = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(amount), 0) as ev_amt
		FROM `tabFuel Dispense Event`
		WHERE customer = %s AND payment_method IN ('Credit', 'Contract')
		  AND status NOT IN ('Invoiced', 'Cancelled')
		  AND (invoice IS NULL OR invoice = '')
		""",
		(customer,),
		as_dict=True,
	)
	pending_commitments = flt(pending_draft_amount + (flt(uninvoiced_events[0].ev_amt) if uninvoiced_events else 0.0))

	available_credit = flt(credit_limit - current_outstanding - pending_commitments, 2)

	# Daily & Monthly consumption checks
	if daily_limit > 0:
		daily_used = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(amount), 0) as amt, COALESCE(SUM(quantity), 0) as qty
			FROM `tabFuel Dispense Event`
			WHERE customer = %s AND business_date = %s AND status != 'Cancelled'
			""",
			(customer, posting_date),
			as_dict=True,
		)[0]
		if flt(daily_used.amt) + flt(requested_amount) > daily_limit and flt(daily_used.qty) + flt(requested_quantity) > daily_limit:
			return _apply_credit_policy(
				"Daily Limit Exceeded",
				policy,
				override_approved_by,
				override_reason,
				available_credit,
				current_outstanding,
				pending_commitments,
			)

	if monthly_limit > 0:
		month_start = posting_date.replace(day=1)
		monthly_used = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(amount), 0) as amt, COALESCE(SUM(quantity), 0) as qty
			FROM `tabFuel Dispense Event`
			WHERE customer = %s AND business_date >= %s AND business_date <= %s AND status != 'Cancelled'
			""",
			(customer, month_start, posting_date),
			as_dict=True,
		)[0]
		if flt(monthly_used.amt) + flt(requested_amount) > monthly_limit and flt(monthly_used.qty) + flt(requested_quantity) > monthly_limit:
			return _apply_credit_policy(
				"Monthly Limit Exceeded",
				policy,
				override_approved_by,
				override_reason,
				available_credit,
				current_outstanding,
				pending_commitments,
			)

	if overdue_outstanding > 0 and cint(cust_doc.get("credit_days", 0)) > 0:
		return _apply_credit_policy(
			"Overdue Balance",
			policy,
			override_approved_by,
			override_reason,
			available_credit,
			current_outstanding,
			pending_commitments,
		)

	if credit_limit > 0 and flt(requested_amount) > available_credit:
		return _apply_credit_policy(
			"Credit Limit Exceeded",
			policy,
			override_approved_by,
			override_reason,
			available_credit,
			current_outstanding,
			pending_commitments,
		)

	return frappe._dict(
		{
			"status": "Approved",
			"allowed": True,
			"credit_limit": credit_limit,
			"current_outstanding": current_outstanding,
			"overdue_outstanding": overdue_outstanding,
			"pending_draft_amount": pending_commitments,
			"available_credit": available_credit,
		}
	)


def _apply_credit_policy(status, policy, override_approved_by, override_reason, available_credit, current_outstanding, pending_commitments):
	if policy == "WARN_AND_ALLOW":
		return frappe._dict(
			{
				"status": status,
				"allowed": True,
				"warning": True,
				"available_credit": available_credit,
				"current_outstanding": current_outstanding,
				"pending_draft_amount": pending_commitments,
			}
		)
	if policy in ("REQUIRE_SUPERVISOR_APPROVAL", "REQUIRE_FINANCE_APPROVAL") and override_approved_by:
		return frappe._dict(
			{
				"status": "Approved",
				"original_status": status,
				"allowed": True,
				"available_credit": available_credit,
				"current_outstanding": current_outstanding,
				"pending_draft_amount": pending_commitments,
			}
		)
	if policy == "ALLOW_WITH_REASON" and override_reason:
		return frappe._dict(
			{
				"status": "Approved",
				"original_status": status,
				"allowed": True,
				"available_credit": available_credit,
				"current_outstanding": current_outstanding,
				"pending_draft_amount": pending_commitments,
			}
		)
	return frappe._dict(
		{
			"status": status,
			"allowed": False,
			"policy": policy,
			"available_credit": available_credit,
			"current_outstanding": current_outstanding,
			"pending_draft_amount": pending_commitments,
			"message": _("Credit check failed with status: {0} (Policy: {1})").format(status, policy),
		}
	)


def calculate_price_discount_and_tax(
	item,
	quantity,
	station=None,
	customer=None,
	contract=None,
	price_list=None,
	rate=None,
	discount_percentage=0,
	discount_amount=0,
	additional_discount_amount=0,
	discount_source=None,
	discount_reason=None,
	discount_approved_by=None,
	tax_template=None,
	prices_include_tax=None,
	posting_date=None,
	user_role=None,
):
	"""Execute the 10-step pricing, discount, and tax calculation engine (§28.5 - §28.9)."""
	settings = get_effective_settings(station=station, customer=customer)
	precision = cint(settings.tax_rounding_precision or 2)
	qty = flt(quantity)
	if qty <= 0:
		frappe.throw(_("Quantity must be greater than zero."))

	# Step 1-4: Determine effective Price List, Contract, and Unit Price
	contract_doc = None
	if contract and frappe.db.exists("Fuel Customer Contract", contract):
		contract_doc = frappe.get_doc("Fuel Customer Contract", contract)
		if contract_doc.price_list and not price_list:
			price_list = contract_doc.price_list

	if not price_list and customer and frappe.db.exists("Customer", customer):
		price_list = frappe.db.get_value("Customer", customer, "default_price_list")
	if not price_list and station and frappe.db.exists("Fuel Station", station):
		price_list = frappe.db.get_value("Fuel Station", station, "default_price_list")
	if not price_list:
		price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"

	if rate is None or flt(rate) == 0:
		rate = get_effective_item_price(item, price_list, posting_date=posting_date)

	rate_before_discount = flt(rate)

	# Contract discount fallback if no explicit discount passed
	if contract_doc and not flt(discount_percentage) and not flt(discount_amount):
		if flt(contract_doc.discount_percentage) > 0:
			discount_percentage = flt(contract_doc.discount_percentage)
			discount_source = "Customer Contract"
		elif flt(contract_doc.discount_amount) > 0:
			discount_amount = flt(contract_doc.discount_amount)
			discount_source = "Customer Contract"

	# Validate conflicting line discounts (§28.6 Rule 1)
	if flt(discount_percentage) > 0 and flt(discount_amount) > 0:
		expected_disc_amt = flt(rate_before_discount * flt(discount_percentage) / 100.0, 4)
		if abs(expected_disc_amt - flt(discount_amount)) > 0.01:
			frappe.throw(_("Cannot specify conflicting discount_percentage and discount_amount simultaneously."))

	# Check discount authorization limits (§28.8)
	eff_disc_pct = flt(discount_percentage)
	if not eff_disc_pct and flt(discount_amount) > 0 and rate_before_discount > 0:
		eff_disc_pct = (flt(discount_amount) / rate_before_discount) * 100.0

	if eff_disc_pct > 0 and discount_source not in ("Customer Contract", "Price List", "Pricing Rule"):
		roles = frappe.get_roles(frappe.session.user)
		is_attendant_only = user_role == "Fuel Attendant" or (
			"Fuel Attendant" in roles
			and "Shift Supervisor" not in roles
			and "Station Manager" not in roles
			and "Fuel Operations Manager" not in roles
			and "System Manager" not in roles
		)
		if is_attendant_only:
			if not cint(settings.allow_attendant_discount) and not discount_approved_by:
				frappe.throw(_("Attendant is not allowed to grant manual discounts without approval."))
			if eff_disc_pct > flt(settings.attendant_discount_limit) and not discount_approved_by:
				frappe.throw(
					_("Discount ({0}%) exceeds Attendant Discount Limit ({1}%). Approval required.").format(
						eff_disc_pct, settings.attendant_discount_limit
					)
				)
			if cint(settings.attendant_discount_requires_reason) and not discount_reason:
				frappe.throw(_("Discount reason is required for attendant discounts."))
		elif eff_disc_pct > flt(settings.supervisor_discount_limit) and not discount_approved_by:
			if cint(settings.manual_discount_requires_approval):
				frappe.throw(
					_("Discount ({0}%) exceeds Supervisor Limit ({1}%). Manager approval required.").format(
						eff_disc_pct, settings.supervisor_discount_limit
					)
				)

	# Step 5: Line discount calculation
	if flt(discount_percentage) > 0:
		unit_discount = flt(rate_before_discount * flt(discount_percentage) / 100.0, 6)
	else:
		unit_discount = flt(discount_amount, 6)

	rate_after_discount = flt(rate_before_discount - unit_discount, 6)
	if rate_after_discount < 0:
		frappe.throw(_("Net unit rate after discount cannot be negative."))

	amount_before_discount = flt(qty * rate_before_discount, precision)
	line_discount_total = flt(qty * unit_discount, precision)
	amount_after_line_discount = flt(amount_before_discount - line_discount_total, precision)

	# Step 6: Invoice-level discount
	net_after_all_discounts = flt(amount_after_line_discount - flt(additional_discount_amount), precision)
	if net_after_all_discounts < 0:
		frappe.throw(_("Net amount after discount cannot be negative."))

	# Step 7-8: Tax rate from ERPNext Sales Taxes and Charges Template (not hardcoded)
	if not tax_template:
		tax_template = settings.default_sales_tax_template
	tax_rate = 0.0
	template_inclusive = False
	if tax_template and frappe.db.exists("Sales Taxes and Charges Template", tax_template):
		tmpl = frappe.get_doc("Sales Taxes and Charges Template", tax_template)
		for trow in tmpl.get("taxes", []) or []:
			tax_rate += flt(trow.rate)
			if cint(trow.included_in_print_rate):
				template_inclusive = True

	# Check customer exemption
	if customer and frappe.db.exists("Customer", customer):
		tax_cat = frappe.db.get_value("Customer", customer, "tax_category")
		if tax_cat and "Exempt" in str(tax_cat):
			tax_rate = 0.0

	is_inclusive = (
		cint(prices_include_tax)
		if prices_include_tax is not None
		else (template_inclusive or settings.selling_price_tax_mode == "TAX_INCLUSIVE" or cint(settings.prices_include_tax))
	)

	if is_inclusive and tax_rate > 0:
		taxable_amount = flt(net_after_all_discounts / (1.0 + (tax_rate / 100.0)), precision)
		tax_amount = flt(net_after_all_discounts - taxable_amount, precision)
		grand_total = flt(net_after_all_discounts, precision)
	else:
		taxable_amount = flt(net_after_all_discounts, precision)
		tax_amount = flt(taxable_amount * (tax_rate / 100.0), precision)
		grand_total = flt(taxable_amount + tax_amount, precision)

	return frappe._dict(
		{
			"price_list": price_list,
			"rate_before_discount": rate_before_discount,
			"discount_percentage": flt(discount_percentage),
			"discount_amount": unit_discount,
			"line_discount_total": line_discount_total,
			"rate_after_discount": rate_after_discount,
			"amount_before_discount": amount_before_discount,
			"amount_after_discount": net_after_all_discounts,
			"tax_template": tax_template,
			"tax_rate": tax_rate,
			"prices_include_tax": cint(is_inclusive),
			"taxable_amount": taxable_amount,
			"tax_amount": tax_amount,
			"grand_total": grand_total,
		}
	)


def get_effective_item_price(item_code, price_list=None, posting_date=None):
	"""Fetch effective Item Price from ERPNext Item Price considering valid_from / valid_upto."""
	posting_date = getdate(posting_date or nowdate())
	filters = {"item_code": item_code, "selling": 1}
	if price_list:
		filters["price_list"] = price_list

	prices = frappe.get_all(
		"Item Price",
		filters=filters,
		fields=["price_list_rate", "valid_from", "valid_upto"],
		order_by="valid_from desc, modified desc",
	)
	for p in prices:
		if p.valid_from and getdate(p.valid_from) > posting_date:
			continue
		if p.valid_upto and getdate(p.valid_upto) < posting_date:
			continue
		return flt(p.price_list_rate)

	return flt(frappe.db.get_value("Item", item_code, "standard_rate") or 0)


def validate_issue_order(issue_order_name, requested_quantity=0, requested_amount=0, qr_token=None, posting_date=None):
	"""Validate Fuel Issue Order before dispensing (§9, §17.2)."""
	doc = (
		frappe.get_doc("Fuel Issue Order", issue_order_name)
		if isinstance(issue_order_name, str)
		else issue_order_name
	)
	posting_date = getdate(posting_date or nowdate())
	settings = get_effective_settings(station=doc.station)

	if qr_token and doc.qr_code and qr_token != doc.qr_code:
		log_audit_event(
			"Invalid QR Token Attempt",
			"Fuel Issue Order",
			doc.name,
			station=doc.station,
			reason="Mismatched QR token",
		)
		frappe.throw(_("Invalid QR code token for Fuel Issue Order {0}.").format(doc.name))

	if doc.approval_status in ("Expired", "Cancelled", "Rejected", "Fully Used"):
		log_audit_event(
			"Expired or Used Issue Order Attempt",
			"Fuel Issue Order",
			doc.name,
			station=doc.station,
			reason=f"Status is {doc.approval_status}",
		)
		frappe.throw(_("Fuel Issue Order {0} is {1} and cannot be used.").format(doc.name, doc.approval_status))

	if doc.approval_status not in ("Approved", "Partially Used"):
		if not (cint(doc.is_emergency) and cint(settings.allow_emergency_issue)):
			frappe.throw(_("Fuel Issue Order {0} must be Approved before dispensing.").format(doc.name))

	if doc.valid_from and getdate(doc.valid_from) > posting_date:
		frappe.throw(_("Fuel Issue Order {0} is not valid until {1}.").format(doc.name, doc.valid_from))

	if doc.valid_until and getdate(doc.valid_until) < posting_date:
		doc.db_set("approval_status", "Expired")
		log_audit_event("Expired QR/Issue Order Attempt", "Fuel Issue Order", doc.name, station=doc.station)
		frappe.throw(_("Fuel Issue Order {0} expired on {1}.").format(doc.name, doc.valid_until))

	if cint(doc.max_uses) > 0 and cint(doc.used_count) >= cint(doc.max_uses):
		frappe.throw(_("Fuel Issue Order {0} has reached its maximum allowed uses ({1}).").format(doc.name, doc.max_uses))

	rem_qty = flt(doc.quantity_limit) - flt(doc.used_quantity)
	if flt(requested_quantity) > rem_qty + 0.0001:
		if not cint(settings.allow_over_issue_with_approval):
			frappe.throw(
				_("Requested quantity ({0}) exceeds remaining quantity ({1}) on Issue Order {2}.").format(
					requested_quantity, rem_qty, doc.name
				)
			)

	if flt(doc.amount_limit) > 0 and flt(requested_amount) > flt(doc.amount_limit):
		frappe.throw(
			_("Requested amount ({0}) exceeds amount limit ({1}) on Issue Order {2}.").format(
				requested_amount, doc.amount_limit, doc.name
			)
		)

	return doc


def consume_issue_order_quantity(issue_order_name, dispensed_quantity, create_stock_entry=True):
	"""Consume quantity from Fuel Issue Order, supporting partial or full execution (§9.1, §17.2)."""
	doc = frappe.get_doc("Fuel Issue Order", issue_order_name)
	validate_issue_order(doc, requested_quantity=dispensed_quantity)

	new_used = flt(doc.used_quantity) + flt(dispensed_quantity)
	rem = max(0.0, flt(doc.quantity_limit) - new_used)
	doc.used_quantity = new_used
	doc.remaining_quantity = rem
	doc.used_count = cint(doc.used_count) + 1

	if rem <= 0.0001:
		doc.approval_status = "Fully Used"
	else:
		doc.approval_status = "Partially Used"

	doc.save(ignore_permissions=True)

	se_name = None
	if create_stock_entry and doc.treatment_type == "Internal":
		se_name = create_stock_entry_from_internal_issue(doc, quantity=dispensed_quantity)

	return doc, se_name


def create_stock_entry_from_internal_issue(issue_order_or_event, quantity=None, warehouse=None, submit=True):
	"""Create standard ERPNext Stock Entry (Material Issue) for internal fuel consumption (§9.5, §11.6, §17.2).
	Idempotent via source_key. Never creates a Sales Invoice for internal consumption.
	"""
	doc = (
		frappe.get_doc("Fuel Issue Order", issue_order_or_event)
		if isinstance(issue_order_or_event, str)
		else issue_order_or_event
	)

	is_event = doc.doctype == "Fuel Dispense Event"
	source_key = f"INT-SE-{doc.doctype}-{doc.name}-{flt(quantity or getattr(doc, 'quantity', 0) or doc.used_quantity)}"

	existing = frappe.db.get_value("Stock Entry", {"source_key": source_key, "docstatus": ["!=", 2]}, "name")
	if existing:
		return existing

	if not is_event and doc.get("stock_entry") and frappe.db.exists("Stock Entry", doc.stock_entry):
		if flt(quantity or doc.used_quantity) == flt(doc.quantity_limit):
			return doc.stock_entry

	station_doc = frappe.get_doc("Fuel Station", doc.station) if doc.get("station") else None
	company = (
		doc.get("company")
		or (station_doc.company if station_doc else None)
		or frappe.defaults.get_user_default("Company")
	)

	if not warehouse:
		warehouse = doc.get("warehouse")
	if not warehouse and doc.get("station"):
		warehouse = frappe.db.get_value(
			"Fuel Tank", {"station": doc.station, "item": doc.item, "active": 1}, "warehouse"
		)
	if not warehouse:
		warehouse = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name")

	expense_account = (
		doc.get("expense_account")
		or (station_doc.default_expense_account if station_doc else None)
		or frappe.db.get_value("Company", company, "default_expense_account")
	)
	cost_center = (
		doc.get("cost_center")
		or (station_doc.default_cost_center if station_doc else None)
		or frappe.db.get_value("Company", company, "cost_center")
	)

	qty_to_issue = flt(quantity or (doc.quantity if is_event else doc.used_quantity) or doc.quantity_limit)

	se = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Issue",
			"purpose": "Material Issue",
			"company": company,
			"posting_date": doc.get("business_date") or nowdate(),
			"fuel_station": doc.get("station"),
			"fuel_issue_order": doc.name if not is_event else doc.get("issue_order"),
			"fuel_dispense_event": doc.name if is_event else None,
			"vehicle": doc.get("vehicle"),
			"employee": doc.get("employee"),
			"department": doc.get("requesting_department"),
			"source_key": source_key,
			"items": [
				{
					"item_code": doc.item,
					"s_warehouse": warehouse,
					"qty": qty_to_issue,
					"uom": frappe.db.get_value("Item", doc.item, "stock_uom") or "Liter",
					"expense_account": expense_account,
					"cost_center": cost_center,
					"project": doc.get("project"),
				}
			],
		}
	)
	se.flags.ignore_permissions = True
	se.insert(ignore_permissions=True)
	if submit:
		se.submit()

	if is_event:
		doc.db_set("stock_document", se.name)
		doc.db_set("status", "Stock Posted")
	else:
		doc.db_set("stock_entry", se.name)

	return se.name


def create_purchase_receipt_from_delivery(delivery_or_name, submit=True):
	"""Create standard ERPNext Purchase Receipt from Fuel Delivery (§11.5, §17.2, §25.7).
	Idempotent: never creates duplicate stock increases. Opens an exception if document_quantity != received_quantity.
	"""
	doc = (
		frappe.get_doc("Fuel Delivery", delivery_or_name)
		if isinstance(delivery_or_name, str)
		else delivery_or_name
	)

	if doc.purchase_receipt and frappe.db.exists("Purchase Receipt", doc.purchase_receipt):
		pr_status = frappe.db.get_value("Purchase Receipt", doc.purchase_receipt, "docstatus")
		if pr_status != 2:
			return doc.purchase_receipt

	source_key = doc.source_key or f"FDL-PR-{doc.name}"
	existing = frappe.db.get_value("Purchase Receipt", {"source_key": source_key, "docstatus": ["!=", 2]}, "name")
	if existing:
		doc.db_set("purchase_receipt", existing)
		return existing

	variance = flt(doc.received_quantity) - flt(doc.document_quantity)
	doc.variance_quantity = variance

	if abs(variance) > flt(doc.allowed_tolerance_quantity) and not doc.approved_by:
		if not doc.exception_reference:
			exc = frappe.get_doc(
				{
					"doctype": "Fuel Reconciliation Exception",
					"exception_type": "Delivery Variance",
					"station": doc.station,
					"business_date": doc.delivery_date,
					"source_documents": doc.name,
					"expected_quantity": flt(doc.document_quantity),
					"actual_quantity": flt(doc.received_quantity),
					"difference": variance,
					"severity": "High",
					"status": "Open",
				}
			)
			exc.insert(ignore_permissions=True)
			doc.db_set("exception_reference", exc.name)
			doc.db_set("status", "Exception")
		frappe.throw(
			_("Delivery quantity ({0}) differs from supplier document quantity ({1}). Exception {2} created; approval required.").format(
				doc.received_quantity, doc.document_quantity, doc.exception_reference
			)
		)

	station_doc = frappe.get_doc("Fuel Station", doc.station)
	company = doc.company or station_doc.company
	warehouse = doc.warehouse or frappe.db.get_value("Fuel Tank", doc.tank, "warehouse")
	cost_center = station_doc.default_cost_center or frappe.db.get_value("Company", company, "cost_center")

	pr = frappe.get_doc(
		{
			"doctype": "Purchase Receipt",
			"supplier": doc.supplier,
			"company": company,
			"posting_date": doc.delivery_date or nowdate(),
			"fuel_station": doc.station,
			"fuel_delivery": doc.name,
			"source_key": source_key,
			"items": [
				{
					"item_code": doc.item,
					"warehouse": warehouse,
					"qty": flt(doc.received_quantity),
					"received_qty": flt(doc.received_quantity),
					"uom": doc.uom or "Liter",
					"rate": flt(doc.rate),
					"cost_center": cost_center,
					"purchase_order": doc.purchase_order,
				}
			],
		}
	)
	pr.flags.ignore_permissions = True
	pr.insert(ignore_permissions=True)
	if submit:
		pr.submit()

	doc.db_set("purchase_receipt", pr.name)
	doc.db_set("source_key", source_key)
	doc.db_set("status", "Received")
	return pr.name


def create_sales_invoice_from_batch(batch_or_name, submit=None, user=None):
	"""Create a standard ERPNext Sales Invoice from Fuel Pump Invoice Batch or Fuel Dispense Event (§11, §17.2, §28).
	Strictly idempotent via source_key. Updates stock according to stock_posting_timing.
	"""
	batch = (
		frappe.get_doc("Fuel Pump Invoice Batch", batch_or_name)
		if isinstance(batch_or_name, str)
		else batch_or_name
	)

	if batch.sales_invoice and frappe.db.exists("Sales Invoice", batch.sales_invoice):
		inv_docstatus = frappe.db.get_value("Sales Invoice", batch.sales_invoice, "docstatus")
		if inv_docstatus != 2:
			return batch.sales_invoice

	source_key = batch.source_key or f"BATCH-{batch.name}"
	existing_inv = frappe.db.get_value("Sales Invoice", {"source_key": source_key, "docstatus": ["!=", 2]}, "name")
	if existing_inv:
		batch.db_set("sales_invoice", existing_inv)
		batch.db_set("status", "Invoiced")
		return existing_inv

	if flt(batch.invoice_quantity) <= 0:
		frappe.throw(_("Cannot create a Sales Invoice with zero or negative quantity ({0}).").format(batch.invoice_quantity))

	station_doc = frappe.get_doc("Fuel Station", batch.station)
	company = station_doc.company
	settings = get_effective_settings(
		company=company,
		station=batch.station,
		pump=batch.pump,
		customer=batch.customer,
		operation_type=batch.payment_method,
	)

	# Verify creator permission / mode
	_verify_invoice_creator_permission(settings, user=user, amount=batch.invoice_amount, quantity=batch.invoice_quantity)

	customer = batch.customer or station_doc.default_cash_customer
	if not customer:
		customer = frappe.db.get_value("Customer", {"disabled": 0}, "name")
	if not customer:
		frappe.throw(_("Customer or Default Cash Customer is required to create Sales Invoice."))

	pump_doc = frappe.get_doc("Fuel Pump", batch.pump) if batch.pump else None
	warehouse = (pump_doc.warehouse if pump_doc else None) or (
		frappe.db.get_value("Fuel Tank", pump_doc.tank, "warehouse") if pump_doc and pump_doc.tank else None
	)
	if not warehouse:
		warehouse = frappe.db.get_value(
			"Fuel Tank", {"station": batch.station, "item": batch.item, "active": 1}, "warehouse"
		)

	cost_center = (
		batch.cost_center
		or station_doc.default_cost_center
		or frappe.db.get_value("Company", company, "cost_center")
	)
	income_account = station_doc.default_income_account or frappe.db.get_value(
		"Company", company, "default_income_account"
	)

	update_stock = 1 if settings.stock_posting_timing in ("ON_INVOICE_SUBMIT", "ON_DISPENSE") else 0

	# Build items list: if batch has events with distinct vehicles/drivers or rates, preserve references
	invoice_items = []
	batch_events = batch.get("events", []) or []
	if batch_events and len(batch_events) > 0 and batch.payment_method in ("Credit", "Card"):
		for row in batch_events:
			ev = frappe.get_doc("Fuel Dispense Event", row.fuel_dispense_event)
			item_dict = {
				"item_code": ev.item,
				"qty": flt(ev.quantity),
				"uom": ev.uom or "Liter",
				"rate": flt(ev.rate),
				"price_list_rate": flt(ev.rate_before_discount or ev.rate),
				"discount_percentage": flt(ev.discount_percentage),
				"discount_amount": flt(ev.discount_amount),
				"warehouse": ev.warehouse or warehouse,
				"cost_center": cost_center,
				"fuel_station": batch.station,
				"pump": ev.pump,
				"fuel_tank": ev.tank,
				"fuel_dispense_event": ev.name,
				"opening_meter_reading": flt(ev.reading_before),
				"closing_meter_reading": flt(ev.reading_after),
				"meter_quantity": flt(ev.quantity),
				"vehicle": ev.vehicle,
				"vehicle_plate_number": ev.vehicle_plate_number or ev.vehicle,
				"driver": ev.driver,
				"driver_reference": ev.driver_name or ev.driver,
				"vehicle_odometer_reading": flt(ev.odometer_reading),
				"attendant": ev.employee,
				"shift": ev.shift,
				"issue_order": ev.issue_order,
				"authorization": ev.authorization,
				"rate_before_discount": flt(ev.rate_before_discount or ev.rate),
				"rate_after_discount": flt(ev.rate),
				"amount_before_discount": flt(ev.amount_before_discount or ev.amount),
				"amount_after_discount": flt(ev.amount),
				"discount_source": ev.discount_source,
			}
			if income_account:
				item_dict["income_account"] = income_account
			invoice_items.append(item_dict)
	else:
		first_ev = (
			frappe.get_doc("Fuel Dispense Event", batch_events[0].fuel_dispense_event)
			if batch_events
			else None
		)
		rate = flt(batch.rate) or (
			flt(batch.invoice_amount) / flt(batch.invoice_quantity) if flt(batch.invoice_quantity) else 0
		)
		item_dict = {
			"item_code": batch.item,
			"qty": flt(batch.invoice_quantity),
			"uom": "Liter",
			"rate": rate,
			"price_list_rate": flt(first_ev.rate_before_discount if first_ev and first_ev.rate_before_discount else rate),
			"discount_percentage": flt(batch.discount_percentage),
			"discount_amount": flt(batch.discount_amount),
			"warehouse": warehouse,
			"cost_center": cost_center,
			"fuel_station": batch.station,
			"pump": batch.pump,
			"fuel_tank": pump_doc.tank if pump_doc else None,
			"fuel_dispense_event": first_ev.name if first_ev and len(batch_events) == 1 else None,
			"opening_meter_reading": flt(batch.opening_reading),
			"closing_meter_reading": flt(batch.closing_reading),
			"meter_quantity": flt(batch.meter_quantity or batch.invoice_quantity),
			"vehicle": batch.vehicle or (first_ev.vehicle if first_ev else None),
			"vehicle_plate_number": (first_ev.vehicle_plate_number or first_ev.vehicle) if first_ev else batch.vehicle,
			"driver": first_ev.driver if first_ev else None,
			"driver_reference": (first_ev.driver_name or first_ev.driver) if first_ev else None,
			"vehicle_odometer_reading": flt(first_ev.odometer_reading) if first_ev else 0,
			"attendant": batch.attendant or (first_ev.employee if first_ev else None),
			"shift": batch.shift,
			"issue_order": first_ev.issue_order if first_ev else None,
			"authorization": first_ev.authorization if first_ev else None,
			"rate_before_discount": flt(first_ev.rate_before_discount if first_ev and first_ev.rate_before_discount else rate),
			"rate_after_discount": rate,
			"amount_before_discount": flt(batch.invoice_quantity * rate),
			"amount_after_discount": flt(batch.invoice_amount or (batch.invoice_quantity * rate)),
			"discount_source": batch.discount_policy,
		}
		if income_account:
			item_dict["income_account"] = income_account
		invoice_items.append(item_dict)

	inv_data = {
		"doctype": "Sales Invoice",
		"customer": customer,
		"company": company,
		"posting_date": batch.business_date or nowdate(),
		"due_date": batch.business_date or nowdate(),
		"update_stock": update_stock,
		"cost_center": cost_center,
		"fuel_station": batch.station,
		"branch": station_doc.branch,
		"business_date": batch.business_date or nowdate(),
		"fuel_shift": batch.shift,
		"fuel_invoice_type": batch.invoice_type or "B2C Simplified",
		"contract_number": batch.contract,
		"payment_method_type": batch.payment_method,
		"card_provider": batch.card_provider,
		"source_key": source_key,
		"items": invoice_items,
	}

	tax_tmpl = batch.tax_template or settings.default_sales_tax_template
	if tax_tmpl and frappe.db.exists("Sales Taxes and Charges Template", tax_tmpl):
		inv_data["taxes_and_charges"] = tax_tmpl
		tmpl_doc = frappe.get_doc("Sales Taxes and Charges Template", tax_tmpl)
		inv_data["taxes"] = []
		for t in tmpl_doc.taxes:
			inv_data["taxes"].append(
				{
					"charge_type": t.charge_type,
					"account_head": t.account_head,
					"description": t.description,
					"rate": t.rate,
					"included_in_print_rate": 1
					if (cint(t.included_in_print_rate) or settings.selling_price_tax_mode == "TAX_INCLUSIVE")
					else 0,
					"cost_center": cost_center,
				}
			)

	inv = frappe.get_doc(inv_data)
	inv.flags.ignore_permissions = True
	inv.insert(ignore_permissions=True)

	# Allocate advance payments if Prepaid / Fuel Authorization has advance_payment_entry
	if batch.payment_method == "Prepaid" and batch_events:
		_allocate_advance_to_invoice(inv, batch_events)

	should_submit = submit if submit is not None else cint(settings.submit_invoices_on_close)
	if should_submit:
		_verify_invoice_submitter_permission(settings, user=user, amount=inv.grand_total, quantity=batch.invoice_quantity)
		inv.submit()

	batch.db_set("sales_invoice", inv.name)
	batch.db_set("source_key", source_key)
	batch.db_set("status", "Submitted" if inv.docstatus == 1 else "Invoiced")

	for row in batch_events:
		frappe.db.set_value(
			"Fuel Dispense Event",
			row.fuel_dispense_event,
			{
				"invoice": inv.name,
				"invoice_batch": batch.name,
				"status": "Stock Posted" if (inv.docstatus == 1 and update_stock) else "Invoiced",
			},
		)

	return inv.name


def _allocate_advance_to_invoice(inv, batch_events):
	"""Allocate advance Payment Entry from Fuel Authorization to Sales Invoice (§26.8, §28.12)."""
	for row in batch_events:
		auth_name = frappe.db.get_value("Fuel Dispense Event", row.fuel_dispense_event, "authorization")
		if auth_name and frappe.db.exists("Fuel Authorization", auth_name):
			pe_name = frappe.db.get_value("Fuel Authorization", auth_name, "advance_payment_entry")
			if pe_name and frappe.db.exists("Payment Entry", pe_name):
				pe = frappe.get_doc("Payment Entry", pe_name)
				if pe.docstatus == 1 and flt(pe.unallocated_amount) > 0:
					alloc = min(flt(pe.unallocated_amount), flt(inv.grand_total))
					inv.append(
						"advances",
						{
							"reference_type": "Payment Entry",
							"reference_name": pe.name,
							"advance_amount": flt(pe.unallocated_amount),
							"allocated_amount": alloc,
						},
					)
					inv.save(ignore_permissions=True)


def _verify_invoice_creator_permission(settings, user=None, amount=0, quantity=0):
	user = user or frappe.session.user
	roles = frappe.get_roles(user)
	if "System Manager" in roles or "System Administrator" in roles or "Fuel Operations Manager" in roles:
		return True

	creator_mode = settings.invoice_creator_mode
	is_attendant_only = (
		"Fuel Attendant" in roles
		and "Shift Supervisor" not in roles
		and "Accountant" not in roles
		and "Cashier" not in roles
		and "Station Manager" not in roles
	)
	if is_attendant_only and creator_mode not in ("ATTENDANT", "HYBRID", "AUTOMATIC"):
		frappe.throw(_("Fuel Attendant is not permitted to create invoices under mode {0}.").format(creator_mode))

	if is_attendant_only:
		if flt(settings.attendant_max_invoice_amount) > 0 and flt(amount) > flt(settings.attendant_max_invoice_amount):
			frappe.throw(
				_("Invoice amount ({0}) exceeds Attendant limit ({1}).").format(
					amount, settings.attendant_max_invoice_amount
				)
			)
		if flt(settings.attendant_max_invoice_quantity) > 0 and flt(quantity) > flt(settings.attendant_max_invoice_quantity):
			frappe.throw(
				_("Invoice quantity ({0}) exceeds Attendant limit ({1}).").format(
					quantity, settings.attendant_max_invoice_quantity
				)
			)
	return True


def _verify_invoice_submitter_permission(settings, user=None, amount=0, quantity=0):
	user = user or frappe.session.user
	roles = frappe.get_roles(user)
	if "System Manager" in roles or "System Administrator" in roles or "Fuel Operations Manager" in roles:
		return True

	submitter_mode = settings.invoice_submitter_mode
	is_attendant_only = (
		"Fuel Attendant" in roles
		and "Shift Supervisor" not in roles
		and "Accountant" not in roles
		and "Cashier" not in roles
		and "Station Manager" not in roles
	)
	if is_attendant_only and (not cint(settings.attendant_can_submit) or submitter_mode != "ATTENDANT"):
		frappe.throw(_("Fuel Attendant is not permitted to submit financial invoices."))
	return True


def create_payment_entry_from_collection(
	sales_invoice=None,
	customer=None,
	paid_amount=0,
	payment_method="Cash",
	mode_of_payment=None,
	station=None,
	shift=None,
	cash_box=None,
	card_provider=None,
	reference_no=None,
	reference_date=None,
	is_advance=False,
	is_refund=False,
	source_key=None,
	submit=True,
):
	"""Create a standard ERPNext Payment Entry for Cash, Card, Bank Transfer, Partial Payment, Advance, or Refund (§11.4, §17.2, §26.9)."""
	if source_key:
		existing = frappe.db.get_value("Payment Entry", {"source_key": source_key, "docstatus": ["!=", 2]}, "name")
		if existing:
			return existing

	inv_doc = frappe.get_doc("Sales Invoice", sales_invoice) if sales_invoice else None
	if inv_doc:
		customer = customer or inv_doc.customer
		station = station or inv_doc.get("fuel_station")
		shift = shift or inv_doc.get("fuel_shift")
		if not flt(paid_amount):
			paid_amount = flt(inv_doc.outstanding_amount)

	station_doc = frappe.get_doc("Fuel Station", station) if station and frappe.db.exists("Fuel Station", station) else None
	company = (
		(inv_doc.company if inv_doc else None)
		or (station_doc.company if station_doc else None)
		or frappe.defaults.get_user_default("Company")
	)

	receivable_account = (
		(inv_doc.debit_to if inv_doc else None)
		or frappe.db.get_value("Company", company, "default_receivable_account")
	)

	# Determine target Cash / Card Clearing / Bank Account
	paid_to_account = None
	if payment_method == "Card":
		if card_provider and frappe.db.exists("Fuel Card Provider Settings", card_provider):
			paid_to_account = frappe.db.get_value("Fuel Card Provider Settings", card_provider, "clearing_account")
		if not paid_to_account and station_doc:
			paid_to_account = station_doc.default_card_clearing_account

	if not paid_to_account and station_doc:
		paid_to_account = station_doc.default_cash_account
	if not paid_to_account:
		paid_to_account = frappe.db.get_value("Company", company, "default_cash_account") or frappe.db.get_value(
			"Company", company, "default_bank_account"
		)

	payment_type = "Pay" if is_refund else "Receive"
	paid_from = paid_to_account if is_refund else receivable_account
	paid_to = receivable_account if is_refund else paid_to_account

	amt = abs(flt(paid_amount))
	pe_data = {
		"doctype": "Payment Entry",
		"payment_type": payment_type,
		"company": company,
		"posting_date": reference_date or (inv_doc.posting_date if inv_doc else nowdate()),
		"party_type": "Customer",
		"party": customer,
		"mode_of_payment": mode_of_payment,
		"paid_from": paid_from,
		"paid_to": paid_to,
		"paid_amount": amt,
		"received_amount": amt,
		"reference_no": reference_no or f"FUEL-{nowdate()}",
		"reference_date": reference_date or nowdate(),
		"fuel_station": station,
		"fuel_shift": shift,
		"fuel_cash_box": cash_box,
		"card_provider": card_provider,
		"source_key": source_key,
		"references": [],
	}

	if inv_doc and not is_advance and inv_doc.docstatus == 1:
		alloc = min(amt, abs(flt(inv_doc.outstanding_amount)))
		if is_refund and flt(inv_doc.outstanding_amount) < 0:
			alloc = min(amt, abs(flt(inv_doc.outstanding_amount)))
		if alloc > 0:
			pe_data["references"].append(
				{
					"reference_doctype": "Sales Invoice",
					"reference_name": inv_doc.name,
					"allocated_amount": -alloc if (is_refund and inv_doc.is_return) else alloc,
				}
			)

	pe = frappe.get_doc(pe_data)
	pe.flags.ignore_permissions = True
	pe.insert(ignore_permissions=True)
	if submit:
		pe.submit()
	return pe.name


def reconcile_pump_shift(
	station,
	pump,
	business_date=None,
	shift=None,
	opening_reading=None,
	closing_reading=None,
	rate=None,
	create_batch=True,
):
	"""Execute pump shift/day reconciliation (§10, §17.2).
	1. Calculates Q_meter = Closing - Opening.
	2. Sums already classified events (Card, Credit, Internal, Issue Order, Coupon, Calibration, Waste) so they are NEVER double-invoiced.
	3. Computes Q_cash = Q_meter - Classified.
	4. If Q_cash < 0: creates a Fuel Reconciliation Exception and blocks/holds per negative_cash_quantity_policy.
	5. If Q_cash > 0: creates proposed Cash Fuel Pump Invoice Batch per unclassified_quantity_policy.
	"""
	business_date = getdate(business_date or nowdate())
	settings = get_effective_settings(station=station, pump=pump)
	pump_doc = frappe.get_doc("Fuel Pump", pump)
	item = pump_doc.item

	# Determine opening & closing readings from Fuel Meter Reading if not explicitly passed
	if opening_reading is None:
		filters = {"station": station, "pump": pump, "reading_type": "Opening", "status": ["!=", "Cancelled"]}
		if shift:
			filters["shift"] = shift
		else:
			filters["business_date"] = business_date
		open_rec = frappe.get_all("Fuel Meter Reading", filters=filters, fields=["reading_value"], order_by="creation asc", limit=1)
		opening_reading = flt(open_rec[0].reading_value) if open_rec else flt(pump_doc.current_meter_reading)

	if closing_reading is None:
		filters = {"station": station, "pump": pump, "reading_type": "Closing", "status": ["!=", "Cancelled"]}
		if shift:
			filters["shift"] = shift
		else:
			filters["business_date"] = business_date
		close_rec = frappe.get_all("Fuel Meter Reading", filters=filters, fields=["reading_value"], order_by="creation desc", limit=1)
		if not close_rec:
			frappe.throw(_("Closing meter reading is required for pump {0}.").format(pump))
		closing_reading = flt(close_rec[0].reading_value)

	validate_meter_sequence(pump, closing_reading, previous_reading=opening_reading, station=station)

	# Aggregate classified events for this station + pump + shift/date
	ev_filters = {"station": station, "pump": pump, "status": ["!=", "Cancelled"]}
	if shift:
		ev_filters["shift"] = shift
	else:
		ev_filters["business_date"] = business_date

	events = frappe.get_all(
		"Fuel Dispense Event",
		filters=ev_filters,
		fields=["name", "payment_method", "quantity", "rate", "amount", "invoice", "status", "issue_order"],
	)

	q_card = 0.0
	q_credit = 0.0
	q_internal = 0.0
	q_issue_order = 0.0
	q_coupon = 0.0
	q_recorded_cash = 0.0
	cash_events_uninvoiced = []

	for ev in events:
		pm = ev.payment_method
		qty = flt(ev.quantity)
		if pm == "Card":
			q_card += qty
		elif pm in ("Credit", "Contract"):
			q_credit += qty
		elif pm == "Internal Issue":
			q_internal += qty
		elif pm in ("Coupon", "Prepaid"):
			q_coupon += qty
		elif pm == "Cash":
			if ev.issue_order:
				io_type = frappe.db.get_value("Fuel Issue Order", ev.issue_order, "treatment_type")
				if io_type and io_type != "Cash":
					q_issue_order += qty
					continue
			q_recorded_cash += qty
			if not ev.invoice:
				cash_events_uninvoiced.append(ev)

	# Aggregate calibration & waste events
	cal_filters = {"station": station, "pump": pump, "status": ["!=", "Cancelled"]}
	if shift:
		cal_filters["shift"] = shift
	else:
		cal_filters["business_date"] = business_date

	cal_events = frappe.get_all(
		"Fuel Calibration Event",
		filters=cal_filters,
		fields=["quantity", "stock_treatment"],
	)
	q_cal = sum(flt(c.quantity) for c in cal_events if c.stock_treatment != "Waste Expense")
	q_waste = sum(flt(c.quantity) for c in cal_events if c.stock_treatment == "Waste Expense")

	res = calculate_cash_residual(
		opening_reading=opening_reading,
		closing_reading=closing_reading,
		card_quantity=q_card,
		credit_quantity=q_credit,
		internal_quantity=q_internal,
		issue_order_quantity=q_issue_order,
		coupon_quantity=q_coupon,
		calibration_quantity=q_cal,
		waste_quantity=q_waste,
	)

	if not rate:
		rate = get_effective_item_price(item, posting_date=business_date) or (
			flt(events[0].rate) if events else 0.0
		)

	rec_doc = frappe.get_doc(
		{
			"doctype": "Fuel Pump Reconciliation",
			"station": station,
			"business_date": business_date,
			"shift": shift,
			"pump": pump,
			"item": item,
			"rate": flt(rate),
			"opening_reading": flt(opening_reading),
			"closing_reading": flt(closing_reading),
			"meter_quantity": res.meter_quantity,
			"card_quantity": q_card,
			"credit_quantity": q_credit,
			"internal_quantity": q_internal,
			"issue_order_quantity": q_issue_order,
			"coupon_quantity": q_coupon,
			"calibration_quantity": q_cal,
			"waste_quantity": q_waste,
			"classified_quantity": res.classified_quantity,
			"cash_quantity": res.cash_quantity,
			"recorded_cash_events_quantity": q_recorded_cash,
			"variance_quantity": flt(res.cash_quantity - q_recorded_cash, 4) if q_recorded_cash > 0 else 0.0,
			"variance_amount": flt((res.cash_quantity - q_recorded_cash) * flt(rate), 2) if q_recorded_cash > 0 else 0.0,
			"status": "Calculated",
		}
	)
	rec_doc.flags.ignore_permissions = True
	rec_doc.insert(ignore_permissions=True)

	# Handle negative cash residual (§10.4): NEVER create a negative invoice!
	if res.cash_quantity < 0:
		exc = frappe.get_doc(
			{
				"doctype": "Fuel Reconciliation Exception",
				"exception_type": "Negative Cash Residual",
				"station": station,
				"business_date": business_date,
				"shift": shift,
				"pump": pump,
				"source_documents": rec_doc.name,
				"expected_quantity": res.meter_quantity,
				"actual_quantity": res.classified_quantity,
				"difference": res.cash_quantity,
				"severity": "Critical",
				"status": "Open",
			}
		)
		exc.insert(ignore_permissions=True)
		rec_doc.db_set("exception_reference", exc.name)
		rec_doc.db_set("status", "Pending Review")
		return rec_doc

	# Handle positive cash residual (§10.5)
	if res.cash_quantity > 0 and create_batch:
		if settings.unclassified_quantity_policy == "CREATE_EXCEPTION" and res.cash_quantity > q_recorded_cash:
			exc = frappe.get_doc(
				{
					"doctype": "Fuel Reconciliation Exception",
					"exception_type": "Unclassified Quantity",
					"station": station,
					"business_date": business_date,
					"shift": shift,
					"pump": pump,
					"source_documents": rec_doc.name,
					"expected_quantity": q_recorded_cash,
					"actual_quantity": res.cash_quantity,
					"difference": res.cash_quantity - q_recorded_cash,
					"severity": "Medium",
					"status": "Open",
				}
			)
			exc.insert(ignore_permissions=True)
			rec_doc.db_set("exception_reference", exc.name)
			rec_doc.db_set("status", "Pending Review")
		elif settings.unclassified_quantity_policy in ("CREATE_CASH_DRAFT", "ALLOW_WITH_REASON", "HOLD_FOR_REVIEW"):
			source_key = f"RECON-CASH-{station}-{pump}-{shift or business_date}-{flt(opening_reading)}-{flt(closing_reading)}"
			existing_batch = frappe.db.get_value("Fuel Pump Invoice Batch", {"source_key": source_key}, "name")
			if existing_batch:
				rec_doc.db_set("invoice_batch", existing_batch)
			else:
				batch = frappe.get_doc(
					{
						"doctype": "Fuel Pump Invoice Batch",
						"station": station,
						"business_date": business_date,
						"shift": shift,
						"pump": pump,
						"item": item,
						"rate": flt(rate),
						"invoice_type": "Cash Residual",
						"payment_method": "Cash",
						"opening_reading": flt(opening_reading),
						"closing_reading": flt(closing_reading),
						"meter_quantity": res.meter_quantity,
						"classified_quantity": res.classified_quantity,
						"unclassified_quantity": max(0.0, flt(res.cash_quantity - q_recorded_cash, 4)),
						"invoice_quantity": res.cash_quantity,
						"invoice_amount": flt(res.cash_quantity * flt(rate), 2),
						"status": "Draft" if settings.unclassified_quantity_policy == "HOLD_FOR_REVIEW" else "Ready",
						"source_key": source_key,
						"events": [
							{
								"fuel_dispense_event": ev.name,
								"quantity": ev.quantity,
								"rate": ev.rate,
								"amount": ev.amount,
							}
							for ev in cash_events_uninvoiced
						],
					}
				)
				batch.flags.ignore_permissions = True
				batch.insert(ignore_permissions=True)
				rec_doc.db_set("invoice_batch", batch.name)

	rec_doc.reload()
	return rec_doc


def resolve_reconciliation_exception(exception_name, resolution, resolution_document=None, approved_by=None):
	"""Resolve and approve a Fuel Reconciliation Exception (§17.2)."""
	exc = frappe.get_doc("Fuel Reconciliation Exception", exception_name)
	approved_by = approved_by or frappe.session.user
	roles = frappe.get_roles(approved_by)
	if "Fuel Attendant" in roles and not any(
		r in roles for r in ("Shift Supervisor", "Station Manager", "Fuel Operations Manager", "System Manager", "System Administrator")
	):
		frappe.throw(_("Fuel Attendant is not authorized to approve reconciliation exceptions."))

	exc.resolution = resolution
	if resolution_document:
		exc.resolution_document = resolution_document
	exc.approved_by = approved_by
	exc.status = "Approved"
	exc.save(ignore_permissions=True)

	log_audit_event(
		"Reconciliation Exception Resolved",
		"Fuel Reconciliation Exception",
		exc.name,
		station=exc.station,
		new_value={"resolution": resolution, "approved_by": approved_by},
		reason=resolution,
	)
	return exc


@frappe.whitelist()
def add_pump_sales_automatically(station, business_date=None, shift=None, pump=None, create_invoices=False):
	"""Group uninvoiced dispense events and create Fuel Pump Invoice Batches respecting grouping settings (§26.3, §28.10).
	Grouping key includes: station + pump + shift + item + rate + tax_template + discount_policy + payment_method (+ customer/attendant/cost_center if configured).
	Never merges multiple pumps into one batch if group_by_pump=1.
	"""
	business_date = getdate(business_date or nowdate())
	settings = get_effective_settings(station=station, pump=pump)

	filters = {
		"station": station,
		"status": ["in", ["Recorded", "Classified", "Reviewed"]],
		"payment_method": ["!=", "Internal Issue"],
	}
	if shift:
		filters["shift"] = shift
	else:
		filters["business_date"] = business_date
	if pump:
		filters["pump"] = pump

	events = frappe.get_all(
		"Fuel Dispense Event",
		filters=filters,
		fields=[
			"name",
			"station",
			"business_date",
			"shift",
			"pump",
			"employee",
			"item",
			"rate",
			"quantity",
			"amount",
			"tax_template",
			"discount_source",
			"discount_percentage",
			"discount_amount",
			"payment_method",
			"card_provider",
			"customer",
			"contract",
			"vehicle",
			"invoice",
			"invoice_batch",
			"reading_before",
			"reading_after",
		],
		order_by="creation asc",
	)

	groups = {}
	for ev in events:
		if ev.invoice or ev.invoice_batch:
			continue
		key_parts = [
			ev.station if cint(settings.group_by_station) else "ALL_ST",
			ev.pump if cint(settings.group_by_pump) else "ALL_PUMP",
			(ev.shift or str(ev.business_date)) if cint(settings.group_by_shift) else str(ev.business_date),
			ev.employee if cint(settings.group_by_attendant) else "ALL_ATT",
			ev.item if cint(settings.group_by_item) else "ALL_ITEM",
			f"{flt(ev.rate, 4)}" if cint(settings.group_by_rate) else "ALL_RATE",
			ev.tax_template or "NO_TAX",
			ev.discount_source or "NO_DISC",
			f"{flt(ev.discount_percentage, 2)}-{flt(ev.discount_amount, 2)}",
			ev.payment_method if cint(settings.group_by_payment_method) else "ALL_PM",
			ev.customer if (cint(settings.group_by_customer) or ev.payment_method in ("Credit", "Contract")) else "ALL_CUST",
		]
		gkey = "|".join(str(p or "") for p in key_parts)
		groups.setdefault(gkey, []).append(ev)

	created_batches = []
	for gkey, ev_list in groups.items():
		source_key = "AUTO-BATCH-" + hashlib.sha256(
			(gkey + "|" + ",".join(sorted(e.name for e in ev_list))).encode("utf-8")
		).hexdigest()[:24]

		existing = frappe.db.get_value("Fuel Pump Invoice Batch", {"source_key": source_key}, "name")
		if existing:
			created_batches.append(existing)
			continue

		first = ev_list[0]
		total_qty = sum(flt(e.quantity) for e in ev_list)
		total_amt = sum(flt(e.amount) for e in ev_list)

		batch = frappe.get_doc(
			{
				"doctype": "Fuel Pump Invoice Batch",
				"station": first.station,
				"business_date": first.business_date or business_date,
				"shift": first.shift,
				"pump": first.pump if cint(settings.group_by_pump) else None,
				"attendant": first.employee if cint(settings.group_by_attendant) else None,
				"item": first.item,
				"rate": flt(first.rate),
				"tax_template": first.tax_template,
				"discount_policy": first.discount_source,
				"discount_percentage": flt(first.discount_percentage),
				"discount_amount": flt(first.discount_amount),
				"invoice_type": "B2B Tax Invoice" if first.payment_method in ("Credit", "Contract") else "Batch Summary",
				"customer": first.customer,
				"contract": first.contract,
				"vehicle": first.vehicle if len({e.vehicle for e in ev_list if e.vehicle}) == 1 else None,
				"payment_method": first.payment_method,
				"card_provider": first.card_provider,
				"opening_reading": min(flt(e.reading_before) for e in ev_list),
				"closing_reading": max(flt(e.reading_after) for e in ev_list),
				"meter_quantity": total_qty,
				"classified_quantity": total_qty,
				"unclassified_quantity": 0,
				"invoice_quantity": total_qty,
				"invoice_amount": total_amt,
				"status": "Ready",
				"source_key": source_key,
				"events": [
					{
						"fuel_dispense_event": e.name,
						"quantity": flt(e.quantity),
						"rate": flt(e.rate),
						"amount": flt(e.amount),
					}
					for e in ev_list
				],
			}
		)
		batch.flags.ignore_permissions = True
		batch.insert(ignore_permissions=True)
		for e in ev_list:
			frappe.db.set_value("Fuel Dispense Event", e.name, "invoice_batch", batch.name)

		if create_invoices:
			create_sales_invoice_from_batch(batch)
		created_batches.append(batch.name)

	return created_batches


def create_credit_or_debit_note(
	original_invoice_name,
	note_type="Credit Note",
	return_qty=None,
	adjusted_rate=None,
	update_stock=False,
	reason=None,
	submit=True,
):
	"""Create a standard ERPNext Credit Note / Sales Return or Debit Note linked to original Sales Invoice (§25.2, §28.13)."""
	orig = frappe.get_doc("Sales Invoice", original_invoice_name)
	if orig.docstatus != 1:
		frappe.throw(_("Original Sales Invoice {0} must be submitted before issuing a {1}.").format(orig.name, note_type))

	if note_type in ("Credit Note", "Sales Return"):
		ret = frappe.copy_doc(orig)
		ret.is_return = 1
		ret.return_against = orig.name
		ret.update_stock = 1 if (note_type == "Sales Return" or cint(update_stock)) else 0
		ret.fuel_invoice_type = note_type
		ret.source_key = f"RET-{orig.name}-{flt(return_qty or 0)}-{flt(adjusted_rate or 0)}"
		ret.e_invoice_uuid = None
		ret.e_invoice_status = "Pending"
		ret.e_invoice_qr = None

		for item in ret.items:
			qty = abs(flt(return_qty)) if return_qty is not None else abs(flt(item.qty))
			item.qty = -qty
			if adjusted_rate is not None:
				item.rate = flt(adjusted_rate)

		ret.flags.ignore_permissions = True
		ret.insert(ignore_permissions=True)
		if submit:
			ret.reload()
			ret.submit()
		log_audit_event(note_type, "Sales Invoice", ret.name, station=orig.get("fuel_station"), reason=reason)
		return ret.name

	elif note_type == "Debit Note":
		dn = frappe.copy_doc(orig)
		dn.is_debit_note = 1
		dn.return_against = orig.name
		dn.update_stock = 0
		dn.fuel_invoice_type = "Debit Note"
		dn.source_key = f"DBN-{orig.name}-{flt(adjusted_rate or 0)}"
		dn.e_invoice_uuid = None
		dn.e_invoice_status = "Pending"
		dn.e_invoice_qr = None

		for item in dn.items:
			qty = abs(flt(return_qty)) if return_qty is not None else abs(flt(item.qty))
			item.qty = qty
			if adjusted_rate is not None:
				item.rate = flt(adjusted_rate)

		dn.flags.ignore_permissions = True
		dn.insert(ignore_permissions=True)
		if submit:
			dn.reload()
			dn.submit()
		log_audit_event("Debit Note", "Sales Invoice", dn.name, station=orig.get("fuel_station"), reason=reason)
		return dn.name

	frappe.throw(_("Unsupported note_type: {0}").format(note_type))


def generate_einvoice_payload(sales_invoice_name):
	"""Generate canonical E-Invoice payload and QR content from Sales Invoice (§25.1, §28.14)."""
	inv = frappe.get_doc("Sales Invoice", sales_invoice_name)
	company_tax_id = frappe.db.get_value("Company", inv.company, "tax_id") or ""
	buyer_tax_id = inv.tax_id or frappe.db.get_value("Customer", inv.customer, "tax_id") or ""

	items_payload = []
	total_discount = flt(inv.discount_amount)
	for it in inv.items:
		line_disc = flt(it.discount_amount) * abs(flt(it.qty))
		total_discount += line_disc
		items_payload.append(
			{
				"item_code": it.item_code,
				"item_description": it.item_name or it.description,
				"quantity": flt(it.qty),
				"unit_price": flt(it.price_list_rate or it.rate),
				"discount_amount": line_disc,
				"taxable_amount": flt(it.net_amount),
				"rate_after_discount": flt(it.rate),
			}
		)

	tax_rate = sum(flt(t.rate) for t in (inv.get("taxes") or []))
	payload = {
		"invoice_number": inv.name,
		"invoice_type": inv.get("fuel_invoice_type")
		or ("Credit Note" if inv.is_return else ("Debit Note" if inv.get("is_debit_note") else "Standard Tax Invoice")),
		"issue_date": str(inv.posting_date),
		"issue_time": str(inv.posting_time),
		"seller_tax_id": company_tax_id,
		"buyer_tax_id": buyer_tax_id,
		"items": items_payload,
		"discount_amount": total_discount,
		"taxable_amount": flt(inv.net_total),
		"tax_rate": tax_rate,
		"tax_amount": flt(inv.total_taxes_and_charges),
		"total_before_tax": flt(inv.net_total),
		"total_tax": flt(inv.total_taxes_and_charges),
		"grand_total": flt(inv.grand_total),
		"currency": inv.currency,
		"original_invoice_reference": inv.return_against,
	}
	return payload


def submit_einvoice(sales_invoice_name, simulate_failure=False):
	"""Idempotently submit E-Invoice, storing external_uuid, QR, status, and Fuel Integration Log (§25.1, §28.14)."""
	inv = frappe.get_doc("Sales Invoice", sales_invoice_name)
	idempotency_key = f"EINV-{inv.name}"

	# If already accepted, return existing UUID without duplicating
	if inv.get("e_invoice_status") == "Accepted" and inv.get("e_invoice_uuid"):
		return frappe._dict(
			{
				"status": "Accepted",
				"uuid": inv.e_invoice_uuid,
				"qr_payload": inv.e_invoice_qr,
				"idempotent": True,
			}
		)

	payload = generate_einvoice_payload(sales_invoice_name)
	payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
	payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

	log_name = frappe.db.get_value("Fuel Integration Log", {"idempotency_key": idempotency_key}, "name")
	if log_name:
		log_doc = frappe.get_doc("Fuel Integration Log", log_name)
		log_doc.retry_count = cint(log_doc.retry_count) + 1
	else:
		log_doc = frappe.get_doc(
			{
				"doctype": "Fuel Integration Log",
				"integration_type": "E-Invoice",
				"idempotency_key": idempotency_key,
				"reference_doctype": "Sales Invoice",
				"reference_name": inv.name,
				"request_log": payload_json,
				"retry_count": 0,
			}
		)

	if simulate_failure:
		log_doc.connection_status = "Error"
		log_doc.status = "Failed"
		log_doc.last_error = "Simulated E-Invoice gateway timeout"
		log_doc.response_log = json.dumps({"error": "Gateway timeout"})
		log_doc.save(ignore_permissions=True)
		frappe.db.set_value(
			"Sales Invoice",
			inv.name,
			{
				"e_invoice_status": "Pending",
				"e_invoice_response": log_doc.response_log,
			},
		)
		return frappe._dict({"status": "Failed", "uuid": None, "log": log_doc.name})

	ext_uuid = inv.get("e_invoice_uuid") or str(uuid.uuid5(uuid.NAMESPACE_DNS, f"fuel-einv-{inv.name}"))
	qr_payload = f"UUID:{ext_uuid}|SELLER:{payload['seller_tax_id']}|DATE:{payload['issue_date']}|TOTAL:{payload['grand_total']}|TAX:{payload['total_tax']}|HASH:{payload_hash[:16]}"
	resp_json = json.dumps(
		{"status": "Accepted", "uuid": ext_uuid, "hash": payload_hash, "qr": qr_payload},
		ensure_ascii=False,
	)

	log_doc.connection_status = "Connected"
	log_doc.external_id = ext_uuid
	log_doc.status = "Accepted"
	log_doc.last_error = None
	log_doc.response_log = resp_json
	log_doc.save(ignore_permissions=True)

	frappe.db.set_value(
		"Sales Invoice",
		inv.name,
		{
			"e_invoice_uuid": ext_uuid,
			"e_invoice_status": "Accepted",
			"e_invoice_qr": qr_payload,
			"e_invoice_submitted_at": now_datetime(),
			"e_invoice_response": resp_json,
		},
	)
	return frappe._dict(
		{
			"status": "Accepted",
			"uuid": ext_uuid,
			"qr_payload": qr_payload,
			"log": log_doc.name,
		}
	)

