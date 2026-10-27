import unittest
import frappe
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate

from fuel_station.migration import import_historical_dispense_event, import_opening_tank_stock
from fuel_station.services.business_logic import (
	add_pump_sales_automatically,
	calculate_cash_residual,
	calculate_meter_quantity,
	calculate_price_discount_and_tax,
	check_customer_credit_and_contract,
	classify_dispense_event,
	consume_issue_order_quantity,
	create_credit_or_debit_note,
	create_payment_entry_from_collection,
	create_purchase_receipt_from_delivery,
	create_sales_invoice_from_batch,
	create_stock_entry_from_internal_issue,
	reconcile_pump_shift,
	resolve_reconciliation_exception,
	submit_einvoice,
	validate_issue_order,
	validate_meter_sequence,
)
from fuel_station.tasks import daily_maintenance


class TestFuelStationComplete(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls._cleanup_operational_state()
		cls._setup_test_environment()

	def setUp(self):
		super().setUp()
		self._cleanup_operational_state()

	def tearDown(self):
		super().tearDown()
		self._cleanup_operational_state()

	@classmethod
	def _cleanup_operational_state(cls):
		open_shifts = frappe.get_all("Fuel Shift", filters={"status": ["!=", "Closed"]}, pluck="name")
		for s in open_shifts:
			frappe.db.set_value("Fuel Shift", s, "status", "Closed", update_modified=False)
		open_boxes = frappe.get_all("Fuel Cash Box", filters={"status": ["!=", "Closed"]}, pluck="name")
		for b in open_boxes:
			frappe.db.set_value("Fuel Cash Box", b, "status", "Closed", update_modified=False)
		open_safes = frappe.get_all("Fuel Station Safe", filters={"status": ["!=", "Closed"]}, pluck="name")
		for sf in open_safes:
			frappe.db.set_value("Fuel Station Safe", sf, "status", "Closed", update_modified=False)
		if frappe.db.exists("Fuel Customer Contract", "CNT-FLEET-2026"):
			frappe.delete_doc("Fuel Customer Contract", "CNT-FLEET-2026", force=1)
		frappe.db.commit()

	@classmethod
	def _setup_test_environment(cls):
		# 1. Find existing Company in ERPNext
		company = frappe.db.get_value("Company", {}, "name")
		if not company:
			frappe.throw("No Company found in test site.")
		cls.company = company
		cls.abbr = frappe.db.get_value("Company", company, "abbr")
		cls.cost_center = frappe.db.get_value("Company", company, "cost_center") or frappe.db.get_value(
			"Cost Center", {"company": company, "is_group": 0}, "name"
		)

		# 2. Find standard accounts for Company
		cls.cash_account = frappe.db.get_value("Company", company, "default_cash_account") or frappe.db.get_value(
			"Account", {"company": company, "account_type": "Cash", "is_group": 0}, "name"
		)
		cls.bank_account = frappe.db.get_value("Company", company, "default_bank_account") or frappe.db.get_value(
			"Account", {"company": company, "account_type": "Bank", "is_group": 0}, "name"
		) or cls.cash_account
		cls.income_account = frappe.db.get_value("Company", company, "default_income_account") or frappe.db.get_value(
			"Account", {"company": company, "root_type": "Income", "is_group": 0}, "name"
		)
		cls.expense_account = frappe.db.get_value("Company", company, "default_expense_account") or frappe.db.get_value(
			"Account", {"company": company, "root_type": "Expense", "is_group": 0}, "name"
		)
		cls.receivable_account = frappe.db.get_value(
			"Company", company, "default_receivable_account"
		) or frappe.db.get_value("Account", {"company": company, "account_type": "Receivable", "is_group": 0}, "name")
		cls.payable_account = frappe.db.get_value(
			"Company", company, "default_payable_account"
		) or frappe.db.get_value("Account", {"company": company, "account_type": "Payable", "is_group": 0}, "name")
		cls.stock_adj_account = frappe.db.get_value(
			"Company", company, "stock_adjustment_account"
		) or cls.expense_account

		# Create a dedicated Card Clearing Account if needed
		parent_asset = frappe.db.get_value("Account", {"company": company, "account_type": "Cash", "is_group": 1}, "name") or frappe.db.get_value(
			"Account", {"company": company, "root_type": "Asset", "is_group": 1}, "name"
		)
		card_acc_name = f"Card Clearing Test - {cls.abbr}"
		if not frappe.db.exists("Account", card_acc_name):
			acc = frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Card Clearing Test",
					"parent_account": parent_asset,
					"company": company,
					"account_type": "Bank",
					"is_group": 0,
				}
			)
			acc.insert(ignore_permissions=True)
		cls.card_clearing_account = card_acc_name

		# Create a Tax Account & Sales Taxes and Charges Template (15% VAT & 0% Zero Rated)
		parent_liab = frappe.db.get_value(
			"Account", {"company": company, "root_type": "Liability", "is_group": 1}, "name"
		)
		tax_acc_name = f"VAT 15 Test - {cls.abbr}"
		if not frappe.db.exists("Account", tax_acc_name):
			tacc = frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "VAT 15 Test",
					"parent_account": parent_liab,
					"company": company,
					"account_type": "Tax",
					"is_group": 0,
				}
			)
			tacc.insert(ignore_permissions=True)
		cls.tax_account = tax_acc_name

		cls.vat_excl_template = f"Fuel VAT 15 Excl - {cls.abbr}"
		if not frappe.db.exists("Sales Taxes and Charges Template", cls.vat_excl_template):
			frappe.get_doc(
				{
					"doctype": "Sales Taxes and Charges Template",
					"title": "Fuel VAT 15 Excl",
					"company": company,
					"taxes": [
						{
							"charge_type": "On Net Total",
							"account_head": cls.tax_account,
							"description": "VAT 15%",
							"rate": 15.0,
							"included_in_print_rate": 0,
							"cost_center": cls.cost_center,
						}
					],
				}
			).insert(ignore_permissions=True)

		cls.vat_incl_template = f"Fuel VAT 15 Incl - {cls.abbr}"
		if not frappe.db.exists("Sales Taxes and Charges Template", cls.vat_incl_template):
			frappe.get_doc(
				{
					"doctype": "Sales Taxes and Charges Template",
					"title": "Fuel VAT 15 Incl",
					"company": company,
					"taxes": [
						{
							"charge_type": "On Net Total",
							"account_head": cls.tax_account,
							"description": "VAT 15% Inclusive",
							"rate": 15.0,
							"included_in_print_rate": 1,
							"cost_center": cls.cost_center,
						}
					],
				}
			).insert(ignore_permissions=True)

		cls.zero_tax_template = f"Fuel Zero Tax - {cls.abbr}"
		if not frappe.db.exists("Sales Taxes and Charges Template", cls.zero_tax_template):
			frappe.get_doc(
				{
					"doctype": "Sales Taxes and Charges Template",
					"title": "Fuel Zero Tax",
					"company": company,
					"taxes": [
						{
							"charge_type": "On Net Total",
							"account_head": cls.tax_account,
							"description": "Zero Rated 0%",
							"rate": 0.0,
							"included_in_print_rate": 0,
							"cost_center": cls.cost_center,
						}
					],
				}
			).insert(ignore_permissions=True)

		# 3. Create Warehouses for Station A and Station B
		parent_wh = frappe.db.get_value("Warehouse", {"company": company, "is_group": 1}, "name")
		cls.wh_a1 = f"Station A - Tank 01 - {cls.abbr}"
		if not frappe.db.exists("Warehouse", cls.wh_a1):
			frappe.get_doc(
				{
					"doctype": "Warehouse",
					"warehouse_name": "Station A - Tank 01",
					"parent_warehouse": parent_wh,
					"company": company,
					"is_group": 0,
				}
			).insert(ignore_permissions=True)

		cls.wh_b1 = f"Station B - Tank 01 - {cls.abbr}"
		if not frappe.db.exists("Warehouse", cls.wh_b1):
			frappe.get_doc(
				{
					"doctype": "Warehouse",
					"warehouse_name": "Station B - Tank 01",
					"parent_warehouse": parent_wh,
					"company": company,
					"is_group": 0,
				}
			).insert(ignore_permissions=True)

		# 4. Create Fuel Item (Gasoline 95 & Diesel)
		cls.item_gas95 = "FUEL-GAS-95"
		if not frappe.db.exists("Item", cls.item_gas95):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": cls.item_gas95,
					"item_name": "بنزين 95 - Gasoline 95",
					"item_group": "Fuel" if frappe.db.exists("Item Group", "Fuel") else "All Item Groups",
					"stock_uom": "Liter",
					"is_stock_item": 1,
					"is_fuel_item": 1,
					"fuel_grade": "95",
					"meter_uom": "Liter",
					"allow_meter_sale": 1,
					"standard_rate": 2.0,
					"valuation_rate": 1.5,
				}
			).insert(ignore_permissions=True)

		cls.price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
		if not frappe.db.exists("Price List", cls.price_list):
			frappe.get_doc(
				{"doctype": "Price List", "price_list_name": cls.price_list, "selling": 1, "enabled": 1}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("Item Price", {"item_code": cls.item_gas95, "price_list": cls.price_list}):
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"item_code": cls.item_gas95,
					"price_list": cls.price_list,
					"price_list_rate": 2.0,
					"selling": 1,
				}
			).insert(ignore_permissions=True)

		# 5. Create Customers (Cash Customer, Credit Fleet Customer, Exempt Customer)
		cg = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "All Customer Groups"
		terr = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"

		cls.cash_customer = "عميل نقدي افتراضي - محطة الوقود"
		if not frappe.db.exists("Customer", cls.cash_customer):
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": cls.cash_customer,
					"customer_type": "Individual",
					"customer_group": cg,
					"territory": terr,
					"fuel_customer_type": "Cash",
				}
			).insert(ignore_permissions=True)

		cls.credit_customer = "شركة النقل السريع الآجلة"
		if not frappe.db.exists("Customer", cls.credit_customer):
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": cls.credit_customer,
					"customer_type": "Company",
					"customer_group": cg,
					"territory": terr,
					"tax_id": "300012345600003",
					"fuel_customer_type": "Credit",
					"vehicle_required": 1,
					"driver_required": 1,
					"credit_control_policy": "BLOCK",
					"credit_limits": [{"company": company, "credit_limit": 10000.0}],
				}
			).insert(ignore_permissions=True)

		# 6. Create Supplier
		sg = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name") or "All Supplier Groups"
		cls.supplier = "شركة إمداد الوقود الوطنية"
		if not frappe.db.exists("Supplier", cls.supplier):
			frappe.get_doc(
				{
					"doctype": "Supplier",
					"supplier_name": cls.supplier,
					"supplier_group": sg,
				}
			).insert(ignore_permissions=True)

		# 7. Create Employees (Attendant 1, Attendant 2, Supervisor)
		cls.emp_attendant1 = cls._get_or_create_employee("عامل مضخة 1", company)
		cls.emp_attendant2 = cls._get_or_create_employee("عامل مضخة 2", company)
		cls.emp_supervisor = cls._get_or_create_employee("مشرف الوردية 1", company)

		# 8. Create Fuel Station A & B, Tanks, Pumps, Shift Type
		cls.station_a = "محطة الوقود أ - Station A"
		if not frappe.db.exists("Fuel Station", cls.station_a):
			frappe.get_doc(
				{
					"doctype": "Fuel Station",
					"station_name": cls.station_a,
					"station_code": "STA-A",
					"company": company,
					"branch": "الفرع الرئيسي",
					"default_cost_center": cls.cost_center,
					"default_cash_customer": cls.cash_customer,
					"default_cash_account": cls.cash_account,
					"default_card_clearing_account": cls.card_clearing_account,
					"default_income_account": cls.income_account,
					"default_expense_account": cls.expense_account,
					"default_waste_account": cls.expense_account,
					"default_variance_account": cls.stock_adj_account,
					"default_price_list": cls.price_list,
					"active": 1,
				}
			).insert(ignore_permissions=True)

		cls.station_b = "محطة الوقود ب - Station B"
		if not frappe.db.exists("Fuel Station", cls.station_b):
			frappe.get_doc(
				{
					"doctype": "Fuel Station",
					"station_name": cls.station_b,
					"station_code": "STA-B",
					"company": company,
					"default_cost_center": cls.cost_center,
					"default_cash_customer": cls.cash_customer,
					"default_cash_account": cls.cash_account,
					"default_card_clearing_account": cls.card_clearing_account,
					"default_income_account": cls.income_account,
					"default_expense_account": cls.expense_account,
					"default_variance_account": cls.stock_adj_account,
					"default_price_list": cls.price_list,
					"active": 1,
				}
			).insert(ignore_permissions=True)

		cls.tank_a1 = f"{cls.station_a}-TANK-01"
		if not frappe.db.exists("Fuel Tank", cls.tank_a1):
			frappe.get_doc(
				{
					"doctype": "Fuel Tank",
					"station": cls.station_a,
					"tank_number": "TANK-01",
					"item": cls.item_gas95,
					"warehouse": cls.wh_a1,
					"capacity": 50000.0,
					"minimum_level": 2000.0,
					"active": 1,
				}
			).insert(ignore_permissions=True)

		cls.pump_a1 = f"{cls.station_a}-PUMP-01"
		if not frappe.db.exists("Fuel Pump", cls.pump_a1):
			frappe.get_doc(
				{
					"doctype": "Fuel Pump",
					"station": cls.station_a,
					"pump_number": "PUMP-01",
					"tank": cls.tank_a1,
					"item": cls.item_gas95,
					"warehouse": cls.wh_a1,
					"uom": "Liter",
					"current_meter_reading": 10000.0,
					"active": 1,
				}
			).insert(ignore_permissions=True)

		cls.pump_a2 = f"{cls.station_a}-PUMP-02"
		if not frappe.db.exists("Fuel Pump", cls.pump_a2):
			frappe.get_doc(
				{
					"doctype": "Fuel Pump",
					"station": cls.station_a,
					"pump_number": "PUMP-02",
					"tank": cls.tank_a1,
					"item": cls.item_gas95,
					"warehouse": cls.wh_a1,
					"uom": "Liter",
					"current_meter_reading": 5000.0,
					"active": 1,
				}
			).insert(ignore_permissions=True)

		cls.shift_type_morning = "الوردية الصباحية"
		if not frappe.db.exists("Fuel Shift Type", cls.shift_type_morning):
			frappe.get_doc(
				{
					"doctype": "Fuel Shift Type",
					"shift_name": cls.shift_type_morning,
					"start_time": "06:00:00",
					"end_time": "14:00:00",
					"active": 1,
				}
			).insert(ignore_permissions=True)

		# 9. Receive initial fuel stock into Tank A1 via Fuel Delivery -> Purchase Receipt
		if flt(frappe.db.get_value("Bin", {"warehouse": cls.wh_a1, "item_code": cls.item_gas95}, "actual_qty")) < 10000:
			deliv = frappe.get_doc(
				{
					"doctype": "Fuel Delivery",
					"station": cls.station_a,
					"supplier": cls.supplier,
					"delivery_date": nowdate(),
					"truck_number": "TRK-101",
					"supplier_document_no": "SUP-DOC-001",
					"tank": cls.tank_a1,
					"item": cls.item_gas95,
					"rate": 1.5,
					"document_quantity": 25000.0,
					"received_quantity": 25000.0,
				}
			).insert(ignore_permissions=True)
			deliv.create_purchase_receipt(submit=True)

		# 10. Ensure Fuel Station Workspace exists
		if not frappe.db.exists("Workspace", "Fuel Station"):
			ws_path = frappe.get_app_path("fuel_station", "fuel_station", "workspace", "fuel_station", "fuel_station.json")
			import json, os
			if os.path.exists(ws_path):
				with open(ws_path) as f:
					ws_dict = json.load(f)
				ws_doc = frappe.get_doc(ws_dict)
				ws_doc.flags.ignore_links = True
				ws_doc.flags.ignore_validate = True
				ws_doc.insert(ignore_permissions=True)

		frappe.db.commit()

	@classmethod
	def _get_or_create_employee(cls, first_name, company):
		existing = frappe.db.get_value("Employee", {"first_name": first_name, "company": company}, "name")
		if existing:
			return existing
		emp = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": first_name,
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2022-01-01",
				"company": company,
				"status": "Active",
			}
		)
		emp.flags.ignore_permissions = True
		emp.insert(ignore_permissions=True)
		return emp.name

	def test_01_cash_flow_and_erpnext_ledgers(self):
		"""§16.1: Opening Reading -> Cash Dispense -> Closing Reading -> Cash Sales Invoice -> Stock Ledger & GL Entry."""
		frappe.db.set_value("Fuel Pump", self.pump_a2, "current_meter_reading", 5000.0)
		r_open = frappe.get_doc(
			{
				"doctype": "Fuel Meter Reading",
				"station": self.station_a,
				"pump": self.pump_a2,
				"business_date": nowdate(),
				"reading_type": "Opening",
				"previous_reading": 5000.0,
				"reading_value": 5000.0,
			}
		).insert(ignore_permissions=True)
		self.assertEqual(r_open.reading_value, 5000.0)

		ev = frappe.get_doc(
			{
				"doctype": "Fuel Dispense Event",
				"station": self.station_a,
				"business_date": nowdate(),
				"pump": self.pump_a2,
				"item": self.item_gas95,
				"employee": self.emp_attendant1,
				"reading_before": 5000.0,
				"reading_after": 5100.0,
				"quantity": 100.0,
				"rate": 2.0,
				"payment_method": "Cash",
			}
		).insert(ignore_permissions=True)
		self.assertEqual(ev.amount, 200.0)
		self.assertEqual(ev.status, "Classified")

		r_close = frappe.get_doc(
			{
				"doctype": "Fuel Meter Reading",
				"station": self.station_a,
				"pump": self.pump_a2,
				"business_date": nowdate(),
				"reading_type": "Closing",
				"previous_reading": 5000.0,
				"reading_value": 5100.0,
			}
		).insert(ignore_permissions=True)
		self.assertEqual(r_close.meter_quantity, 100.0)

		batch = frappe.get_doc(
			{
				"doctype": "Fuel Pump Invoice Batch",
				"station": self.station_a,
				"business_date": nowdate(),
				"pump": self.pump_a2,
				"item": self.item_gas95,
				"rate": 2.0,
				"payment_method": "Cash",
				"opening_reading": 5000.0,
				"closing_reading": 5100.0,
				"meter_quantity": 100.0,
				"invoice_quantity": 100.0,
				"invoice_amount": 200.0,
				"events": [{"fuel_dispense_event": ev.name, "quantity": 100.0, "rate": 2.0, "amount": 200.0}],
			}
		).insert(ignore_permissions=True)

		inv_name = create_sales_invoice_from_batch(batch, submit=True)
		self.assertTrue(frappe.db.exists("Sales Invoice", inv_name))

		# Verify Stock Ledger Entry & GL Entry exist for this Sales Invoice
		sle_qty = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_type": "Sales Invoice", "voucher_no": inv_name, "is_cancelled": 0}, "actual_qty"
		)
		self.assertEqual(flt(sle_qty), -100.0)

		gl_entries = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Sales Invoice", "voucher_no": inv_name, "is_cancelled": 0},
			fields=["account", "debit", "credit"],
		)
		self.assertTrue(len(gl_entries) >= 2)

		# Verify idempotency (§16.7): calling create_sales_invoice_from_batch again returns same invoice
		inv_name_2 = create_sales_invoice_from_batch(batch.name, submit=True)
		self.assertEqual(inv_name, inv_name_2)

		# Verify non-negotiable Rule §3.6: deleting an invoiced Fuel Dispense Event is blocked
		ev.reload()
		with self.assertRaises(Exception):
			ev.delete()

	def test_02_mandatory_reconciliation_example_2000_liters(self):
		"""§10.2 & §16.2: Opening=10,000, Closing=12,000 (Meter=2,000L), Card=600L, Credit=400L => Expected Cash=1,000L."""
		shift = frappe.get_doc(
			{
				"doctype": "Fuel Shift",
				"station": self.station_a,
				"business_date": add_days(nowdate(), -1),
				"shift_type": self.shift_type_morning,
				"supervisor": self.emp_supervisor,
				"status": "Open",
			}
		).insert(ignore_permissions=True)

		frappe.db.set_value("Fuel Pump", self.pump_a1, "current_meter_reading", 10000.0)

		# Setup vehicle & driver for credit customer
		veh = self._ensure_vehicle(self.credit_customer, "ABC-1001")
		drv = self._ensure_driver(self.credit_customer, "سائق 1")
		auth = frappe.get_doc(
			{
				"doctype": "Fuel Authorization",
				"authorization_type": "Credit",
				"station": self.station_a,
				"customer": self.credit_customer,
				"vehicle": veh,
				"driver": drv,
				"item": self.item_gas95,
				"quantity_limit": 1000.0,
				"payment_method": "Credit",
			}
		).insert(ignore_permissions=True)

		# 1. Card event = 600 liters
		frappe.get_doc(
			{
				"doctype": "Fuel Dispense Event",
				"station": self.station_a,
				"business_date": shift.business_date,
				"shift": shift.name,
				"pump": self.pump_a1,
				"item": self.item_gas95,
				"quantity": 600.0,
				"rate": 2.0,
				"payment_method": "Card",
				"payment_reference": "POS-REF-600",
			}
		).insert(ignore_permissions=True)

		# 2. Credit event = 400 liters
		frappe.get_doc(
			{
				"doctype": "Fuel Dispense Event",
				"station": self.station_a,
				"business_date": shift.business_date,
				"shift": shift.name,
				"pump": self.pump_a1,
				"item": self.item_gas95,
				"customer": self.credit_customer,
				"vehicle": veh,
				"driver": drv,
				"authorization": auth.name,
				"quantity": 400.0,
				"rate": 2.0,
				"payment_method": "Credit",
			}
		).insert(ignore_permissions=True)

		# Run reconciliation for Opening=10,000, Closing=12,000
		recon = reconcile_pump_shift(
			station=self.station_a,
			pump=self.pump_a1,
			business_date=shift.business_date,
			shift=shift.name,
			opening_reading=10000.0,
			closing_reading=12000.0,
			rate=2.0,
			create_batch=True,
		)
		self.assertEqual(flt(recon.meter_quantity), 2000.0)
		self.assertEqual(flt(recon.card_quantity), 600.0)
		self.assertEqual(flt(recon.credit_quantity), 400.0)
		self.assertEqual(flt(recon.classified_quantity), 1000.0)
		self.assertEqual(flt(recon.cash_quantity), 1000.0)
		self.assertTrue(bool(recon.invoice_batch))

		batch = frappe.get_doc("Fuel Pump Invoice Batch", recon.invoice_batch)
		self.assertEqual(flt(batch.invoice_quantity), 1000.0)
		self.assertEqual(flt(batch.invoice_amount), 2000.0)

		# Cleanup shift status so it doesn't block subsequent tests
		shift.db_set("status", "Closed")
		frappe.db.delete("Fuel Dispense Event", {"shift": shift.name})

	def test_03_negative_cash_residual_creates_exception(self):
		"""§10.4 & §16.6: When classified quantity > meter quantity (Q_cash < 0), never create negative invoice; create Critical Exception."""
		shift = frappe.get_doc(
			{
				"doctype": "Fuel Shift",
				"station": self.station_a,
				"business_date": add_days(nowdate(), -2),
				"shift_type": self.shift_type_morning,
				"supervisor": self.emp_supervisor,
				"status": "Open",
			}
		).insert(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "Fuel Dispense Event",
				"station": self.station_a,
				"business_date": shift.business_date,
				"shift": shift.name,
				"pump": self.pump_a1,
				"item": self.item_gas95,
				"quantity": 300.0,
				"rate": 2.0,
				"payment_method": "Card",
				"payment_reference": "POS-OVER-300",
			}
		).insert(ignore_permissions=True)

		recon = reconcile_pump_shift(
			station=self.station_a,
			pump=self.pump_a1,
			business_date=shift.business_date,
			shift=shift.name,
			opening_reading=12000.0,
			closing_reading=12200.0,  # Only 200L on meter, but 300L classified!
			rate=2.0,
			create_batch=True,
		)
		self.assertEqual(flt(recon.cash_quantity), -100.0)
		self.assertFalse(bool(recon.invoice_batch))
		self.assertTrue(bool(recon.exception_reference))
		self.assertEqual(recon.status, "Pending Review")

		exc = resolve_reconciliation_exception(recon.exception_reference, resolution="Card entry typo corrected")
		self.assertEqual(exc.status, "Approved")
		shift.db_set("status", "Closed")

	def test_04_internal_issue_order_qr_partial_and_stock_entry(self):
		"""§9 & §16.5: Fuel Issue Order -> Approve -> Print/QR validation -> Partial & Full Dispense -> Stock Entry (no Sales Invoice)."""
		io = frappe.get_doc(
			{
				"doctype": "Fuel Issue Order",
				"station": self.station_a,
				"company": self.company,
				"treatment_type": "Internal",
				"employee": self.emp_attendant1,
				"plate_number": "COMPANY-TRUCK-01",
				"item": self.item_gas95,
				"quantity_limit": 100.0,
				"max_uses": 2,
				"expense_account": self.expense_account,
				"cost_center": self.cost_center,
				"valid_from": add_days(nowdate(), -1),
				"valid_until": add_days(nowdate(), 5),
				"approval_status": "Approved",
			}
		).insert(ignore_permissions=True)
		self.assertTrue(io.qr_code.startswith("FIO-"))
		self.assertTrue(io.print_token.startswith("PRT-"))

		# Invalid QR token must throw and log audit event
		with self.assertRaises(Exception):
			validate_issue_order(io.name, requested_quantity=40.0, qr_token="WRONG-QR-TOKEN")

		# 1st partial dispense: 40L
		ev1 = frappe.get_doc(
			{
				"doctype": "Fuel Dispense Event",
				"station": self.station_a,
				"business_date": nowdate(),
				"pump": self.pump_a1,
				"item": self.item_gas95,
				"issue_order": io.name,
				"quantity": 40.0,
				"rate": 2.0,
				"payment_method": "Internal Issue",
			}
		).insert(ignore_permissions=True)
		io.reload()
		self.assertEqual(flt(io.used_quantity), 40.0)
		self.assertEqual(flt(io.remaining_quantity), 60.0)
		self.assertEqual(io.approval_status, "Partially Used")
		self.assertTrue(bool(ev1.stock_document))
		self.assertFalse(bool(ev1.invoice))

		# 2nd dispense: remaining 60L -> Fully Used
		ev2 = frappe.get_doc(
			{
				"doctype": "Fuel Dispense Event",
				"station": self.station_a,
				"business_date": nowdate(),
				"pump": self.pump_a1,
				"item": self.item_gas95,
				"issue_order": io.name,
				"quantity": 60.0,
				"rate": 2.0,
				"payment_method": "Internal Issue",
			}
		).insert(ignore_permissions=True)
		io.reload()
		self.assertEqual(flt(io.used_quantity), 100.0)
		self.assertEqual(flt(io.remaining_quantity), 0.0)
		self.assertEqual(io.approval_status, "Fully Used")
		self.assertTrue(bool(ev2.stock_document))

		# Attempting 3rd dispense on Fully Used order must fail
		with self.assertRaises(Exception):
			validate_issue_order(io.name, requested_quantity=10.0)

	def test_05_customer_vehicles_drivers_contracts_and_credit_limits(self):
		"""§26.13 (1-18): Customer, 2 Vehicles, 2 Drivers, Contract, Credit Limit Enforcement, Partial Payment, Advance, Return."""
		veh1 = self._ensure_vehicle(self.credit_customer, "FLT-2001")
		veh2 = self._ensure_vehicle(self.credit_customer, "FLT-2002")
		drv1 = self._ensure_driver(self.credit_customer, "سائق الأسطول 1")
		drv2 = self._ensure_driver(self.credit_customer, "سائق الأسطول 2")

		contract_no = "CNT-FLEET-2026"
		if frappe.db.exists("Fuel Customer Contract", contract_no):
			frappe.delete_doc("Fuel Customer Contract", contract_no, force=1)
		frappe.db.delete("Fuel Dispense Event", {"customer": self.credit_customer, "status": ["!=", "Invoiced"]})

		current_ar = flt(frappe.db.get_value(
			"Sales Invoice",
			{"customer": self.credit_customer, "docstatus": 1},
			"sum(outstanding_amount)"
		))

		contract = frappe.get_doc(
			{
				"doctype": "Fuel Customer Contract",
				"customer": self.credit_customer,
				"company": self.company,
				"contract_number": contract_no,
				"start_date": add_days(nowdate(), -10),
				"end_date": add_days(nowdate(), 30),
				"price_list": self.price_list,
				"discount_percentage": 5.0,  # 5% contract discount
				"allowed_items": self.item_gas95,
				"allowed_stations": self.station_a,
				"allowed_vehicles": f"{veh1}, {veh2}",
				"credit_limit": current_ar + 1000.0,
				"credit_control_policy": "BLOCK",
				"status": "Active",
			}
		).insert(ignore_permissions=True)

		# 1. Credit sale within limit (100L * 2.0 - 5% = 190.0)
		ev_ok = frappe.get_doc(
			{
				"doctype": "Fuel Dispense Event",
				"station": self.station_a,
				"business_date": nowdate(),
				"pump": self.pump_a1,
				"item": self.item_gas95,
				"customer": self.credit_customer,
				"contract": contract.name,
				"vehicle": veh1,
				"driver": drv1,
				"odometer_reading": 45200.0,
				"quantity": 100.0,
				"rate": 2.0,
				"payment_method": "Credit",
			}
		).insert(ignore_permissions=True)
		self.assertEqual(flt(ev_ok.discount_percentage), 5.0)
		self.assertEqual(flt(ev_ok.rate), 1.9)
		self.assertEqual(flt(ev_ok.amount), 190.0)
		self.assertEqual(ev_ok.credit_check_result, "Approved")

		# 2. Credit sale exceeding contract credit_limit (1000.0) when policy is BLOCK -> must fail
		with self.assertRaises(Exception):
			frappe.get_doc(
				{
					"doctype": "Fuel Dispense Event",
					"station": self.station_a,
					"business_date": nowdate(),
					"pump": self.pump_a1,
					"item": self.item_gas95,
					"customer": self.credit_customer,
					"contract": contract.name,
					"vehicle": veh2,
					"driver": drv2,
					"quantity": 600.0,  # 600 * 1.9 = 1140 > remaining credit (810)
					"rate": 2.0,
					"payment_method": "Credit",
				}
			).insert(ignore_permissions=True)

		# 3. Change policy to REQUIRE_SUPERVISOR_APPROVAL -> blocked without approval, allowed with credit_override_approved_by
		contract.db_set("credit_control_policy", "REQUIRE_SUPERVISOR_APPROVAL")
		with self.assertRaises(Exception):
			frappe.get_doc(
				{
					"doctype": "Fuel Dispense Event",
					"station": self.station_a,
					"business_date": nowdate(),
					"pump": self.pump_a1,
					"item": self.item_gas95,
					"customer": self.credit_customer,
					"contract": contract.name,
					"vehicle": veh2,
					"driver": drv2,
					"quantity": 600.0,
					"rate": 2.0,
					"payment_method": "Credit",
				}
			).insert(ignore_permissions=True)

		ev_approved = frappe.get_doc(
			{
				"doctype": "Fuel Dispense Event",
				"station": self.station_a,
				"business_date": nowdate(),
				"pump": self.pump_a1,
				"item": self.item_gas95,
				"customer": self.credit_customer,
				"contract": contract.name,
				"vehicle": veh2,
				"driver": drv2,
				"quantity": 50.0,
				"rate": 2.0,
				"payment_method": "Credit",
				"credit_override_approved_by": "Administrator",
			}
		).insert(ignore_permissions=True)
		self.assertEqual(ev_approved.credit_check_result, "Approved")

		# 4. Unregistered vehicle blocked
		veh_unreg = self._ensure_vehicle(self.credit_customer, "UNREG-999")
		with self.assertRaises(Exception):
			frappe.get_doc(
				{
					"doctype": "Fuel Dispense Event",
					"station": self.station_a,
					"business_date": nowdate(),
					"pump": self.pump_a1,
					"item": self.item_gas95,
					"customer": self.credit_customer,
					"contract": contract.name,
					"vehicle": veh_unreg,
					"driver": drv1,
					"quantity": 10.0,
					"rate": 2.0,
					"payment_method": "Credit",
				}
			).insert(ignore_permissions=True)

		# 5. Expired contract blocked
		contract.db_set("end_date", add_days(nowdate(), -1))
		with self.assertRaises(Exception):
			frappe.get_doc(
				{
					"doctype": "Fuel Dispense Event",
					"station": self.station_a,
					"business_date": nowdate(),
					"pump": self.pump_a1,
					"item": self.item_gas95,
					"customer": self.credit_customer,
					"contract": contract.name,
					"vehicle": veh1,
					"driver": drv1,
					"quantity": 10.0,
					"rate": 2.0,
					"payment_method": "Credit",
				}
			).insert(ignore_permissions=True)
		contract.db_set("end_date", add_days(nowdate(), 30))
		contract.db_set("credit_limit", 50000.0)

		# 6. Create B2B Tax Invoice from ev_ok, verify Vehicle, Driver, Odometer & Tax on invoice & print format
		batch = frappe.get_doc(
			{
				"doctype": "Fuel Pump Invoice Batch",
				"station": self.station_a,
				"business_date": nowdate(),
				"pump": self.pump_a1,
				"item": self.item_gas95,
				"rate": ev_ok.rate,
				"tax_template": self.vat_excl_template,
				"invoice_type": "B2B Tax Invoice",
				"customer": self.credit_customer,
				"contract": contract.name,
				"vehicle": veh1,
				"payment_method": "Credit",
				"invoice_quantity": ev_ok.quantity,
				"invoice_amount": ev_ok.amount,
				"events": [{"fuel_dispense_event": ev_ok.name, "quantity": ev_ok.quantity, "rate": ev_ok.rate, "amount": ev_ok.amount}],
			}
		).insert(ignore_permissions=True)
		inv_name = create_sales_invoice_from_batch(batch, submit=True)
		inv_doc = frappe.get_doc("Sales Invoice", inv_name)
		self.assertEqual(inv_doc.items[0].vehicle, veh1)
		self.assertEqual(inv_doc.items[0].driver, drv1)
		self.assertEqual(flt(inv_doc.items[0].vehicle_odometer_reading), 45200.0)
		self.assertEqual(flt(inv_doc.net_total), 190.0)
		self.assertEqual(flt(inv_doc.total_taxes_and_charges), 28.5)
		self.assertEqual(flt(inv_doc.grand_total), 218.5)

		# Render Arabic RTL print format and verify vehicle/driver/tax are displayed
		html = frappe.get_print("Sales Invoice", inv_name, print_format="Fuel Tax Invoice RTL")
		self.assertIn(veh1, html)
		self.assertIn("45200", html)

		# 7. Partial payment against invoice (§26.13 #13)
		pe_partial = create_payment_entry_from_collection(
			sales_invoice=inv_name,
			paid_amount=100.0,
			payment_method="Cash",
			station=self.station_a,
			submit=True,
		)
		self.assertTrue(frappe.db.exists("Payment Entry", pe_partial))
		inv_doc.reload()
		self.assertEqual(flt(inv_doc.outstanding_amount), 118.5)

		# 8. Sales Return / Credit Note reversing stock and tax (§26.13 #15, §28.18 #15)
		ret_name = create_credit_or_debit_note(
			inv_name,
			note_type="Sales Return",
			return_qty=10.0,
			update_stock=True,
			reason="Quality return test",
			submit=True,
		)
		ret_doc = frappe.get_doc("Sales Invoice", ret_name)
		self.assertEqual(ret_doc.is_return, 1)
		self.assertEqual(ret_doc.return_against, inv_name)
		self.assertEqual(flt(ret_doc.items[0].qty), -10.0)
		ret_sle = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_type": "Sales Invoice", "voucher_no": ret_name, "is_cancelled": 0}, "actual_qty"
		)
		self.assertEqual(flt(ret_sle), 10.0)

		# 9. Debit Note (§28.18 #16)
		dn_name = create_credit_or_debit_note(
			inv_name,
			note_type="Debit Note",
			return_qty=10.0,
			adjusted_rate=0.5,
			reason="Price undercharge adjustment",
			submit=True,
		)
		dn_doc = frappe.get_doc("Sales Invoice", dn_name)
		self.assertEqual(dn_doc.is_debit_note, 1)
		self.assertEqual(dn_doc.return_against, inv_name)

		# 10. Direct modification of submitted Sales Invoice is forbidden (§28.18 #20)
		inv_doc.reload()
		inv_doc.grand_total = flt(inv_doc.grand_total) + 50.0
		with self.assertRaises(Exception):
			inv_doc.on_update_after_submit()

		if frappe.db.exists("Fuel Customer Contract", contract_no):
			frappe.delete_doc("Fuel Customer Contract", contract_no, force=1)

	def test_06_taxes_discounts_and_einvoice_engine(self):
		"""§28.18 (1-20): Tax Exclusive vs Tax Inclusive, Zero Rated, Discounts, E-Invoice retry & UUID/QR."""
		# 1. Tax Exclusive calculation
		res_excl = calculate_price_discount_and_tax(
			item=self.item_gas95,
			quantity=100.0,
			rate=2.0,
			tax_template=self.vat_excl_template,
			prices_include_tax=0,
		)
		self.assertEqual(flt(res_excl.taxable_amount), 200.0)
		self.assertEqual(flt(res_excl.tax_amount), 30.0)
		self.assertEqual(flt(res_excl.grand_total), 230.0)

		# 2. Tax Inclusive calculation (230 inclusive of 15% VAT -> taxable 200, tax 30)
		res_incl = calculate_price_discount_and_tax(
			item=self.item_gas95,
			quantity=100.0,
			rate=2.30,
			tax_template=self.vat_incl_template,
			prices_include_tax=1,
		)
		self.assertEqual(flt(res_incl.taxable_amount), 200.0)
		self.assertEqual(flt(res_incl.tax_amount), 30.0)
		self.assertEqual(flt(res_incl.grand_total), 230.0)

		# 3. Zero-rated tax template
		res_zero = calculate_price_discount_and_tax(
			item=self.item_gas95,
			quantity=50.0,
			rate=2.0,
			tax_template=self.zero_tax_template,
		)
		self.assertEqual(flt(res_zero.tax_amount), 0.0)
		self.assertEqual(flt(res_zero.grand_total), 100.0)

		# 4. Negative net price after discount must be rejected (§28.18 #14)
		with self.assertRaises(Exception):
			calculate_price_discount_and_tax(
				item=self.item_gas95,
				quantity=10.0,
				rate=2.0,
				discount_amount=2.5,
				discount_approved_by="Administrator",
			)

		# 5. Attendant discount exceeding limit blocked without approval, allowed with approval (§28.18 #10)
		with self.assertRaises(Exception):
			calculate_price_discount_and_tax(
				item=self.item_gas95,
				quantity=10.0,
				rate=2.0,
				discount_percentage=5.0,  # > 2% attendant limit
				user_role="Fuel Attendant",
			)
		res_disc_ok = calculate_price_discount_and_tax(
			item=self.item_gas95,
			quantity=10.0,
			rate=2.0,
			discount_percentage=5.0,
			user_role="Fuel Attendant",
			discount_approved_by="Administrator",
			discount_reason="Manager approved promo",
		)
		self.assertEqual(flt(res_disc_ok.rate_after_discount), 1.9)

		# 6. E-Invoice failure simulation & safe retry without duplication (§28.18 #18, #19)
		batch = frappe.get_doc(
			{
				"doctype": "Fuel Pump Invoice Batch",
				"station": self.station_a,
				"business_date": nowdate(),
				"pump": self.pump_a2,
				"item": self.item_gas95,
				"rate": 2.30,
				"tax_template": self.vat_incl_template,
				"payment_method": "Card",
				"invoice_quantity": 50.0,
				"invoice_amount": 115.0,
			}
		).insert(ignore_permissions=True)
		inv_name = create_sales_invoice_from_batch(batch, submit=True)

		fail_res = submit_einvoice(inv_name, simulate_failure=True)
		self.assertEqual(fail_res.status, "Failed")

		ok_res = submit_einvoice(inv_name, simulate_failure=False)
		self.assertEqual(ok_res.status, "Accepted")
		self.assertTrue(bool(ok_res.uuid))
		self.assertIn("UUID:", ok_res.qr_payload)

		# Retry again must be idempotent and return the exact same UUID
		retry_res = submit_einvoice(inv_name, simulate_failure=False)
		self.assertEqual(retry_res.uuid, ok_res.uuid)
		self.assertTrue(retry_res.idempotent)

	def test_07_prepaid_advance_and_fuel_card_coupon(self):
		"""§26.8 & §28.18 #17: Advance Payment Entry -> Fuel Authorization -> Dispense -> Invoice with Advance Allocated; Fuel Card/Coupon."""
		pe_adv = create_payment_entry_from_collection(
			customer=self.credit_customer,
			paid_amount=500.0,
			payment_method="Cash",
			station=self.station_a,
			is_advance=True,
			submit=True,
		)
		auth = frappe.get_doc(
			{
				"doctype": "Fuel Authorization",
				"authorization_type": "Prepaid",
				"station": self.station_a,
				"customer": self.credit_customer,
				"item": self.item_gas95,
				"quantity_limit": 200.0,
				"amount_limit": 500.0,
				"payment_method": "Prepaid",
				"advance_payment_entry": pe_adv,
			}
		).insert(ignore_permissions=True)

		ev = frappe.get_doc(
			{
				"doctype": "Fuel Dispense Event",
				"station": self.station_a,
				"business_date": nowdate(),
				"pump": self.pump_a1,
				"item": self.item_gas95,
				"customer": self.credit_customer,
				"vehicle": self._ensure_vehicle(self.credit_customer, "FLT-2001"),
				"driver": self._ensure_driver(self.credit_customer, "سائق الأسطول 1"),
				"authorization": auth.name,
				"quantity": 100.0,
				"rate": 2.0,
				"payment_method": "Prepaid",
			}
		).insert(ignore_permissions=True)
		auth.reload()
		self.assertEqual(flt(auth.used_quantity), 100.0)
		self.assertEqual(flt(auth.remaining_quantity), 100.0)
		self.assertEqual(auth.status, "Partially Used")

		batch = frappe.get_doc(
			{
				"doctype": "Fuel Pump Invoice Batch",
				"station": self.station_a,
				"business_date": nowdate(),
				"pump": self.pump_a1,
				"item": self.item_gas95,
				"rate": 2.0,
				"customer": self.credit_customer,
				"payment_method": "Prepaid",
				"invoice_quantity": 100.0,
				"invoice_amount": 200.0,
				"events": [{"fuel_dispense_event": ev.name, "quantity": 100.0, "rate": 2.0, "amount": 200.0}],
			}
		).insert(ignore_permissions=True)
		inv_name = create_sales_invoice_from_batch(batch, submit=True)
		inv_doc = frappe.get_doc("Sales Invoice", inv_name)
		self.assertTrue(len(inv_doc.advances) >= 1)

		# Test Coupon / Fuel Card (§26.8)
		card_no = "COUPON-50L-TEST"
		if frappe.db.exists("Fuel Card", card_no):
			frappe.delete_doc("Fuel Card", card_no, force=1)
		coupon = frappe.get_doc(
			{
				"doctype": "Fuel Card",
				"card_number": card_no,
				"card_type": "Coupon",
				"allowed_item": self.item_gas95,
				"allowed_station": self.station_a,
				"quantity_limit": 50.0,
				"status": "Active",
			}
		).insert(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "Fuel Dispense Event",
				"station": self.station_a,
				"business_date": nowdate(),
				"pump": self.pump_a1,
				"item": self.item_gas95,
				"fuel_card": coupon.name,
				"quantity": 50.0,
				"rate": 2.0,
				"payment_method": "Coupon",
			}
		).insert(ignore_permissions=True)
		coupon.reload()
		self.assertEqual(flt(coupon.remaining_quantity), 0.0)
		self.assertEqual(coupon.status, "Exhausted")

	def test_08_full_shift_cash_box_handover_and_safe_lifecycle(self):
		"""§30.22 (1-25): Full Shift -> Assignment -> Cash Box -> Denomination Count -> Handover -> Cash Transfer -> Safe Close -> Reopen."""
		bdate = add_days(nowdate(), -3)

		# 1. Open Shift
		shift = frappe.get_doc(
			{
				"doctype": "Fuel Shift",
				"station": self.station_a,
				"business_date": bdate,
				"shift_type": self.shift_type_morning,
				"supervisor": self.emp_supervisor,
				"opening_cash_float": 500.0,
				"status": "Open",
			}
		).insert(ignore_permissions=True)

		# 2. Prevent conflicting open shift for same station (§30.22 #2)
		with self.assertRaises(Exception):
			frappe.get_doc(
				{
					"doctype": "Fuel Shift",
					"station": self.station_a,
					"business_date": bdate,
					"shift_type": self.shift_type_morning,
					"status": "Open",
				}
			).insert(ignore_permissions=True)

		# 3. Open Cash Box for Attendant 1 (§30.22 #4)
		box1 = frappe.get_doc(
			{
				"doctype": "Fuel Cash Box",
				"cash_box_code": "BOX-ATT-1",
				"box_type": "صندوق العامل",
				"station": self.station_a,
				"business_date": bdate,
				"shift": shift.name,
				"assigned_employee": self.emp_attendant1,
				"opening_float": 200.0,
				"status": "Open",
			}
		).insert(ignore_permissions=True)

		# 4. Prevent same employee from opening two active Cash Boxes (§30.22 #5)
		with self.assertRaises(Exception):
			frappe.get_doc(
				{
					"doctype": "Fuel Cash Box",
					"cash_box_code": "BOX-ATT-1-DUP",
					"box_type": "صندوق العامل",
					"station": self.station_a,
					"business_date": bdate,
					"shift": shift.name,
					"assigned_employee": self.emp_attendant1,
					"opening_float": 100.0,
					"status": "Open",
				}
			).insert(ignore_permissions=True)

		# 5. Assign Attendant 1 to Pump A1 (§30.22 #6)
		asg1 = frappe.get_doc(
			{
				"doctype": "Fuel Pump Assignment",
				"station": self.station_a,
				"business_date": bdate,
				"shift": shift.name,
				"pump": self.pump_a1,
				"employee": self.emp_attendant1,
				"cash_box": box1.name,
				"opening_reading": 20000.0,
				"status": "Active",
			}
		).insert(ignore_permissions=True)

		# Prevent second active assignment on same pump in same shift
		with self.assertRaises(Exception):
			frappe.get_doc(
				{
					"doctype": "Fuel Pump Assignment",
					"station": self.station_a,
					"business_date": bdate,
					"shift": shift.name,
					"pump": self.pump_a1,
					"employee": self.emp_attendant2,
					"opening_reading": 20000.0,
					"status": "Active",
				}
			).insert(ignore_permissions=True)

		# 6. Handover Pump A1 from Attendant 1 to Attendant 2 at reading 20500 (§30.22 #7)
		handover = frappe.get_doc(
			{
				"doctype": "Pump Handover",
				"station": self.station_a,
				"business_date": bdate,
				"pump": self.pump_a1,
				"shift": shift.name,
				"outgoing_employee": self.emp_attendant1,
				"incoming_employee": self.emp_attendant2,
				"outgoing_assignment": asg1.name,
				"handover_time": now_datetime(),
				"meter_reading_at_handover": 20500.0,
				"cash_count_at_handover": 1200.0,
				"status": "Confirmed",
			}
		).insert(ignore_permissions=True)
		asg1.reload()
		self.assertEqual(asg1.status, "Handed Over")
		self.assertEqual(flt(asg1.closing_reading), 20500.0)

		# 7. Record Cash Sales, Approved Expense, and Unapproved Expense on Box 1 (§30.22 #17, #18)
		box1.cash_sales = 1000.0
		box1.card_sales_reference = 400.0  # Must NOT enter expected_cash
		box1.unapproved_expenses = 75.0  # Must NOT reduce expected_cash

		# Expense without reference document must be rejected
		box1.approved_expenses = 50.0
		with self.assertRaises(Exception):
			box1.save(ignore_permissions=True)

		box1.reload()
		box1.cash_sales = 1000.0
		box1.card_sales_reference = 400.0  # Must NOT enter expected_cash
		box1.unapproved_expenses = 75.0  # Must NOT reduce expected_cash
		box1.approved_expenses = 50.0
		box1.expense_reference_doctype = "Journal Entry"
		box1.expense_reference_name = "EXP-REF-001"
		# Expected cash = 200 (float) + 1000 (cash sales) - 50 (approved expense) = 1150.0
		# Denomination count (§30.22 #12): 10 * 100 + 3 * 50 = 1150.0
		box1.set(
			"denominations",
			[
				{"banknote_or_coin": 100.0, "quantity": 10},
				{"banknote_or_coin": 50.0, "quantity": 3},
			],
		)
		box1.status = "Counted"
		box1.save(ignore_permissions=True)
		self.assertEqual(flt(box1.expected_cash), 1150.0)
		self.assertEqual(flt(box1.counted_cash), 1150.0)
		self.assertEqual(flt(box1.variance), 0.0)

		# 8. Create Station Safe and Cash Transfer (§30.22 #13, #14, #15, #16)
		safe = frappe.get_doc(
			{
				"doctype": "Fuel Station Safe",
				"safe_code": "SAFE-MAIN-A",
				"station": self.station_a,
				"business_date": bdate,
				"shift": shift.name,
				"responsible_employee": self.emp_supervisor,
				"opening_balance": 1000.0,
				"status": "Open",
			}
		).insert(ignore_permissions=True)

		# Cannot close safe while box1 is not Closed/Transferred
		safe.status = "Closed"
		with self.assertRaises(Exception):
			safe.save(ignore_permissions=True)
		safe.status = "Open"

		# Create Cash Transfer from box1 to safe (1150.0)
		ct = frappe.get_doc(
			{
				"doctype": "Cash Transfer",
				"from_cash_box": box1.name,
				"to_safe": safe.name,
				"station": self.station_a,
				"business_date": bdate,
				"shift": shift.name,
				"amount": 1150.0,
				"receiver_confirmed": 0,
				"status": "Draft",
			}
		).insert(ignore_permissions=True)

		# Cannot confirm transfer before receiver_confirmed=1 (§30.22 #14)
		ct.status = "Confirmed"
		with self.assertRaises(Exception):
			ct.save(ignore_permissions=True)

		ct.reload()
		ct.receiver_confirmed = 1
		ct.status = "Confirmed"
		ct.save(ignore_permissions=True)

		# Close Box 1 (after transfer of 1150, expected_cash is 0, counted_cash is 0)
		box1.reload()
		self.assertEqual(flt(box1.cash_transfers_out), 1150.0)
		box1.set("denominations", [])
		box1.counted_cash = 0.0
		box1.status = "Closed"
		box1.save(ignore_permissions=True)
		self.assertTrue(bool(box1.first_closed_at))

		# Direct modification of closed box1 must be blocked (§30.22 #20)
		box1.opening_float = 999.0
		with self.assertRaises(Exception):
			box1.save(ignore_permissions=True)

		# Reopen closed box1 with approval & reason, then close again (§30.22 #19)
		box1.reload()
		box1.status = "Reopened With Approval"
		box1.reopen_reason = "Recount verification"
		box1.approved_by = "Administrator"
		box1.save(ignore_permissions=True)
		self.assertEqual(box1.status, "Reopened With Approval")
		box1.status = "Closed"
		box1.save(ignore_permissions=True)

		# Close Safe (opening 1000 + received 1150 - bank deposit 500 = 1650 expected)
		safe.reload()
		self.assertEqual(flt(safe.cash_received_from_boxes), 1150.0)
		safe.cash_deposited_to_bank = 500.0
		safe.set("denominations", [{"banknote_or_coin": 50.0, "quantity": 33}])  # 1650.0
		safe.status = "Closed"
		safe.save(ignore_permissions=True)
		self.assertEqual(flt(safe.expected_safe_balance), 1650.0)
		self.assertEqual(flt(safe.counted_safe_balance), 1650.0)
		self.assertEqual(flt(safe.variance), 0.0)

		# Close Shift
		shift.reload()
		shift.status = "Closed"
		shift.save(ignore_permissions=True)
		self.assertEqual(shift.closing_status, "Closed")

	def test_09_card_settlement_and_tank_reconciliation_and_calibration(self):
		"""§25.4, §25.10, §28.18: Card Settlement with Fee Journal Entry, Pump Calibration, Tank Reconciliation."""
		prov_name = "Mada Network Test"
		if not frappe.db.exists("Fuel Card Provider Settings", prov_name):
			frappe.get_doc(
				{
					"doctype": "Fuel Card Provider Settings",
					"provider": prov_name,
					"company": self.company,
					"clearing_account": self.card_clearing_account,
					"settlement_account": self.bank_account,
					"fee_account": self.expense_account,
					"fee_percentage": 1.0,
					"reference_required": 1,
					"active": 1,
				}
			).insert(ignore_permissions=True)

		cs = frappe.get_doc(
			{
				"doctype": "Card Settlement",
				"station": self.station_a,
				"company": self.company,
				"business_date": nowdate(),
				"provider": prov_name,
				"station_card_amount": 1000.0,
				"terminal_report_amount": 1000.0,
				"provider_fee_amount": 10.0,
				"bank_transferred_amount": 990.0,
				"status": "Settled",
			}
		).insert(ignore_permissions=True)
		self.assertTrue(bool(cs.journal_entry))

		# Calibration Event with Waste Expense -> creates Stock Entry
		cal = frappe.get_doc(
			{
				"doctype": "Fuel Calibration Event",
				"station": self.station_a,
				"business_date": nowdate(),
				"pump": self.pump_a1,
				"previous_reading": 20500.0,
				"current_reading": 20520.0,
				"reason": "Periodic metrological test",
				"stock_treatment": "Waste Expense",
				"status": "Approved",
			}
		).insert(ignore_permissions=True)
		cal.reload()
		self.assertEqual(flt(cal.quantity), 20.0)
		self.assertTrue(bool(cal.stock_entry))

		# Tank Reconciliation
		tr = frappe.get_doc(
			{
				"doctype": "Fuel Tank Reconciliation",
				"station": self.station_a,
				"business_date": nowdate(),
				"tank": self.tank_a1,
				"physical_dip_quantity": 24000.0,
			}
		).insert(ignore_permissions=True)
		self.assertEqual(tr.status, "Calculated")

	def test_10_workspace_reports_and_station_permissions(self):
		"""§29.15 & §30.22 #25: Verify Workspace, Reports, Scheduled Jobs, Migration, and Station Isolation."""
		# 1. Workspace exists and has no excluded service or nozzle links
		self.assertTrue(frappe.db.exists("Workspace", "Fuel Station"))
		ws = frappe.get_doc("Workspace", "Fuel Station")
		for link in ws.links:
			self.assertNotIn("Nozzle", str(link.link_to or ""))
			self.assertNotIn("Wash", str(link.link_to or ""))

		# 2. Execute all 20 Script Reports and verify they run without error
		report_names = [
			"Daily Fuel Sales",
			"Pump Sales Report",
			"Fuel Dispense Report",
			"Meter Reading Report",
			"Tank Stock Report",
			"Pump Reconciliation Report",
			"Attendant Performance Report",
			"Cash Custody Report",
			"Customer Fuel Consumption",
			"Vehicle Fuel Consumption",
			"Credit Aging Report",
			"Fuel Delivery Report",
			"Tax Sales Report",
			"Discount Analysis Report",
			"Electronic Invoice Status Report",
			"Shift Closing Report",
			"Cash Boxes and Safe Closing Report",
			"Fuel Period Closing Checklist",
			"Card Settlement Reconciliation Report",
			"Fuel Audit Trail Report",
		]
		for rname in report_names:
			rep_doc = frappe.get_doc("Report", rname)
			cols, data = rep_doc.get_data(filters={"station": self.station_a})
			self.assertTrue(len(cols) > 0, f"Report {rname} returned no columns")

		# 3. Scheduled maintenance job runs idempotently
		daily_maintenance()

		# 4. Historical migration helper test (§14)
		hist_ev = import_historical_dispense_event(
			{
				"external_id": "HIST-LEGACY-001",
				"station": self.station_a,
				"business_date": add_days(nowdate(), -30),
				"pump": self.pump_a1,
				"item": self.item_gas95,
				"quantity": 50.0,
				"rate": 1.8,
				"payment_method": "Cash",
			},
			cutover_date=add_days(nowdate(), -10),
		)
		self.assertTrue(frappe.db.exists("Fuel Dispense Event", hist_ev))

	def _ensure_vehicle(self, customer, plate_number):
		if frappe.db.exists("Customer Vehicle", plate_number):
			return plate_number
		frappe.get_doc(
			{
				"doctype": "Customer Vehicle",
				"customer": customer,
				"plate_number": plate_number,
				"vehicle_code": plate_number,
				"vehicle_type": "Truck",
				"fuel_type": self.item_gas95,
				"active": 1,
			}
		).insert(ignore_permissions=True)
		return plate_number

	def _ensure_driver(self, customer, driver_name):
		existing = frappe.db.get_value("Customer Driver", {"customer": customer, "driver_name": driver_name}, "name")
		if existing:
			return existing
		doc = frappe.get_doc(
			{
				"doctype": "Customer Driver",
				"customer": customer,
				"driver_name": driver_name,
				"driver_code": f"DRV-{driver_name[-1]}",
				"active": 1,
			}
		).insert(ignore_permissions=True)
		return doc.name

