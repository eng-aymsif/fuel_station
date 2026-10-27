import frappe
from frappe import _
from frappe.utils import flt
from fuel_station.permissions import get_allowed_stations_for_user


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "station", "label": _("المحطة / Station"), "fieldtype": "Link", "options": "Fuel Station", "width": 130},
		{"fieldname": "business_date", "label": _("التاريخ / Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "shift", "label": _("الوردية / Shift"), "fieldtype": "Link", "options": "Fuel Shift", "width": 120},
		{"fieldname": "supervisor", "label": _("المشرف / Supervisor"), "fieldtype": "Link", "options": "Employee", "width": 120},
		{"fieldname": "pump", "label": _("المضخة / Pump"), "fieldtype": "Link", "options": "Fuel Pump", "width": 110},
		{"fieldname": "opening_reading", "label": _("قراءة البداية"), "fieldtype": "Float", "width": 110},
		{"fieldname": "closing_reading", "label": _("قراءة النهاية"), "fieldtype": "Float", "width": 110},
		{"fieldname": "meter_quantity", "label": _("كمية العداد"), "fieldtype": "Float", "width": 100},
		{"fieldname": "cash_quantity", "label": _("المبيعات النقدية (لتر)"), "fieldtype": "Float", "width": 120},
		{"fieldname": "card_quantity", "label": _("مبيعات البطاقات"), "fieldtype": "Float", "width": 110},
		{"fieldname": "credit_quantity", "label": _("المبيعات الآجلة"), "fieldtype": "Float", "width": 110},
		{"fieldname": "internal_quantity", "label": _("الصرف الداخلي"), "fieldtype": "Float", "width": 100},
		{"fieldname": "coupon_quantity", "label": _("الكوبونات"), "fieldtype": "Float", "width": 95},
		{"fieldname": "calibration_quantity", "label": _("المعايرة والهدر"), "fieldtype": "Float", "width": 110},
		{"fieldname": "expected_cash", "label": _("النقد المتوقع"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "counted_cash", "label": _("النقد المعدود"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "box_variance", "label": _("فروقات الصناديق"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "transferred_to_safe", "label": _("المحول للخزينة"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "status", "label": _("الحالة"), "fieldtype": "Data", "width": 100},
	]
	conds = ["1=1"]
	params = {}
	allowed = get_allowed_stations_for_user()
	if allowed is not None:
		if not allowed:
			return columns, []
		conds.append("r.station IN %(allowed)s")
		params["allowed"] = tuple(allowed)
	for fld in ("station", "shift", "business_date", "pump"):
		if filters.get(fld):
			conds.append(f"r.{fld} = %({fld})s")
			params[fld] = filters[fld]

	recons = frappe.db.sql(
		f"""
		SELECT r.station, r.business_date, r.shift, s.supervisor, r.pump,
		       r.opening_reading, r.closing_reading, r.meter_quantity,
		       r.cash_quantity, r.card_quantity, r.credit_quantity,
		       r.internal_quantity, r.coupon_quantity,
		       (r.calibration_quantity + r.waste_quantity) as calibration_quantity,
		       r.status
		FROM `tabFuel Pump Reconciliation` r
		LEFT JOIN `tabFuel Shift` s ON s.name = r.shift
		WHERE {' AND '.join(conds)}
		ORDER BY r.business_date DESC, r.station, r.pump
		""",
		params,
		as_dict=True,
	)
	for row in recons:
		box_filters = {"station": row.station}
		if row.shift:
			box_filters["shift"] = row.shift
		else:
			box_filters["business_date"] = row.business_date
		boxes = frappe.get_all("Fuel Cash Box", filters=box_filters, fields=["expected_cash", "counted_cash", "variance", "cash_transfers_out"])
		row["expected_cash"] = sum(flt(b.expected_cash) for b in boxes)
		row["counted_cash"] = sum(flt(b.counted_cash) for b in boxes)
		row["box_variance"] = sum(flt(b.variance) for b in boxes)
		row["transferred_to_safe"] = sum(flt(b.cash_transfers_out) for b in boxes)

	return columns, recons
