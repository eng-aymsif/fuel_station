import frappe
from frappe import _
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "name", "label": _("Reconciliation"), "fieldtype": "Link", "options": "Fuel Pump Reconciliation", "width": 140},
		{"fieldname": "business_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "station", "label": _("Station"), "fieldtype": "Link", "options": "Fuel Station", "width": 130},
		{"fieldname": "shift", "label": _("Shift"), "fieldtype": "Link", "options": "Fuel Shift", "width": 110},
		{"fieldname": "pump", "label": _("Pump"), "fieldtype": "Link", "options": "Fuel Pump", "width": 110},
		{"fieldname": "opening_reading", "label": _("Opening Reading"), "fieldtype": "Float", "width": 120},
		{"fieldname": "closing_reading", "label": _("Closing Reading"), "fieldtype": "Float", "width": 120},
		{"fieldname": "meter_quantity", "label": _("Meter Qty"), "fieldtype": "Float", "width": 100},
		{"fieldname": "card_quantity", "label": _("Card Qty"), "fieldtype": "Float", "width": 90},
		{"fieldname": "credit_quantity", "label": _("Credit Qty"), "fieldtype": "Float", "width": 90},
		{"fieldname": "internal_quantity", "label": _("Internal Qty"), "fieldtype": "Float", "width": 95},
		{"fieldname": "cash_quantity", "label": _("Expected Cash Qty"), "fieldtype": "Float", "width": 130},
		{"fieldname": "variance_quantity", "label": _("Variance Qty"), "fieldtype": "Float", "width": 110},
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
	for fld in ("station", "shift", "pump", "business_date"):
		if filters.get(fld):
			conds.append(f"{fld} = %({fld})s")
			params[fld] = filters[fld]
	data = frappe.db.sql(
		f"""
		SELECT name, business_date, station, shift, pump, opening_reading, closing_reading,
		       meter_quantity, card_quantity, credit_quantity, internal_quantity, cash_quantity,
		       variance_quantity, status
		FROM `tabFuel Pump Reconciliation`
		WHERE {' AND '.join(conds)}
		ORDER BY business_date DESC, creation DESC
		""",
		params,
		as_dict=True,
	)
	return columns, data
