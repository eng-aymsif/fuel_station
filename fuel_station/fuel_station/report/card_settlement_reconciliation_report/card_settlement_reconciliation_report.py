import frappe
from frappe import _
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "name", "label": _("Settlement"), "fieldtype": "Link", "options": "Card Settlement", "width": 130},
		{"fieldname": "business_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "station", "label": _("Station"), "fieldtype": "Link", "options": "Fuel Station", "width": 130},
		{"fieldname": "provider", "label": _("Provider"), "fieldtype": "Data", "width": 120},
		{"fieldname": "station_card_amount", "label": _("Station Card Ops"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "terminal_report_amount", "label": _("Terminal Report"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "bank_transferred_amount", "label": _("Bank Transferred"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "provider_fee_amount", "label": _("Provider Fees"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "pending_or_rejected_amount", "label": _("Pending / Rejected"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "difference_amount", "label": _("Difference"), "fieldtype": "Currency", "width": 110},
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
	if filters.get("station"):
		conds.append("station = %(station)s")
		params["station"] = filters["station"]
	data = frappe.db.sql(
		f"SELECT name, business_date, station, provider, station_card_amount, terminal_report_amount, bank_transferred_amount, provider_fee_amount, pending_or_rejected_amount, difference_amount, status FROM `tabCard Settlement` WHERE {' AND '.join(conds)} ORDER BY business_date DESC",
		params,
		as_dict=True,
	)
	return columns, data
