import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, now_datetime, nowdate
from fuel_station.services.business_logic import (
	calculate_price_discount_and_tax,
	check_customer_credit_and_contract,
	classify_dispense_event,
	consume_issue_order_quantity,
	create_stock_entry_from_internal_issue,
	log_audit_event,
	validate_issue_order,
	validate_meter_sequence,
)
from fuel_station.services.settings_service import get_effective_settings


class FuelDispenseEvent(Document):
	def validate(self):
		if not self.business_date:
			self.business_date = nowdate()

		# Idempotency / duplicate prevention (§3.5)
		if self.external_id and not self.source_key:
			self.source_key = f"EXT-{self.external_id}"

		# Populate defaults from Pump
		if self.pump and frappe.db.exists("Fuel Pump", self.pump):
			pump_doc = frappe.get_doc("Fuel Pump", self.pump)
			if not self.item:
				self.item = pump_doc.item
			if not self.tank:
				self.tank = pump_doc.tank
			if not self.warehouse:
				self.warehouse = pump_doc.warehouse
			if not self.uom:
				self.uom = pump_doc.uom or "Liter"

		# Validate shift optionality (§30.2)
		settings = get_effective_settings(
			station=self.station,
			pump=self.pump,
			customer=self.customer,
			operation_type=self.payment_method,
		)

		# Prevent Attendant from manually overriding price below list price without discount flow (§13)
		if not self.is_new():
			old = self.get_doc_before_save()
			if old and old.status == "Cancelled" and self.status != "Cancelled":
				frappe.throw(_("Cancelled Fuel Dispense Event cannot be reactivated."))
			if old and self.status == "Cancelled" and old.status != "Cancelled":
				if not self.cancellation_reason:
					frappe.throw(_("Cancellation reason is required to cancel a Fuel Dispense Event."))
				self.cancelled_by = frappe.session.user
				self.cancelled_at = now_datetime()
				log_audit_event(
					"Dispense Event Cancelled",
					"Fuel Dispense Event",
					self.name,
					station=self.station,
					reason=self.cancellation_reason,
				)
				return

		# Validate meter readings if provided
		if flt(self.reading_after) > 0 or flt(self.reading_before) > 0:
			validate_meter_sequence(
				pump=self.pump,
				reading_value=self.reading_after,
				previous_reading=self.reading_before,
				station=self.station,
			)
			diff = flt(flt(self.reading_after) - flt(self.reading_before), 4)
			if diff > 0 and not flt(self.quantity):
				self.quantity = diff
			elif diff > 0 and abs(flt(self.quantity) - diff) > 0.01:
				frappe.throw(
					_("Quantity ({0}) does not match meter reading difference ({1}).").format(self.quantity, diff)
				)

		# Never store sensitive full card numbers (§11.2, §25.4)
		if self.card_last_four and len(str(self.card_last_four).strip()) > 4:
			frappe.throw(_("Only the last 4 digits of a payment card may be stored."))

		# Calculate price, discount, and tax
		calc = calculate_price_discount_and_tax(
			item=self.item,
			quantity=self.quantity,
			station=self.station,
			customer=self.customer,
			contract=self.contract,
			price_list=self.price_list,
			rate=self.rate_before_discount or self.rate,
			discount_percentage=self.discount_percentage,
			discount_amount=self.discount_amount,
			discount_source=self.discount_source,
			discount_reason=self.discount_reason,
			discount_approved_by=self.discount_approved_by,
			tax_template=self.tax_template,
			prices_include_tax=self.prices_include_tax if self.prices_include_tax else None,
			posting_date=self.business_date,
		)
		self.price_list = calc.price_list
		self.rate_before_discount = calc.rate_before_discount
		self.discount_percentage = calc.discount_percentage
		self.discount_amount = calc.discount_amount
		self.rate = calc.rate_after_discount
		self.amount_before_discount = calc.amount_before_discount
		self.amount = calc.amount_after_discount
		self.tax_template = calc.tax_template
		self.prices_include_tax = calc.prices_include_tax
		self.tax_amount = calc.tax_amount
		self.grand_total = calc.grand_total

		# Populate vehicle/driver display fields
		if self.vehicle and not self.vehicle_plate_number and frappe.db.exists("Customer Vehicle", self.vehicle):
			self.vehicle_plate_number = frappe.db.get_value("Customer Vehicle", self.vehicle, "plate_number")
		if self.driver and not self.driver_name and frappe.db.exists("Customer Driver", self.driver):
			self.driver_name = frappe.db.get_value("Customer Driver", self.driver, "driver_name")

		# Validate Fuel Card / Coupon if linked (§26.8)
		if self.fuel_card and frappe.db.exists("Fuel Card", self.fuel_card):
			self._validate_fuel_card()

		# Validate Fuel Authorization if linked (§6.9)
		if self.authorization and frappe.db.exists("Fuel Authorization", self.authorization):
			self._validate_authorization()

		# Validate Fuel Issue Order if linked (§9)
		if self.issue_order and frappe.db.exists("Fuel Issue Order", self.issue_order):
			validate_issue_order(
				self.issue_order,
				requested_quantity=self.quantity,
				requested_amount=self.grand_total or self.amount,
				posting_date=self.business_date,
			)

		# Credit limit & contract enforcement for Credit/Contract sales (§26.6)
		if self.payment_method in ("Credit", "Contract"):
			if not self.customer:
				frappe.throw(_("Customer is required for Credit / Contract sales."))
			if cint(settings.credit_requires_authorization) and not (
				self.authorization or self.issue_order or self.contract or self.fuel_card
			):
				frappe.throw(_("Credit sale requires Authorization, Issue Order, Contract, or Fuel Card."))

			credit_res = check_customer_credit_and_contract(
				customer=self.customer,
				requested_amount=self.grand_total or self.amount,
				requested_quantity=self.quantity,
				station=self.station,
				item=self.item,
				vehicle=self.vehicle,
				driver=self.driver,
				contract=self.contract,
				posting_date=self.business_date,
				override_approved_by=self.credit_override_approved_by,
				override_reason=self.credit_override_reason,
			)
			self.credit_check_result = credit_res.status
			if not credit_res.allowed:
				log_audit_event(
					"Credit Limit / Contract Block",
					"Fuel Dispense Event",
					self.name or "New",
					station=self.station,
					new_value=credit_res,
					reason=credit_res.message,
				)
				frappe.throw(credit_res.message)

		# Card reference check
		if self.payment_method == "Card" and cint(settings.card_requires_reference) and not self.payment_reference:
			frappe.throw(_("Payment Reference is required for Card sales."))

		# Internal Issue check
		if self.payment_method == "Internal Issue" and cint(settings.internal_issue_requires_order) and not self.issue_order:
			frappe.throw(_("Fuel Issue Order is required for Internal Issue."))

		if self.status == "Recorded":
			self.status = "Classified"

	def _validate_fuel_card(self):
		card = frappe.get_doc("Fuel Card", self.fuel_card)
		if card.status != "Active":
			frappe.throw(_("Fuel Card / Coupon {0} is {1}.").format(card.name, card.status))
		bdate = getdate(self.business_date)
		if card.valid_from and getdate(card.valid_from) > bdate:
			frappe.throw(_("Fuel Card / Coupon {0} is not yet valid.").format(card.name))
		if card.valid_until and getdate(card.valid_until) < bdate:
			frappe.throw(_("Fuel Card / Coupon {0} has expired.").format(card.name))
		if card.allowed_item and card.allowed_item != self.item:
			frappe.throw(_("Fuel Card / Coupon {0} is restricted to item {1}.").format(card.name, card.allowed_item))
		if card.allowed_station and card.allowed_station != self.station:
			frappe.throw(_("Fuel Card / Coupon {0} is restricted to station {1}.").format(card.name, card.allowed_station))
		if flt(card.quantity_limit) > 0 and flt(card.used_quantity) + flt(self.quantity) > flt(card.quantity_limit) + 0.0001:
			frappe.throw(_("Quantity exceeds remaining balance on Fuel Card / Coupon {0}.").format(card.name))

	def _validate_authorization(self):
		auth = frappe.get_doc("Fuel Authorization", self.authorization)
		if auth.status not in ("Active", "Partially Used"):
			frappe.throw(_("Fuel Authorization {0} is {1}.").format(auth.name, auth.status))
		if flt(auth.quantity_limit) > 0 and flt(auth.used_quantity) + flt(self.quantity) > flt(auth.quantity_limit) + 0.0001:
			frappe.throw(_("Quantity exceeds remaining limit on Fuel Authorization {0}.").format(auth.name))
		if flt(auth.amount_limit) > 0 and flt(auth.used_amount) + flt(self.amount) > flt(auth.amount_limit) + 0.01:
			frappe.throw(_("Amount exceeds remaining limit on Fuel Authorization {0}.").format(auth.name))

	def after_insert(self):
		if self.status == "Cancelled":
			return
		if self.pump and flt(self.reading_after) > 0:
			frappe.db.set_value("Fuel Pump", self.pump, "current_meter_reading", flt(self.reading_after))

		if self.issue_order and frappe.db.exists("Fuel Issue Order", self.issue_order):
			settings = get_effective_settings(station=self.station, pump=self.pump)
			create_se = (
				self.payment_method == "Internal Issue"
				and settings.stock_posting_timing in ("ON_DISPENSE", "ON_INVOICE_SUBMIT")
			)
			_, se_name = consume_issue_order_quantity(self.issue_order, self.quantity, create_stock_entry=create_se)
			if se_name:
				self.db_set("stock_document", se_name)
				self.db_set("status", "Stock Posted")

		if self.authorization and frappe.db.exists("Fuel Authorization", self.authorization):
			auth = frappe.get_doc("Fuel Authorization", self.authorization)
			auth.used_quantity = flt(auth.used_quantity) + flt(self.quantity)
			auth.used_amount = flt(auth.used_amount) + flt(self.amount)
			auth.save(ignore_permissions=True)

		if self.fuel_card and frappe.db.exists("Fuel Card", self.fuel_card):
			card = frappe.get_doc("Fuel Card", self.fuel_card)
			card.used_quantity = flt(card.used_quantity) + flt(self.quantity)
			card.used_amount = flt(card.used_amount) + flt(self.amount)
			card.save(ignore_permissions=True)

	def on_trash(self):
		# Non-negotiable Rule §3.6: Never delete after posting/invoicing
		if self.status in ("Invoiced", "Stock Posted") or self.invoice or self.stock_document:
			frappe.throw(_("Deleting a posted or invoiced Fuel Dispense Event is strictly prohibited. Use Cancellation with a reason instead."))


@frappe.whitelist()
def make_sales_invoice(event_name):
	"""Generate a standard ERPNext Sales Invoice from a single Fuel Dispense Event."""
	doc = frappe.get_doc("Fuel Dispense Event", event_name)
	if doc.invoice and frappe.db.exists("Sales Invoice", doc.invoice):
		return doc.invoice

	from fuel_station.services.business_logic import create_sales_invoice_from_batch
	inv = create_sales_invoice_from_batch(doc, submit=False)
	if inv:
		doc.db_set("invoice", inv.name)
		doc.db_set("status", "Invoiced")
		return inv.name
	return None
