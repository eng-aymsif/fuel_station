import frappe
from frappe import _
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "name", "label": _("Log ID"), "fieldtype": "Link", "options": "Fuel Audit Log", "width": 130},
		{"fieldname": "event_timestamp", "label": _("Timestamp"), "fieldtype": "Datetime", "width": 150},
		{"fieldname": "event_type", "label": _("Event Type"), "fieldtype": "Data", "width": 160},
		{"fieldname": "reference_doctype", "label": _("DocType"), "fieldtype": "Data", "width": 140},
		{"fieldname": "reference_name", "label": _("Document"), "fieldtype": "Data", "width": 140},
		{"fieldname": "station", "label": _("Station"), "fieldtype": "Link", "options": "Fuel Station", "width": 130},
		{"fieldname": "user", "label": _("User"), "fieldtype": "Link", "options": "User", "width": 130},
		{"fieldname": "previous_value", "label": _("Previous Value"), "fieldtype": "Data", "width": 140},
		{"fieldname": "new_value", "label": _("New Value"), "fieldtype": "Data", "width": 140},
		{"fieldname": "reason", "label": _("Reason"), "fieldtype": "Data", "width": 180},
	]
	conds = ["1=1"]
	params = {}
	allowed = get_allowed_stations_for_user()
	if allowed is not None:
		if not allowed:
			return columns, []
		conds.append("(station IN %(allowed)s OR station IS NULL OR station = '')")
		params["allowed"] = tuple(allowed)
	if filters.get("station"):
		conds.append("station = %(station)s")
		params["station"] = filters["station"]
	if filters.get("event_type"):
		conds.append("event_type = %(event_type)s")
		params["event_type"] = filters["event_type"]
	data = frappe.db.sql(
		f"SELECT name, event_timestamp, event_type, reference_doctype, reference_name, station, user, previous_value, new_value, reason FROM `tabFuel Audit Log` WHERE {' AND '.join(conds)} ORDER BY event_timestamp DESC",
		params,
		as_dict=True,
	)
	return columns, data
