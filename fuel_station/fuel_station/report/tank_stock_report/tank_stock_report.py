import frappe
from frappe import _
from frappe.utils import flt
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "tank", "label": _("Fuel Tank"), "fieldtype": "Link", "options": "Fuel Tank", "width": 150},
		{"fieldname": "station", "label": _("Station"), "fieldtype": "Link", "options": "Fuel Station", "width": 140},
		{"fieldname": "item", "label": _("Fuel Item"), "fieldtype": "Link", "options": "Item", "width": 130},
		{"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 160},
		{"fieldname": "capacity", "label": _("Capacity (L)"), "fieldtype": "Float", "width": 120},
		{"fieldname": "minimum_level", "label": _("Min Level (L)"), "fieldtype": "Float", "width": 120},
		{"fieldname": "actual_qty", "label": _("Current Stock (Stock Ledger)"), "fieldtype": "Float", "width": 160},
		{"fieldname": "below_min", "label": _("Below Minimum?"), "fieldtype": "Check", "width": 110},
	]
	t_filters = {}
	allowed = get_allowed_stations_for_user()
	if allowed is not None:
		if not allowed:
			return columns, []
		t_filters["station"] = ["in", allowed]
	if filters.get("station"):
		t_filters["station"] = filters["station"]
	if filters.get("item"):
		t_filters["item"] = filters["item"]

	tanks = frappe.get_all("Fuel Tank", filters=t_filters, fields=["name", "station", "item", "warehouse", "capacity", "minimum_level"])
	data = []
	for t in tanks:
		qty = flt(frappe.db.get_value("Bin", {"warehouse": t.warehouse, "item_code": t.item}, "actual_qty"))
		data.append({
			"tank": t.name,
			"station": t.station,
			"item": t.item,
			"warehouse": t.warehouse,
			"capacity": flt(t.capacity),
			"minimum_level": flt(t.minimum_level),
			"actual_qty": qty,
			"below_min": 1 if (flt(t.minimum_level) > 0 and qty < flt(t.minimum_level)) else 0,
		})
	return columns, data
