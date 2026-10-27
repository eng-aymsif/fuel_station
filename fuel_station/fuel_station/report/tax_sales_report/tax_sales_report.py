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
		{"fieldname": "payment_method_type", "label": _("Payment Method"), "fieldtype": "Data", "width": 110},
		{"fieldname": "net_total", "label": _("Taxable Net Total"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "total_taxes_and_charges", "label": _("Total Tax"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "grand_total", "label": _("Grand Total"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "e_invoice_status", "label": _("E-Invoice Status"), "fieldtype": "Data", "width": 120},
	]
	conds = ["docstatus = 1"]
	params = {}
	allowed = get_allowed_stations_for_user()
	if allowed is not None:
		if not allowed:
			return columns, []
		conds.append("fuel_station IN %(allowed)s")
		params["allowed"] = tuple(allowed)
	if filters.get("station"):
		conds.append("fuel_station = %(station)s")
		params["station"] = filters["station"]
	if filters.get("customer"):
		conds.append("customer = %(customer)s")
		params["customer"] = filters["customer"]
	data = frappe.db.sql(
		f"SELECT name, posting_date, fuel_station, customer, payment_method_type, net_total, total_taxes_and_charges, grand_total, e_invoice_status FROM `tabSales Invoice` WHERE {' AND '.join(conds)} ORDER BY posting_date DESC, name DESC",
		params,
		as_dict=True,
	)
	return columns, data
