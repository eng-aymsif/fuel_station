import frappe
from frappe import _
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "name", "label": _("Delivery"), "fieldtype": "Link", "options": "Fuel Delivery", "width": 130},
		{"fieldname": "delivery_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "station", "label": _("Station"), "fieldtype": "Link", "options": "Fuel Station", "width": 130},
		{"fieldname": "supplier", "label": _("Supplier"), "fieldtype": "Link", "options": "Supplier", "width": 140},
		{"fieldname": "tank", "label": _("Tank"), "fieldtype": "Link", "options": "Fuel Tank", "width": 130},
		{"fieldname": "item", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 110},
		{"fieldname": "document_quantity", "label": _("Document Qty"), "fieldtype": "Float", "width": 120},
		{"fieldname": "received_quantity", "label": _("Received Qty"), "fieldtype": "Float", "width": 120},
		{"fieldname": "variance_quantity", "label": _("Variance Qty"), "fieldtype": "Float", "width": 110},
		{"fieldname": "purchase_receipt", "label": _("Purchase Receipt"), "fieldtype": "Link", "options": "Purchase Receipt", "width": 140},
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
	for fld in ("station", "supplier", "tank", "item"):
		if filters.get(fld):
			conds.append(f"{fld} = %({fld})s")
			params[fld] = filters[fld]
	data = frappe.db.sql(
		f"SELECT name, delivery_date, station, supplier, tank, item, document_quantity, received_quantity, variance_quantity, purchase_receipt, status FROM `tabFuel Delivery` WHERE {' AND '.join(conds)} ORDER BY delivery_date DESC",
		params,
		as_dict=True,
	)
	return columns, data
