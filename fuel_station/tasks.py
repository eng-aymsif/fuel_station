import frappe
from frappe.utils import add_days, cint, flt, getdate, nowdate
from fuel_station.services.settings_service import get_effective_settings


def daily_maintenance():
	"""Idempotent daily scheduled maintenance jobs (§25.19)."""
	expire_overdue_issue_orders_and_authorizations()
	check_tank_minimum_levels_and_calibrations()
	cleanup_old_integration_logs()


def hourly_maintenance():
	"""Idempotent hourly scheduled maintenance jobs (§25.19)."""
	expire_overdue_issue_orders_and_authorizations()


def expire_overdue_issue_orders_and_authorizations(posting_date=None):
	today = getdate(posting_date or nowdate())
	orders = frappe.get_all(
		"Fuel Issue Order",
		filters={
			"approval_status": ["in", ["Approved", "Partially Used"]],
			"valid_until": ["<", today],
		},
		pluck="name",
	)
	for name in orders:
		frappe.db.set_value("Fuel Issue Order", name, "approval_status", "Expired")

	auths = frappe.get_all(
		"Fuel Authorization",
		filters={
			"status": ["in", ["Active", "Partially Used"]],
			"valid_until": ["<", today],
		},
		pluck="name",
	)
	for name in auths:
		frappe.db.set_value("Fuel Authorization", name, "status", "Expired")

	return {"expired_issue_orders": len(orders), "expired_authorizations": len(auths)}


def check_tank_minimum_levels_and_calibrations(posting_date=None):
	today = getdate(posting_date or nowdate())
	low_tanks = []
	for t in frappe.get_all("Fuel Tank", filters={"active": 1}, fields=["name", "warehouse", "item", "minimum_level"]):
		if flt(t.minimum_level) > 0:
			qty = flt(frappe.db.get_value("Bin", {"warehouse": t.warehouse, "item_code": t.item}, "actual_qty"))
			if qty < flt(t.minimum_level):
				low_tanks.append(t.name)

	due_pumps = frappe.get_all(
		"Fuel Pump",
		filters={"active": 1, "next_calibration_date": ["<=", today]},
		pluck="name",
	)
	return {"low_tanks": low_tanks, "due_calibrations": due_pumps}


def cleanup_old_integration_logs():
	settings = get_effective_settings()
	retention_days = cint(settings.integration_log_retention_days or 90)
	cutoff = add_days(nowdate(), -retention_days)
	old_logs = frappe.get_all(
		"Fuel Integration Log",
		filters={"creation": ["<", cutoff], "status": "Accepted"},
		pluck="name",
	)
	for name in old_logs:
		frappe.delete_doc("Fuel Integration Log", name, ignore_permissions=True)
	return len(old_logs)

