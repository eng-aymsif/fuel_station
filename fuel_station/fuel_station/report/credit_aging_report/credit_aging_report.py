import frappe
from frappe import _
from frappe.utils import flt
from fuel_station.services.business_logic import check_customer_credit_and_contract


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 160},
		{"fieldname": "credit_limit", "label": _("Credit Limit"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "current_outstanding", "label": _("Outstanding (AR)"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "overdue_outstanding", "label": _("Overdue Balance"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "pending_draft_amount", "label": _("Pending Commitments"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "available_credit", "label": _("Available Credit"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "status", "label": _("Credit Status"), "fieldtype": "Data", "width": 140},
	]
	c_filters = {"disabled": 0}
	if filters.get("customer"):
		c_filters["name"] = filters["customer"]
	customers = frappe.get_all("Customer", filters=c_filters, pluck="name")
	data = []
	for cust in customers:
		res = check_customer_credit_and_contract(cust, requested_amount=0, company=filters.get("company"), validate_requirements=False)
		if flt(res.get("credit_limit")) > 0 or flt(res.get("current_outstanding")) > 0 or filters.get("customer"):
			data.append({
				"customer": cust,
				"credit_limit": flt(res.get("credit_limit")),
				"current_outstanding": flt(res.get("current_outstanding")),
				"overdue_outstanding": flt(res.get("overdue_outstanding")),
				"pending_draft_amount": flt(res.get("pending_draft_amount")),
				"available_credit": flt(res.get("available_credit")),
				"status": res.get("status"),
			})
	return columns, data
