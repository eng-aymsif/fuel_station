import frappe
from frappe import _
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "name", "label": _("Custody ID"), "fieldtype": "Link", "options": "Fuel Cash Custody", "width": 140},
		{"fieldname": "station", "label": _("Station"), "fieldtype": "Link", "options": "Fuel Station", "width": 140},
		{"fieldname": "shift", "label": _("Shift"), "fieldtype": "Link", "options": "Fuel Shift", "width": 120},
		{"fieldname": "employee", "label": _("Employee"), "fieldtype": "Link", "options": "Employee", "width": 140},
		{"fieldname": "opening_amount", "label": _("Opening"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "cash_sales", "label": _("Cash Sales"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "expected_amount", "label": _("Expected"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "actual_amount", "label": _("Actual"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "variance_amount", "label": _("Variance"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
	]
	conds = ["1=1"]
	params = {}
	allowed = get_allowed_stations_for_user()
	if allowed is not None:
		if not allowed:
			return columns, []
		conds.append("station IN %(allowed)s")
		params["allowed"] = tuple(allowed)
	for fld in ("station", "shift", "employee"):
		if filters.get(fld):
			conds.append(f"{fld} = %({fld})s")
			params[fld] = filters[fld]
	data = frappe.db.sql(
		f"SELECT name, station, shift, employee, opening_amount, cash_sales, expected_amount, actual_amount, variance_amount, status FROM `tabFuel Cash Custody` WHERE {' AND '.join(conds)} ORDER BY creation DESC",
		params,
		as_dict=True,
	)
	return columns, data
