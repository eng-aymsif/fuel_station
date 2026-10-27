import frappe
from frappe import _
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "name", "label": _("Event"), "fieldtype": "Link", "options": "Fuel Dispense Event", "width": 140},
		{"fieldname": "business_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "station", "label": _("Station"), "fieldtype": "Link", "options": "Fuel Station", "width": 130},
		{"fieldname": "employee", "label": _("Attendant"), "fieldtype": "Link", "options": "Employee", "width": 130},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 130},
		{"fieldname": "discount_source", "label": _("Discount Source"), "fieldtype": "Data", "width": 140},
		{"fieldname": "discount_percentage", "label": _("Discount %"), "fieldtype": "Float", "width": 100},
		{"fieldname": "discount_amount", "label": _("Unit Discount"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "total_discount", "label": _("Total Discount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "discount_approved_by", "label": _("Approved By"), "fieldtype": "Link", "options": "User", "width": 130},
	]
	conds = ["status != 'Cancelled'", "(discount_percentage > 0 OR discount_amount > 0)"]
	params = {}
	allowed = get_allowed_stations_for_user()
	if allowed is not None:
		if not allowed:
			return columns, []
		conds.append("station IN %(allowed)s")
		params["allowed"] = tuple(allowed)
	if filters.get("station"):
		conds.append("station = %(station)s")
		params["station"] = filters["station"]
	data = frappe.db.sql(
		f"""
		SELECT name, business_date, station, employee, customer, discount_source,
		       discount_percentage, discount_amount,
		       (amount_before_discount - amount) as total_discount,
		       discount_approved_by
		FROM `tabFuel Dispense Event`
		WHERE {' AND '.join(conds)}
		ORDER BY business_date DESC
		""",
		params,
		as_dict=True,
	)
	return columns, data
