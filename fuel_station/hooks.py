app_name = "fuel_station"
app_title = "Fuel Station"
app_publisher = "Ayman Saif"
app_description = "ERPNext Standard Fuel Station Management System"
app_email = "aymansaif444.ey@gmail.com"
app_license = "mit"
required_apps = ["frappe", "erpnext"]

# Assets & Desk Inclusions
# ------------------------
app_include_js = ["fuel_station.bundle.js"]
app_include_css = ["fuel_station.bundle.css"]
extend_bootinfo = "fuel_station.boot.extend_bootinfo"

doctype_js = {
	"Purchase Receipt": "public/js/purchase_receipt.js",
	"Sales Invoice": "public/js/sales_invoice.js",
	"Stock Entry": "public/js/stock_entry.js",
	"Customer": "public/js/customer.js",
	"Payment Entry": "public/js/payment_entry.js",
}

# Website & Documentation Routes
# ------------------------------
website_route_rules = [
	{"from_route": "/docs/<slug>", "to_route": "docs/page"},
]

# Jinja Printing Methods
# ----------------------
jinja = {
	"methods": [
		"fuel_station.printing.fuel_money",
		"fuel_station.printing.fuel_format_qty",
		"fuel_station.printing.fuel_qr_code",
		"fuel_station.printing.fuel_zatca_qr",
		"fuel_station.printing.fuel_station_info",
		"fuel_station.printing.fuel_bidi",
	],
}

# Installation & Migration
# ------------------------
after_install = "fuel_station.install.after_install"
before_uninstall = "fuel_station.uninstall.before_uninstall"
after_migrate = "fuel_station.setup.install.after_migrate"

override_doctype_class = {
	"Customer": "fuel_station.overrides.customer.CustomCustomer",
	"Sales Invoice": "fuel_station.overrides.sales_invoice.CustomSalesInvoice",
	"Stock Entry": "fuel_station.overrides.stock_entry.CustomStockEntry",
	"Payment Entry": "fuel_station.overrides.payment_entry.CustomPaymentEntry",
	"Purchase Receipt": "fuel_station.overrides.purchase_receipt.CustomPurchaseReceipt",
}

doc_events = {
	"Sales Invoice": {
		"validate": "fuel_station.events.validate_sales_invoice",
		"on_submit": "fuel_station.events.on_submit_sales_invoice",
		"on_cancel": "fuel_station.events.on_cancel_sales_invoice",
		"on_update_after_submit": "fuel_station.events.on_update_after_submit_sales_invoice",
	},
	"Item": {
		"on_trash": "fuel_station.events.prevent_item_deletion_with_transactions",
	},
}

permission_query_conditions = {
	"Fuel Station": "fuel_station.permissions.get_station_query_conditions",
	"Fuel Tank": "fuel_station.permissions.get_tank_query_conditions",
	"Fuel Pump": "fuel_station.permissions.get_pump_query_conditions",
	"Fuel Shift": "fuel_station.permissions.get_shift_query_conditions",
	"Fuel Pump Assignment": "fuel_station.permissions.get_assignment_query_conditions",
	"Fuel Meter Reading": "fuel_station.permissions.get_reading_query_conditions",
	"Fuel Dispense Event": "fuel_station.permissions.get_dispense_query_conditions",
	"Fuel Pump Reconciliation": "fuel_station.permissions.get_reconciliation_query_conditions",
	"Fuel Cash Box": "fuel_station.permissions.get_cash_box_query_conditions",
	"Fuel Station Safe": "fuel_station.permissions.get_safe_query_conditions",
}

has_permission = {
	"Fuel Station": "fuel_station.permissions.has_station_permission",
	"Fuel Tank": "fuel_station.permissions.has_station_permission",
	"Fuel Pump": "fuel_station.permissions.has_station_permission",
	"Fuel Shift": "fuel_station.permissions.has_station_permission",
	"Fuel Dispense Event": "fuel_station.permissions.has_station_permission",
	"Fuel Cash Box": "fuel_station.permissions.has_station_permission",
	"Fuel Station Safe": "fuel_station.permissions.has_station_permission",
}

scheduler_events = {
	"daily": [
		"fuel_station.tasks.daily_maintenance",
	],
	"hourly": [
		"fuel_station.tasks.hourly_maintenance",
	],
}
