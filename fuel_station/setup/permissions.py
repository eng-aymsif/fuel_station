"""صلاحيات أدوار محطة الوقود على DocTypes القياسية (Custom DocPerm عبر آلية Role Permission Manager - نمط mueen)."""

import frappe
from frappe.permissions import add_permission, update_permission_property

READ = ("read", "select")
VIEW = ("read", "select", "report", "print", "email")
EDIT = ("read", "select", "write", "create", "report", "print", "email")

COMMON = {
	"Fuel Station": READ,
	"Fuel Tank": READ,
	"Fuel Pump": READ,
	"Fuel Shift Type": READ,
	"Customer": READ,
	"Customer Group": READ,
	"Supplier": READ,
	"Supplier Group": READ,
	"Item": READ,
	"Item Group": READ,
	"UOM": READ,
	"Warehouse": READ,
	"Account": ("select",),
	"Cost Center": ("select",),
	"Company": READ,
	"Currency": READ,
	"Mode of Payment": READ,
	"Sales Invoice": VIEW,
	"Payment Entry": VIEW,
}

ROLE_PERMISSIONS = {
	"Fuel Attendant": {
		**COMMON,
		"Fuel Shift": READ,
		"Fuel Pump Assignment": READ,
		"Fuel Meter Reading": ("read", "select", "create", "write"),
		"Fuel Dispense Event": ("read", "select", "create", "write"),
		"Fuel Cash Box": ("read", "select", "write"),
		"Pump Handover": ("read", "select", "create", "write"),
	},
	"Shift Supervisor": {
		**COMMON,
		"Customer": EDIT,
		"Fuel Shift": EDIT,
		"Fuel Pump Assignment": EDIT,
		"Fuel Meter Reading": EDIT,
		"Fuel Dispense Event": EDIT,
		"Fuel Pump Reconciliation": EDIT,
		"Fuel Cash Box": EDIT,
		"Fuel Station Safe": EDIT,
		"Cash Transfer": EDIT,
		"Pump Handover": EDIT,
		"Fuel Authorization": EDIT,
		"Fuel Issue Order": EDIT,
		"Fuel Reconciliation Exception": EDIT,
		"Fuel Delivery": EDIT,
		"Customer Vehicle": EDIT,
		"Customer Driver": EDIT,
	},
	"Cashier": {
		**COMMON,
		"Fuel Dispense Event": EDIT,
		"Fuel Cash Box": EDIT,
		"Fuel Station Safe": EDIT,
		"Cash Transfer": EDIT,
		"Card Settlement": EDIT,
		"Fuel Pump Invoice Batch": EDIT,
		"Payment Entry": EDIT,
	},
	"Accountant": {
		**COMMON,
		"Fuel Shift": VIEW,
		"Fuel Pump Reconciliation": EDIT,
		"Fuel Pump Invoice Batch": EDIT,
		"Card Settlement": EDIT,
		"Fuel Station Safe": EDIT,
		"Cash Transfer": EDIT,
		"Sales Invoice": EDIT,
		"Purchase Receipt": VIEW,
		"Payment Entry": EDIT,
		"Journal Entry": EDIT,
		"Fuel Customer Contract": EDIT,
	},
	"Inventory Officer": {
		**COMMON,
		"Fuel Tank": EDIT,
		"Fuel Delivery": EDIT,
		"Fuel Tank Reconciliation": EDIT,
		"Fuel Calibration Event": EDIT,
		"Stock Entry": EDIT,
		"Purchase Receipt": EDIT,
		"Warehouse": EDIT,
		"Item": EDIT,
	},
	"Station Manager": {
		**COMMON,
		"Fuel Station": EDIT,
		"Fuel Tank": EDIT,
		"Fuel Pump": EDIT,
		"Fuel Shift": EDIT,
		"Fuel Pump Assignment": EDIT,
		"Fuel Meter Reading": EDIT,
		"Fuel Dispense Event": EDIT,
		"Fuel Pump Reconciliation": EDIT,
		"Fuel Reconciliation Exception": EDIT,
		"Fuel Pump Invoice Batch": EDIT,
		"Fuel Cash Box": EDIT,
		"Fuel Station Safe": EDIT,
		"Cash Transfer": EDIT,
		"Pump Handover": EDIT,
		"Fuel Delivery": EDIT,
		"Fuel Tank Reconciliation": EDIT,
		"Fuel Calibration Event": EDIT,
		"Fuel Authorization": EDIT,
		"Fuel Issue Order": EDIT,
		"Fuel Customer Contract": EDIT,
	},
	"Fuel Operations Manager": {
		**COMMON,
		"Fuel Station": EDIT,
		"Fuel Tank": EDIT,
		"Fuel Pump": EDIT,
		"Fuel Shift": EDIT,
		"Fuel Pump Assignment": EDIT,
		"Fuel Meter Reading": EDIT,
		"Fuel Dispense Event": EDIT,
		"Fuel Pump Reconciliation": EDIT,
		"Fuel Reconciliation Exception": EDIT,
		"Fuel Pump Invoice Batch": EDIT,
		"Fuel Cash Box": EDIT,
		"Fuel Station Safe": EDIT,
		"Cash Transfer": EDIT,
		"Pump Handover": EDIT,
		"Fuel Delivery": EDIT,
		"Fuel Tank Reconciliation": EDIT,
		"Fuel Calibration Event": EDIT,
		"Fuel Authorization": EDIT,
		"Fuel Issue Order": EDIT,
		"Fuel Customer Contract": EDIT,
		"Fuel Card": EDIT,
		"Fuel Operations Settings": EDIT,
		"Fuel Tax Policy": EDIT,
	},
}


def apply_role_permissions():
	for role, doctypes in ROLE_PERMISSIONS.items():
		if not frappe.db.exists("Role", role):
			continue
		for doctype, ptypes in doctypes.items():
			ensure_permissions(doctype, role, ptypes)


def ensure_permissions(doctype: str, role: str, ptypes):
	if not frappe.db.exists("DocType", doctype):
		return

	existing = frappe.db.get_value(
		"Custom DocPerm",
		{"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0},
		ptypes,
		as_dict=True,
	)
	if not existing:
		add_permission(doctype, role, 0, ptype=ptypes[0])
		existing = {}

	changed = False
	for ptype in ptypes:
		if not existing.get(ptype):
			update_permission_property(doctype, role, 0, ptype, 1, validate=False)
			changed = True
	if changed or not existing:
		frappe.clear_cache(doctype=doctype)
