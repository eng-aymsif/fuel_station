import frappe
from frappe import _
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 150},
		{"fieldname": "contract", "label": _("Contract"), "fieldtype": "Link", "options": "Fuel Customer Contract", "width": 130},
		{"fieldname": "vehicle", "label": _("Vehicle"), "fieldtype": "Link", "options": "Customer Vehicle", "width": 120},
		{"fieldname": "driver", "label": _("Driver"), "fieldtype": "Link", "options": "Customer Driver", "width": 120},
		{"fieldname": "station", "label": _("Station"), "fieldtype": "Link", "options": "Fuel Station", "width": 130},
		{"fieldname": "item", "label": _("Fuel Item"), "fieldtype": "Link", "options": "Item", "width": 110},
		{"fieldname": "quantity", "label": _("Quantity (L)"), "fieldtype": "Float", "width": 110},
		{"fieldname": "amount", "label": _("Net Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "grand_total", "label": _("Grand Total"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "invoice", "label": _("Sales Invoice"), "fieldtype": "Link", "options": "Sales Invoice", "width": 130},
	]
	conds = ["status != 'Cancelled'", "customer IS NOT NULL", "customer != ''"]
	params = {}
	allowed = get_allowed_stations_for_user()
	if allowed is not None:
		if not allowed:
			return columns, []
		conds.append("station IN %(allowed)s")
		params["allowed"] = tuple(allowed)
	for fld in ("customer", "contract", "vehicle", "driver", "station", "item"):
		if filters.get(fld):
			conds.append(f"{fld} = %({fld})s")
			params[fld] = filters[fld]
	data = frappe.db.sql(
		f"""
		SELECT customer, contract, vehicle, driver, station, item,
		       SUM(quantity) as quantity, SUM(amount) as amount, SUM(grand_total) as grand_total,
		       MAX(invoice) as invoice
		FROM `tabFuel Dispense Event`
		WHERE {' AND '.join(conds)}
		GROUP BY customer, contract, vehicle, driver, station, item
		ORDER BY customer, vehicle
		""",
		params,
		as_dict=True,
	)
	return columns, data
