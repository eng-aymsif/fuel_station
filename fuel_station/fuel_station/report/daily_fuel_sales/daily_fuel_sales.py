import frappe
from frappe import _
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "business_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "station", "label": _("Station"), "fieldtype": "Link", "options": "Fuel Station", "width": 140},
		{"fieldname": "shift", "label": _("Shift"), "fieldtype": "Link", "options": "Fuel Shift", "width": 120},
		{"fieldname": "pump", "label": _("Pump"), "fieldtype": "Link", "options": "Fuel Pump", "width": 120},
		{"fieldname": "item", "label": _("Fuel Item"), "fieldtype": "Link", "options": "Item", "width": 120},
		{"fieldname": "payment_method", "label": _("Payment Method"), "fieldtype": "Data", "width": 110},
		{"fieldname": "quantity", "label": _("Quantity (L)"), "fieldtype": "Float", "width": 110},
		{"fieldname": "amount", "label": _("Net Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "tax_amount", "label": _("Tax Amount"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "grand_total", "label": _("Grand Total"), "fieldtype": "Currency", "width": 120},
	]
	conds = ["status != 'Cancelled'"]
	params = {}
	allowed_stations = get_allowed_stations_for_user()
	if allowed_stations is not None:
		if not allowed_stations:
			return columns, []
		conds.append("station IN %(allowed_stations)s")
		params["allowed_stations"] = tuple(allowed_stations)

	for fld in ("station", "shift", "pump", "item", "payment_method", "customer"):
		if filters.get(fld):
			conds.append(f"{fld} = %({fld})s")
			params[fld] = filters[fld]
	if filters.get("from_date"):
		conds.append("business_date >= %(from_date)s")
		params["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conds.append("business_date <= %(to_date)s")
		params["to_date"] = filters["to_date"]

	where_sql = " AND ".join(conds)
	data = frappe.db.sql(
		f"""
		SELECT business_date, station, shift, pump, item, payment_method,
		       SUM(quantity) as quantity, SUM(amount) as amount,
		       SUM(tax_amount) as tax_amount, SUM(grand_total) as grand_total
		FROM `tabFuel Dispense Event`
		WHERE {where_sql}
		GROUP BY business_date, station, shift, pump, item, payment_method
		ORDER BY business_date DESC, station, pump
		""",
		params,
		as_dict=True,
	)
	return columns, data
