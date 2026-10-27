import frappe
from frappe import _
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "employee", "label": _("Attendant"), "fieldtype": "Link", "options": "Employee", "width": 150},
		{"fieldname": "station", "label": _("Station"), "fieldtype": "Link", "options": "Fuel Station", "width": 140},
		{"fieldname": "shift", "label": _("Shift"), "fieldtype": "Link", "options": "Fuel Shift", "width": 120},
		{"fieldname": "events_count", "label": _("Transactions"), "fieldtype": "Int", "width": 110},
		{"fieldname": "total_quantity", "label": _("Total Liters"), "fieldtype": "Float", "width": 120},
		{"fieldname": "total_amount", "label": _("Total Sales Amount"), "fieldtype": "Currency", "width": 140},
	]
	conds = ["status != 'Cancelled'"]
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
		f"""
		SELECT employee, station, shift, COUNT(name) as events_count,
		       SUM(quantity) as total_quantity, SUM(amount) as total_amount
		FROM `tabFuel Dispense Event`
		WHERE {' AND '.join(conds)}
		GROUP BY employee, station, shift
		ORDER BY total_quantity DESC
		""",
		params,
		as_dict=True,
	)
	return columns, data
