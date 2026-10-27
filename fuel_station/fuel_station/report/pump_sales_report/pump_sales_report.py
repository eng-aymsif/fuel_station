import frappe
from frappe import _
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "station", "label": _("Station"), "fieldtype": "Link", "options": "Fuel Station", "width": 140},
		{"fieldname": "pump", "label": _("Pump"), "fieldtype": "Link", "options": "Fuel Pump", "width": 130},
		{"fieldname": "item", "label": _("Fuel Item"), "fieldtype": "Link", "options": "Item", "width": 130},
		{"fieldname": "opening_reading", "label": _("Opening Reading"), "fieldtype": "Float", "width": 130},
		{"fieldname": "closing_reading", "label": _("Closing Reading"), "fieldtype": "Float", "width": 130},
		{"fieldname": "total_quantity", "label": _("Dispensed Liters"), "fieldtype": "Float", "width": 130},
		{"fieldname": "total_amount", "label": _("Total Sales"), "fieldtype": "Currency", "width": 130},
	]
	conds = ["status != 'Cancelled'"]
	params = {}
	allowed = get_allowed_stations_for_user()
	if allowed is not None:
		if not allowed:
			return columns, []
		conds.append("station IN %(allowed)s")
		params["allowed"] = tuple(allowed)
	for fld in ("station", "pump", "shift", "item"):
		if filters.get(fld):
			conds.append(f"{fld} = %({fld})s")
			params[fld] = filters[fld]
	if filters.get("business_date"):
		conds.append("business_date = %(business_date)s")
		params["business_date"] = filters["business_date"]

	where_sql = " AND ".join(conds)
	data = frappe.db.sql(
		f"""
		SELECT station, pump, item,
		       MIN(reading_before) as opening_reading,
		       MAX(reading_after) as closing_reading,
		       SUM(quantity) as total_quantity,
		       SUM(amount) as total_amount
		FROM `tabFuel Dispense Event`
		WHERE {where_sql}
		GROUP BY station, pump, item
		ORDER BY station, pump
		""",
		params,
		as_dict=True,
	)
	return columns, data
