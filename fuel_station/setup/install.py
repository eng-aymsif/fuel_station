"""تهيئة بيانات تطبيق محطة الوقود الأساسية (الأدوار، الأبعاد المحاسبية، المجموعات، الأصناف القياسية).

يطابق بدقة بنية وأسلوب تطبيق mueen في mueen/setup/install.py
كل الدوال قابلة للتكرار دون أثر جانبي. تخصيصات DocTypes القياسية موجودة في fuel_station/customizations.
"""

import frappe
from fuel_station.setup.permissions import apply_role_permissions

ROLES = (
	"Fuel Attendant",
	"Shift Supervisor",
	"Cashier",
	"Accountant",
	"Inventory Officer",
	"Station Manager",
	"Fuel Operations Manager",
)

ACCOUNTING_DIMENSIONS = (
	# (العنوان، نوع المستند)
	("Fuel Station", "Fuel Station"),
	("Fuel Shift", "Fuel Shift"),
)

ITEM_GROUPS = {
	"Fuel": (
		"Gasoline",
		"Diesel",
		"Kerosene",
		"Fuel Gas",
	),
	"Station Operational Supplies": (
		"Oils and Lubricants",
		"Filters and Consumables",
		"Fuel Cards and Coupons",
	),
}

SUPPLIER_GROUPS = {
	"Fuel and Station Suppliers": (
		"Fuel Distribution Companies",
		"Oil and Derivative Companies",
		"Pump and Tank Maintenance Companies",
		"POS and System Vendors",
	),
}

CUSTOMER_GROUPS = (
	"Cash Customers",
	"Credit Fleet Customers",
	"Government Entities",
	"Transport Companies",
	"Station Employees",
)

# (رمز الصنف، اسم الصنف، مجموعة الصنف، درجة الوقود، سعر افتراضي)
DEFAULT_FUEL_ITEMS = (
	("FUEL-GAS-91", "Gasoline 91", "Gasoline", "91", 2.18),
	("FUEL-GAS-95", "Gasoline 95", "Gasoline", "95", 2.33),
	("FUEL-DIESEL", "Diesel Fuel", "Diesel", "DIESEL", 1.15),
)


def after_migrate():
	create_roles()
	create_accounting_dimensions()
	apply_role_permissions()
	apply_settings_defaults()


def setup_all():
	create_roles()
	create_accounting_dimensions()
	apply_role_permissions()
	create_masters()
	apply_settings_defaults()


def apply_settings_defaults():
	"""حفظ القيم الافتراضية للحقول غير المحفوظة في Fuel Operations Settings (نفس نمط mueen)."""
	if not frappe.db.exists("DocType", "Fuel Operations Settings"):
		return
	meta = frappe.get_meta("Fuel Operations Settings")
	singles = frappe.qb.Table("tabSingles")
	saved = set(
		frappe.qb.from_(singles)
		.select(singles.field)
		.where(singles.doctype == "Fuel Operations Settings")
		.run(pluck=True)
	)
	for df in meta.fields:
		if df.default is not None and df.fieldname not in saved and not df.is_virtual:
			frappe.db.set_single_value("Fuel Operations Settings", df.fieldname, df.default)
	frappe.clear_document_cache("Fuel Operations Settings", "Fuel Operations Settings")


def create_roles():
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def create_accounting_dimensions():
	for label, document_type in ACCOUNTING_DIMENSIONS:
		if not frappe.db.exists("DocType", document_type):
			continue
		if frappe.db.exists("Accounting Dimension", {"document_type": document_type}):
			continue
		in_test = frappe.flags.in_test
		frappe.flags.in_test = True
		try:
			frappe.get_doc(
				{"doctype": "Accounting Dimension", "label": label, "document_type": document_type}
			).insert(ignore_permissions=True)
		except Exception:
			pass
		finally:
			frappe.flags.in_test = in_test


def get_tree_root(doctype: str, parent_field: str) -> str:
	root = frappe.db.get_value(doctype, {parent_field: ("in", ("", None)), "is_group": 1}, "name")
	if not root:
		root = frappe.db.get_value(doctype, {"is_group": 1}, "name")
	return root


def ensure_tree_node(doctype: str, parent_field: str, name: str, parent: str = None, is_group: int = 0):
	if not parent:
		parent = get_tree_root(doctype, parent_field)
	name_field = frappe.scrub(doctype) + "_name"
	if frappe.db.exists(doctype, name):
		return
	frappe.get_doc({"doctype": doctype, name_field: name, parent_field: parent, "is_group": is_group}).insert(
		ignore_permissions=True
	)


def create_masters():
	# 1. UOMs
	for uom in ("Liter", "Cubic Meter", "Gallon"):
		if not frappe.db.exists("UOM", uom):
			frappe.get_doc({"doctype": "UOM", "uom_name": uom, "must_be_whole_number": 0}).insert(
				ignore_permissions=True
			)

	# 2. Item Groups (شجري)
	root_ig = get_tree_root("Item Group", "parent_item_group") or "All Item Groups"
	for group, children in ITEM_GROUPS.items():
		ensure_tree_node("Item Group", "parent_item_group", group, root_ig, is_group=1)
		for child in children:
			ensure_tree_node("Item Group", "parent_item_group", child, group)

	# 3. Supplier Groups (شجري)
	root_sg = get_tree_root("Supplier Group", "parent_supplier_group") or "All Supplier Groups"
	for group, children in SUPPLIER_GROUPS.items():
		ensure_tree_node("Supplier Group", "parent_supplier_group", group, root_sg, is_group=1)
		for child in children:
			ensure_tree_node("Supplier Group", "parent_supplier_group", child, group)

	# 4. Customer Groups
	root_cg = get_tree_root("Customer Group", "parent_customer_group") or "All Customer Groups"
	for group in CUSTOMER_GROUPS:
		ensure_tree_node("Customer Group", "parent_customer_group", group, root_cg)

	# 5. أصناف الوقود القياسية
	uom = get_default_uom()
	for item_code, item_name, item_group, fuel_grade, standard_rate in DEFAULT_FUEL_ITEMS:
		if frappe.db.exists("Item", item_code):
			continue
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_name,
				"item_group": item_group if frappe.db.exists("Item Group", item_group) else root_ig,
				"stock_uom": uom,
				"is_stock_item": 1,
				"is_sales_item": 1,
				"is_purchase_item": 1,
				"is_fuel_item": 1,
				"fuel_grade": fuel_grade,
				"meter_uom": uom,
				"allow_meter_sale": 1,
				"standard_rate": standard_rate,
			}
		).insert(ignore_permissions=True)


def get_default_uom() -> str:
	for uom in (frappe.db.get_single_value("Stock Settings", "stock_uom"), "Liter", "Nos", "Unit"):
		if uom and frappe.db.exists("UOM", uom):
			return uom
	return frappe.db.get_value("UOM", {"must_be_whole_number": 0}, "name") or "Liter"
