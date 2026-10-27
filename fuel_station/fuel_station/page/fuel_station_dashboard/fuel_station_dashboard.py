import frappe
from frappe import _
from frappe.utils import flt, nowdate, get_datetime, now_datetime
from erpnext.stock.utils import get_stock_balance


@frappe.whitelist()
def get_dashboard_data(station=None):
	"""
	Returns real-time dashboard state for the selected Fuel Station:
	- Stations list
	- Active Shift details
	- Operational KPIs (Volumes, Revenues, Payment breakdown)
	- Underground Tank Levels & Percentages (via ERPNext stock balances)
	- Forecourt Pumps status & active assignments
	- Recent Dispense Activity feed
	"""
	stations = frappe.get_all("Fuel Station", fields=["name", "station_name", "company"], order_by="name asc")
	if not station:
		station = stations[0].name if stations else None

	if not station:
		return {
			"stations": [],
			"current_station": None,
			"shift": None,
			"kpis": {},
			"tanks": [],
			"pumps": [],
			"recent_dispenses": [],
		}

	# 1. Active Shift
	active_shift = frappe.db.get_value(
		"Fuel Shift",
		{"station": station, "status": "Open"},
		["name", "shift_type", "supervisor", "opened_at", "opening_cash_float", "business_date"],
		as_dict=True,
	)

	# 2. KPIs (Today's operations)
	today = nowdate()
	filters = {"station": station}
	if active_shift:
		filters["shift"] = active_shift.name
	else:
		filters["business_date"] = today

	dispenses = frappe.get_all(
		"Fuel Dispense Event",
		filters=filters,
		fields=["name", "quantity", "amount", "grand_total", "payment_method", "docstatus", "status"],
	)

	valid_dispenses = [d for d in dispenses if d.status != "Cancelled"]
	total_liters = sum(flt(d.quantity) for d in valid_dispenses)
	total_sales = sum(flt(d.grand_total or d.amount) for d in valid_dispenses)
	cash_sales = sum(flt(d.grand_total or d.amount) for d in valid_dispenses if d.payment_method == "Cash")
	card_sales = sum(flt(d.grand_total or d.amount) for d in valid_dispenses if d.payment_method == "Card")
	credit_sales = sum(flt(d.grand_total or d.amount) for d in valid_dispenses if d.payment_method in ("Customer Credit", "Issue Order", "Prepaid Card"))

	# Open cash boxes
	open_boxes_count = frappe.db.count("Fuel Cash Box", {"station": station, "status": "Open"})

	# 3. Underground Tanks & Dip Levels
	tanks_data = []
	tanks = frappe.get_all(
		"Fuel Tank",
		filters={"station": station, "active": 1},
		fields=["name", "tank_number", "item", "warehouse", "capacity", "minimum_level"],
		order_by="tank_number asc",
	)
	for t in tanks:
		capacity = flt(t.capacity) or 1.0
		current_qty = flt(get_stock_balance(t.item, t.warehouse)) if (t.item and t.warehouse) else 0.0
		pct = round((current_qty / capacity) * 100.0, 1) if capacity else 0.0
		tanks_data.append({
			"name": t.name,
			"tank_number": t.tank_number or t.name,
			"item": t.item,
			"warehouse": t.warehouse,
			"capacity": capacity,
			"current_stock": current_qty,
			"percentage": min(max(pct, 0.0), 100.0),
			"minimum_level": flt(t.minimum_level),
			"is_low": current_qty <= flt(t.minimum_level) and current_qty > 0,
		})

	# 4. Forecourt Pumps & Nozzles
	pumps_data = []
	pumps = frappe.get_all(
		"Fuel Pump",
		filters={"station": station, "active": 1},
		fields=["name", "pump_number", "tank", "item", "current_meter_reading", "active"],
		order_by="pump_number asc",
	)
	for p in pumps:
		assignment = None
		if active_shift:
			assignment = frappe.db.get_value(
				"Fuel Pump Assignment",
				{"pump": p.name, "shift": active_shift.name, "status": "Active"},
				["name", "employee", "start_time"],
				as_dict=True,
			)
		pumps_data.append({
			"name": p.name,
			"pump_number": p.pump_number or p.name,
			"tank": p.tank,
			"item": p.item,
			"current_meter_reading": flt(p.current_meter_reading),
			"attendant": assignment.employee if assignment else None,
			"is_assigned": bool(assignment),
		})

	# 5. Recent Dispense Feed
	recent_dispenses = frappe.get_all(
		"Fuel Dispense Event",
		filters={"station": station},
		fields=["name", "creation", "pump", "item", "quantity", "grand_total", "amount", "payment_method", "vehicle_plate_number", "customer"],
		order_by="creation desc",
		limit=8,
	)

	return {
		"stations": stations,
		"current_station": station,
		"shift": active_shift,
		"kpis": {
			"today_liters": total_liters,
			"today_sales": total_sales,
			"cash_sales": cash_sales,
			"card_sales": card_sales,
			"credit_sales": credit_sales,
			"dispense_count": len(valid_dispenses),
			"open_boxes_count": open_boxes_count,
			"active_pumps_count": len([p for p in pumps_data if p["is_assigned"]]),
			"total_pumps_count": len(pumps_data),
		},
		"tanks": tanks_data,
		"pumps": pumps_data,
		"recent_dispenses": recent_dispenses,
	}
