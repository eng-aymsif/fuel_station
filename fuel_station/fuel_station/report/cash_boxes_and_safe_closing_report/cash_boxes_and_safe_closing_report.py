import frappe
from frappe import _
from frappe.utils import flt
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "cash_box", "label": _("الصندوق / Cash Box"), "fieldtype": "Link", "options": "Fuel Cash Box", "width": 140},
		{"fieldname": "station", "label": _("المحطة / Station"), "fieldtype": "Link", "options": "Fuel Station", "width": 130},
		{"fieldname": "shift", "label": _("الوردية / Shift"), "fieldtype": "Link", "options": "Fuel Shift", "width": 110},
		{"fieldname": "assigned_employee", "label": _("الموظف / Employee"), "fieldtype": "Link", "options": "Employee", "width": 130},
		{"fieldname": "opening_float", "label": _("الرصيد الافتتاحي"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "cash_sales", "label": _("المبيعات النقدية"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "approved_expenses", "label": _("المصروفات المعتمدة"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "cash_transfers_out", "label": _("التحويلات للخزينة"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "expected_cash", "label": _("المتوقع"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "counted_cash", "label": _("المعدود"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "variance", "label": _("الفرق"), "fieldtype": "Currency", "width": 100},
		{"fieldname": "status", "label": _("حالة الاعتماد"), "fieldtype": "Data", "width": 110},
		{"fieldname": "receiving_safe", "label": _("الخزينة المستلمة"), "fieldtype": "Link", "options": "Fuel Station Safe", "width": 130},
		{"fieldname": "bank_deposit", "label": _("الإيداع البنكي للخزينة"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "safe_variance", "label": _("الفرق النهائي للخزينة"), "fieldtype": "Currency", "width": 130},
	]
	conds = ["1=1"]
	params = {}
	allowed = get_allowed_stations_for_user()
	if allowed is not None:
		if not allowed:
			return columns, []
		conds.append("station IN %(allowed)s")
		params["allowed"] = tuple(allowed)
	for fld in ("station", "shift", "business_date", "assigned_employee"):
		if filters.get(fld):
			conds.append(f"{fld} = %({fld})s")
			params[fld] = filters[fld]

	boxes = frappe.db.sql(
		f"""
		SELECT name as cash_box, station, shift, business_date, assigned_employee,
		       opening_float, cash_sales, approved_expenses, cash_transfers_out,
		       expected_cash, counted_cash, variance, status
		FROM `tabFuel Cash Box`
		WHERE {' AND '.join(conds)}
		ORDER BY creation DESC
		""",
		params,
		as_dict=True,
	)
	for row in boxes:
		safe = frappe.get_all(
			"Fuel Station Safe",
			filters={"station": row.station},
			fields=["name", "cash_deposited_to_bank", "variance"],
			order_by="creation desc",
			limit=1,
		)
		if safe:
			row["receiving_safe"] = safe[0].name
			row["bank_deposit"] = flt(safe[0].cash_deposited_to_bank)
			row["safe_variance"] = flt(safe[0].variance)

	return columns, boxes
