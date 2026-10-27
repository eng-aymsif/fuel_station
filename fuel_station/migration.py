import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate
from fuel_station.services.business_logic import log_audit_event
from fuel_station.services.settings_service import get_effective_settings

MASTER_DATA_IMPORT_ORDER = [
	"Company",
	"Account",
	"Cost Center",
	"Warehouse",
	"Item Group",
	"Item",
	"UOM",
	"Item Price",
	"Customer",
	"Supplier",
	"Employee",
	"Fuel Station",
	"Fuel Tank",
	"Fuel Pump",
	"Fuel Shift Type",
	"Fuel Shift",
	"Fuel Pump Assignment",
]


def import_opening_tank_stock(station, tank, quantity, valuation_rate, posting_date=None, source_reference=None):
	"""Import opening fuel stock using standard ERPNext Stock Reconciliation (§14.3).
	Never writes directly to Stock Ledger Entry.
	"""
	settings = get_effective_settings(station=station)
	cutover = settings.migration_cutover_date
	posting_date = getdate(posting_date or cutover or nowdate())
	if cutover and posting_date > getdate(cutover):
		frappe.throw(
			_("Opening stock date ({0}) cannot be after Migration Cutover Date ({1}).").format(
				posting_date, cutover
			)
		)

	tank_doc = frappe.get_doc("Fuel Tank", tank)
	station_doc = frappe.get_doc("Fuel Station", station)
	company = station_doc.company

	diff_account = (
		station_doc.default_variance_account
		or frappe.db.get_value("Company", company, "stock_adjustment_account")
	)
	sr = frappe.get_doc(
		{
			"doctype": "Stock Reconciliation",
			"purpose": "Opening Stock",
			"company": company,
			"posting_date": posting_date,
			"expense_account": diff_account,
			"cost_center": station_doc.default_cost_center or frappe.db.get_value("Company", company, "cost_center"),
			"items": [
				{
					"item_code": tank_doc.item,
					"warehouse": tank_doc.warehouse,
					"qty": flt(quantity),
					"valuation_rate": flt(valuation_rate),
				}
			],
		}
	)
	sr.flags.ignore_permissions = True
	sr.insert(ignore_permissions=True)
	sr.submit()

	log_audit_event(
		"Opening Stock Imported",
		"Stock Reconciliation",
		sr.name,
		station=station,
		new_value={"tank": tank, "qty": quantity, "rate": valuation_rate, "source": source_reference},
		reason=source_reference or "Initial Migration",
	)
	return sr.name


def import_historical_dispense_event(event_data, cutover_date=None):
	"""Import historical Fuel Dispense Event before Migration Cutover Date without re-posting closed financial periods (§14.4)."""
	settings = get_effective_settings(station=event_data.get("station"))
	cutover = getdate(cutover_date or settings.migration_cutover_date or nowdate())
	bdate = getdate(event_data.get("business_date") or cutover)
	if bdate > cutover:
		frappe.throw(_("Historical dispense event date ({0}) must be on or before Cutover Date ({1}).").format(bdate, cutover))

	ext_id = event_data.get("external_id")
	if ext_id and frappe.db.exists("Fuel Dispense Event", {"external_id": ext_id}):
		return frappe.db.get_value("Fuel Dispense Event", {"external_id": ext_id}, "name")

	doc = frappe.get_doc(
		{
			"doctype": "Fuel Dispense Event",
			"external_id": ext_id,
			"station": event_data["station"],
			"business_date": bdate,
			"shift": event_data.get("shift"),
			"pump": event_data["pump"],
			"item": event_data.get("item"),
			"quantity": flt(event_data["quantity"]),
			"rate": flt(event_data["rate"]),
			"payment_method": event_data.get("payment_method", "Cash"),
			"customer": event_data.get("customer"),
			"payment_reference": event_data.get("payment_reference") or "HIST-MIGRATION",
			"status": "Invoiced",
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	doc.db_set("status", "Invoiced")
	return doc.name

