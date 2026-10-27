import frappe
from frappe import _
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "name", "label": _("Invoice"), "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
		{"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "fuel_station", "label": _("Station"), "fieldtype": "Link", "options": "Fuel Station", "width": 130},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 140},
		{"fieldname": "grand_total", "label": _("Grand Total"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "e_invoice_uuid", "label": _("E-Invoice UUID"), "fieldtype": "Data", "width": 200},
		{"fieldname": "e_invoice_status", "label": _("Status"), "fieldtype": "Data", "width": 110},
		{"fieldname": "e_invoice_submitted_at", "label": _("Submitted At"), "fieldtype": "Datetime", "width": 150},
	]
	conds = ["docstatus = 1"]
	params = {}
	allowed = get_allowed_stations_for_user()
	if allowed is not None:
		if not allowed:
			return columns, []
		conds.append("fuel_station IN %(allowed)s")
		params["allowed"] = tuple(allowed)
	if filters.get("e_invoice_status"):
		conds.append("e_invoice_status = %(e_invoice_status)s")
		params["e_invoice_status"] = filters["e_invoice_status"]
	data = frappe.db.sql(
		f"SELECT name, posting_date, fuel_station, customer, grand_total, e_invoice_uuid, e_invoice_status, e_invoice_submitted_at FROM `tabSales Invoice` WHERE {' AND '.join(conds)} ORDER BY posting_date DESC",
		params,
		as_dict=True,
	)
	return columns, data
