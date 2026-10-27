import json
import frappe
from frappe import _
from frappe.utils import flt, nowdate, now_datetime
from fuel_station.services.business_logic import (
	get_effective_item_price,
	check_customer_credit_and_contract,
	validate_issue_order,
	consume_issue_order_quantity,
)


@frappe.whitelist()
def get_pos_init_data(station=None):
	"""
	Initializes the POS Fast Dispense terminal:
	- List of stations
	- Selected station active shift & supervisor
	- Configured pumps with fuel grades and current totalizers
	- Item retail prices
	- Available Fleet Customers & active Issue Orders
	"""
	stations = frappe.get_all("Fuel Station", fields=["name", "station_name", "company"], order_by="name asc")
	if not station:
		station = stations[0].name if stations else None

	if not station:
		return {"stations": [], "current_station": None, "shift": None, "pumps": [], "items": []}

	# 1. Active Shift
	active_shift = frappe.db.get_value(
		"Fuel Shift",
		{"station": station, "status": "Open"},
		["name", "shift_type", "supervisor", "opened_at", "business_date"],
		as_dict=True,
	)

	# 2. Forecourt Pumps
	pumps = frappe.get_all(
		"Fuel Pump",
		filters={"station": station, "active": 1},
		fields=["name", "pump_number", "tank", "item", "current_meter_reading", "uom", "warehouse"],
		order_by="pump_number asc",
	)

	# 3. Item prices
	items_map = {}
	for p in pumps:
		if p.item and p.item not in items_map:
			price = get_effective_item_price(p.item, posting_date=nowdate())
			items_map[p.item] = {
				"item_code": p.item,
				"rate": flt(price),
				"uom": p.uom or "Liter",
			}
		p["rate"] = items_map.get(p.item, {}).get("rate", 0.0)

	# 4. Fleet Customers
	customers = frappe.get_all("Customer", fields=["name", "customer_name"], limit=50)

	# 5. Open Issue Orders
	issue_orders = frappe.get_all(
		"Fuel Issue Order",
		filters={"approval_status": "Approved", "remaining_quantity": [">", 0]},
		fields=["name", "plate_number", "vehicle", "item", "remaining_quantity", "customer"],
		limit=30,
	)

	return {
		"stations": stations,
		"current_station": station,
		"shift": active_shift,
		"pumps": pumps,
		"items": list(items_map.values()),
		"customers": customers,
		"issue_orders": issue_orders,
	}


@frappe.whitelist()
def submit_pos_dispense(payload):
	"""
	Records and completes a rapid fuel dispense transaction from the POS console.
	Creates a standard Fuel Dispense Event and submits it.
	"""
	if isinstance(payload, str):
		data = json.loads(payload)
	else:
		data = payload

	pump_name = data.get("pump")
	station = data.get("station")
	qty = flt(data.get("quantity"))
	payment_method = data.get("payment_method") or "Cash"
	customer = data.get("customer")
	vehicle_plate = data.get("vehicle_plate_number")
	driver_name = data.get("driver_name")
	issue_order = data.get("issue_order")
	shift_name = data.get("shift")

	if qty <= 0:
		frappe.throw(_("Quantity dispensed must be greater than zero."))

	pump_doc = frappe.get_doc("Fuel Pump", pump_name)
	reading_before = flt(pump_doc.current_meter_reading)
	reading_after = reading_before + qty

	# Unit rate & amount
	rate = flt(data.get("rate")) or get_effective_item_price(pump_doc.item, posting_date=nowdate())
	amount = round(qty * rate, 2)

	# Validate Fleet Credit if applicable
	contract_name = None
	if payment_method == "Customer Credit":
		if not customer:
			frappe.throw(_("Customer is required for Fleet Credit dispense."))
		credit_check = check_customer_credit_and_contract(customer, required_amount=amount, requested_quantity=qty)
		if not credit_check.get("allowed"):
			frappe.throw(_("Credit check failed: {0}").format(credit_check.get("message")))
		contract_name = credit_check.get("contract")

	# Validate Issue Order if applicable
	if payment_method == "Issue Order" and issue_order:
		val = validate_issue_order(issue_order, requested_quantity=qty)
		if not val.get("valid"):
			frappe.throw(_("Issue Order invalid: {0}").format(val.get("message")))

	# Create Fuel Dispense Event
	dispense = frappe.get_doc({
		"doctype": "Fuel Dispense Event",
		"station": station or pump_doc.station,
		"business_date": nowdate(),
		"shift": shift_name,
		"pump": pump_name,
		"tank": pump_doc.tank,
		"warehouse": pump_doc.warehouse,
		"item": pump_doc.item,
		"uom": pump_doc.uom or "Liter",
		"reading_before": reading_before,
		"reading_after": reading_after,
		"quantity": qty,
		"rate": rate,
		"amount": amount,
		"grand_total": amount,
		"payment_method": payment_method,
		"customer": customer,
		"vehicle_plate_number": vehicle_plate,
		"driver_name": driver_name,
		"issue_order": issue_order,
		"contract": contract_name,
		"status": "Recorded",
	})
	dispense.insert(ignore_permissions=True)
	try:
		dispense.submit()
	except Exception:
		pass

	# Update pump current meter reading
	pump_doc.db_set("current_meter_reading", reading_after)

	# If issue order, consume quota
	if payment_method == "Issue Order" and issue_order:
		try:
			consume_issue_order_quantity(issue_order, dispensed_quantity=qty, create_stock_entry=False)
		except Exception:
			pass

	return {
		"name": dispense.name,
		"status": dispense.status,
		"quantity": dispense.quantity,
		"grand_total": dispense.grand_total,
		"reading_after": reading_after,
		"print_format": "Fuel Dispense Thermal Receipt",
	}
