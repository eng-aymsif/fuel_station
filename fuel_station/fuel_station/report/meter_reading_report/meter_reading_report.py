import frappe
from frappe import _
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "name", "label": _("Reading ID"), "fieldtype": "Link", "options": "Fuel Meter Reading", "width": 130},
		{"fieldname": "station", "label": _("Station"), "fieldtype": "Link", "options": "Fuel Station", "width": 130},
		{"fieldname": "pump", "label": _("Pump"), "fieldtype": "Link", "options": "Fuel Pump", "width": 120},
		{"fieldname": "shift", "label": _("Shift"), "fieldtype": "Link", "options": "Fuel Shift", "width": 120},
		{"fieldname": "reading_type", "label": _("Reading Type"), "fieldtype": "Data", "width": 110},
		{"fieldname": "previous_reading", "label": _("Previous Reading"), "fieldtype": "Float", "width": 130},
		{"fieldname": "reading_value", "label": _("Current Reading"), "fieldtype": "Float", "width": 130},
		{"fieldname": "meter_quantity", "label": _("Meter Quantity"), "fieldtype": "Float", "width": 120},
		{"fieldname": "employee", "label": _("Employee"), "fieldtype": "Link", "options": "Employee", "width": 120},
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
	for fld in ("station", "pump", "shift", "reading_type"):
		if filters.get(fld):
			conds.append(f"{fld} = %({fld})s")
			params[fld] = filters[fld]
	data = frappe.db.sql(
		f"SELECT name, station, pump, shift, reading_type, previous_reading, reading_value, meter_quantity, employee, status FROM `tabFuel Meter Reading` WHERE {' AND '.join(conds)} ORDER BY creation DESC",
		params,
		as_dict=True,
	)
	return columns, data
