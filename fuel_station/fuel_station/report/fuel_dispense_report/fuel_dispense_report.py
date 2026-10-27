import frappe
from frappe import _
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "name", "label": _("Event ID"), "fieldtype": "Link", "options": "Fuel Dispense Event", "width": 140},
		{"fieldname": "business_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "station", "label": _("Station"), "fieldtype": "Link", "options": "Fuel Station", "width": 130},
		{"fieldname": "shift", "label": _("Shift"), "fieldtype": "Link", "options": "Fuel Shift", "width": 110},
		{"fieldname": "pump", "label": _("Pump"), "fieldtype": "Link", "options": "Fuel Pump", "width": 110},
		{"fieldname": "employee", "label": _("Attendant"), "fieldtype": "Link", "options": "Employee", "width": 120},
		{"fieldname": "item", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 110},
		{"fieldname": "quantity", "label": _("Quantity"), "fieldtype": "Float", "width": 100},
		{"fieldname": "rate", "label": _("Rate"), "fieldtype": "Currency", "width": 90},
		{"fieldname": "amount", "label": _("Amount"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "payment_method", "label": _("Payment Method"), "fieldtype": "Data", "width": 110},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 130},
		{"fieldname": "vehicle", "label": _("Vehicle"), "fieldtype": "Link", "options": "Customer Vehicle", "width": 110},
		{"fieldname": "driver", "label": _("Driver"), "fieldtype": "Link", "options": "Customer Driver", "width": 110},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "invoice", "label": _("Sales Invoice"), "fieldtype": "Link", "options": "Sales Invoice", "width": 130},
	]
	conds = ["1=1"]
	params = {}
	allowed = get_allowed_stations_for_user()
	if allowed is not None:
		if not allowed:
			return columns, []
		conds.append("station IN %(allowed)s")
		params["allowed"] = tuple(allowed)
	for fld in ("station", "shift", "pump", "employee", "item", "payment_method", "customer", "vehicle", "driver", "status"):
		if filters.get(fld):
			conds.append(f"{fld} = %({fld})s")
			params[fld] = filters[fld]
	if filters.get("business_date"):
		conds.append("business_date = %(business_date)s")
		params["business_date"] = filters["business_date"]

	where_sql = " AND ".join(conds)
	data = frappe.db.sql(
		f"""
		SELECT name, business_date, station, shift, pump, employee, item,
		       quantity, rate, amount, payment_method, customer, vehicle, driver, status, invoice
		FROM `tabFuel Dispense Event`
		WHERE {where_sql}
		ORDER BY creation DESC
		""",
		params,
		as_dict=True,
	)
	return columns, data
