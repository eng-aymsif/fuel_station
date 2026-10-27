"""تهيئة محطة الوقود لكل شركة: الحسابات، العميل النقدي، والمحطة الافتراضية (نفس نمط mueen)."""

import frappe
from frappe import _

CASH_CUSTOMER = "Fuel Cash Customer"
POS_PROFILE_PREFIX = "Fuel POS"

# حقل الإعدادات: (اسم الحساب، النوع الجذري، نوع الحساب، الحساب الافتراضي للشركة لتحديد الأب)
ACCOUNTS = {
	"default_income_account": ("Fuel Sales Revenue", "Income", "", "default_income_account"),
	"default_expense_account": ("Cost of Fuel Sold", "Expense", "Cost of Goods Sold", "default_expense_account"),
	"default_waste_account": ("Fuel Calibration and Waste Expense", "Expense", "", "default_expense_account"),
	"default_variance_account": ("Fuel Stock Variance Expense", "Expense", "Stock Adjustment", "stock_adjustment_account"),
	"default_card_clearing_account": ("POS Card Clearing Account", "Asset", "Bank", "default_bank_account"),
}


def setup_company(company: str):
	"""إنشاء وضبط حسابات المحطة والعميل النقدي ومحطة وقود افتراضية للشركة."""
	company_doc = frappe.get_cached_doc("Company", company)
	accounts = {fieldname: ensure_account(company_doc, *spec) for fieldname, spec in ACCOUNTS.items()}

	cash_customer = ensure_cash_customer(company_doc)

	# إنشاء محطة وقود افتراضية للشركة وربط الحسابات بها إن لم تكن موجودة
	station_name = f"Main Station - {company_doc.abbr}"
	if not frappe.db.exists("Fuel Station", station_name):
		station = frappe.get_doc(
			{
				"doctype": "Fuel Station",
				"station_name": station_name,
				"station_code": f"ST-{company_doc.abbr}",
				"company": company_doc.name,
				"default_cost_center": company_doc.cost_center,
				"default_cash_customer": cash_customer,
				"default_cash_account": company_doc.default_cash_account or get_cash_account(company_doc.name),
				"default_card_clearing_account": accounts.get("default_card_clearing_account"),
				"default_income_account": accounts.get("default_income_account"),
				"default_expense_account": accounts.get("default_expense_account"),
				"default_waste_account": accounts.get("default_waste_account"),
				"default_variance_account": accounts.get("default_variance_account"),
				"active": 1,
			}
		)
		station.insert(ignore_permissions=True)


def ensure_account(company_doc, account_name, root_type, account_type, default_field):
	existing = frappe.db.get_value(
		"Account", {"company": company_doc.name, "account_name": account_name, "is_group": 0}, "name"
	)
	if existing:
		return existing

	parent = get_parent_account(company_doc, root_type, default_field)
	account = frappe.get_doc(
		{
			"doctype": "Account",
			"company": company_doc.name,
			"account_name": account_name,
			"parent_account": parent,
			"account_type": account_type or None,
			"account_currency": company_doc.default_currency,
		}
	)
	account.insert(ignore_permissions=True)
	return account.name


def get_parent_account(company_doc, root_type, default_field):
	default_account = company_doc.get(default_field)
	if default_account:
		parent = frappe.db.get_value("Account", default_account, "parent_account")
		if parent:
			return parent

	parent = frappe.db.get_value(
		"Account",
		{"company": company_doc.name, "root_type": root_type, "is_group": 1},
		"name",
		order_by="lft desc",
	)
	if not parent:
		parent = frappe.db.get_value(
			"Account",
			{"company": company_doc.name, "is_group": 1},
			"name",
			order_by="lft asc",
		)
	return parent


def ensure_cash_customer(company_doc):
	existing = frappe.db.get_value("Customer", {"customer_name": CASH_CUSTOMER}, "name")
	if existing:
		return existing

	cg = (
		"Cash Customers"
		if frappe.db.exists("Customer Group", "Cash Customers")
		else frappe.db.get_single_value("Selling Settings", "customer_group")
		or frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
		or "All Customer Groups"
	)
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": CASH_CUSTOMER,
			"customer_type": "Individual",
			"customer_group": cg,
			"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories",
			"fuel_customer_type": "Cash",
		}
	)
	customer.insert(ignore_permissions=True)
	return customer.name


def get_cash_account(company):
	return frappe.db.get_value(
		"Account",
		{"company": company, "account_type": "Cash", "is_group": 0},
		"name",
	)

