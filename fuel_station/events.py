import frappe
from frappe import _
from frappe.utils import cint, flt
from fuel_station.services.business_logic import log_audit_event, submit_einvoice
from fuel_station.services.settings_service import get_effective_settings


def validate_sales_invoice(doc, method=None):
	"""Validate Fuel Sales Invoice tax requirements and discount rules (§28.2)."""
	if not doc.get("fuel_station"):
		return

	# Check if B2B Standard Tax Invoice or Tax Policy requires Customer Tax ID
	inv_type = doc.get("fuel_invoice_type") or ""
	if "B2B" in inv_type or "Standard Tax Invoice" in inv_type:
		cust_tax_id = doc.get("tax_id") or frappe.db.get_value("Customer", doc.customer, "tax_id")
		if not cust_tax_id:
			frappe.throw(
				_("Customer Tax Registration Number (tax_id) is mandatory for B2B Standard Tax Invoices ({0}).").format(
					doc.customer
				)
			)

	policies = frappe.get_all(
		"Fuel Tax Policy",
		filters={"company": doc.company, "invoice_type": inv_type, "active": 1},
		fields=["require_customer_tax_id", "require_customer_address"],
		limit=1,
	)
	if policies:
		pol = policies[0]
		if cint(pol.require_customer_tax_id):
			cust_tax_id = doc.get("tax_id") or frappe.db.get_value("Customer", doc.customer, "tax_id")
			if not cust_tax_id:
				frappe.throw(_("Customer Tax ID is required by Fuel Tax Policy for this invoice type."))
		if cint(pol.require_customer_address) and not doc.get("customer_address"):
			cust_addr = frappe.db.get_value("Customer", doc.customer, "customer_primary_address")
			if not cust_addr:
				frappe.throw(_("Customer Address is required by Fuel Tax Policy for this invoice type."))


def on_submit_sales_invoice(doc, method=None):
	"""Sync status to Fuel Dispense Event / Fuel Pump Invoice Batch and trigger E-Invoice if enabled."""
	if not doc.get("fuel_station"):
		return

	settings = get_effective_settings(company=doc.company, station=doc.get("fuel_station"))
	if cint(settings.e_invoice_required) and settings.e_invoice_submission_mode == "ON_SUBMIT":
		submit_einvoice(doc.name)

	for item in doc.get("items", []) or []:
		ev_name = item.get("fuel_dispense_event")
		if ev_name and frappe.db.exists("Fuel Dispense Event", ev_name):
			new_status = "Stock Posted" if cint(doc.update_stock) else "Invoiced"
			frappe.db.set_value("Fuel Dispense Event", ev_name, {"invoice": doc.name, "status": new_status})


def on_cancel_sales_invoice(doc, method=None):
	"""Record audit log when a Fuel Sales Invoice is cancelled (§15, §25.2)."""
	if doc.get("fuel_station"):
		log_audit_event(
			"Sales Invoice Cancelled",
			"Sales Invoice",
			doc.name,
			station=doc.get("fuel_station"),
			previous_value="Submitted",
			new_value="Cancelled",
		)


def on_update_after_submit_sales_invoice(doc, method=None):
	"""Prevent direct modification of financial/quantity fields on a submitted Fuel Sales Invoice (§28.13, §28.18 #20)."""
	if not doc.get("fuel_station"):
		return
	old = doc.get_doc_before_save()
	if old:
		if flt(old.grand_total) != flt(doc.grand_total) or flt(old.total_qty) != flt(doc.total_qty):
			frappe.throw(
				_("Direct modification of a submitted Sales Invoice is forbidden. Issue a Credit Note or Debit Note instead.")
			)


def prevent_item_deletion_with_transactions(doc, method=None):
	"""Prevent deleting a Fuel Item that has transactions (§26.11)."""
	if frappe.db.exists("Fuel Dispense Event", {"item": doc.name}) or frappe.db.exists(
		"Fuel Delivery", {"item": doc.name}
	):
		frappe.throw(
			_("Cannot delete Item {0} because it has linked Fuel Station transactions.").format(doc.name)
		)

