import frappe
from frappe import _
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "check_item", "label": _("Checklist Item"), "fieldtype": "Data", "width": 260},
		{"fieldname": "pending_count", "label": _("Pending / Open Count"), "fieldtype": "Int", "width": 150},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 120},
	]
	station_filter = {}
	allowed = get_allowed_stations_for_user()
	if allowed is not None:
		station_filter["station"] = ["in", allowed or ["__NONE__"]]
	if filters.get("station"):
		station_filter["station"] = filters["station"]

	open_shifts = frappe.db.count("Fuel Shift", {**station_filter, "status": ["in", ["Open", "In Operation", "Pending Closing"]]})
	open_pumps = frappe.db.count("Fuel Pump Assignment", {**station_filter, "status": "Active"})
	unclassified = frappe.db.count("Fuel Dispense Event", {**station_filter, "status": ["in", ["Draft", "Exception"]]})
	open_exceptions = frappe.db.count("Fuel Reconciliation Exception", {**station_filter, "status": ["in", ["Open", "Under Review"]]})
	open_boxes = frappe.db.count("Fuel Cash Box", {**station_filter, "status": ["in", ["Open", "Pending Count"]]})
	uninvoiced = frappe.db.count("Fuel Dispense Event", {**station_filter, "status": ["in", ["Recorded", "Classified"]], "payment_method": ["!=", "Internal Issue"]})

	checks = [
		(_("كل الورديات مغلقة / All Shifts Closed"), open_shifts),
		(_("كل المضخات مغلقة / All Pump Assignments Closed"), open_pumps),
		(_("كل الكميات مصنفة / All Events Classified"), unclassified),
		(_("لا توجد فروقات حرجة / No Open Reconciliation Exceptions"), open_exceptions),
		(_("كل صناديق النقد معدودة / All Cash Boxes Counted"), open_boxes),
		(_("فواتير اليوم منشأة / All Sales Events Invoiced"), uninvoiced),
	]
	data = [
		{
			"check_item": label,
			"pending_count": cnt,
			"status": "Ready" if cnt == 0 else "Action Required",
		}
		for label, cnt in checks
	]
	return columns, data
