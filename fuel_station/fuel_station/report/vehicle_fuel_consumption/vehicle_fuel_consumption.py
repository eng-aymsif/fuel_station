import frappe
from frappe import _
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "vehicle", "label": _("Vehicle / Plate"), "fieldtype": "Link", "options": "Customer Vehicle", "width": 140},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 140},
		{"fieldname": "driver", "label": _("Driver"), "fieldtype": "Link", "options": "Customer Driver", "width": 140},
		{"fieldname": "item", "label": _("Fuel Item"), "fieldtype": "Link", "options": "Item", "width": 120},
		{"fieldname": "fill_count", "label": _("Fill Count"), "fieldtype": "Int", "width": 100},
		{"fieldname": "total_quantity", "label": _("Total Liters"), "fieldtype": "Float", "width": 120},
		{"fieldname": "total_amount", "label": _("Total Amount"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "last_odometer", "label": _("Last Odometer"), "fieldtype": "Float", "width": 120},
	]
	conds = ["status != 'Cancelled'", "vehicle IS NOT NULL", "vehicle != ''"]
	params = {}
	allowed = get_allowed_stations_for_user()
	if allowed is not None:
		if not allowed:
			return columns, []
		conds.append("station IN %(allowed)s")
		params["allowed"] = tuple(allowed)
	for fld in ("vehicle", "customer", "driver", "station", "item"):
		if filters.get(fld):
			conds.append(f"{fld} = %({fld})s")
			params[fld] = filters[fld]
	data = frappe.db.sql(
		f"""
		SELECT vehicle, customer, driver, item,
		       COUNT(name) as fill_count,
		       SUM(quantity) as total_quantity,
		       SUM(amount) as total_amount,
		       MAX(odometer_reading) as last_odometer
		FROM `tabFuel Dispense Event`
		WHERE {' AND '.join(conds)}
		GROUP BY vehicle, customer, driver, item
		ORDER BY total_quantity DESC
		""",
		params,
		as_dict=True,
	)
	return columns, data
