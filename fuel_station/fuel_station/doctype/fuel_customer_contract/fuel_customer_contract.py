import frappe
from frappe.model.document import Document
from frappe.utils import flt
from fuel_station.services.business_logic import check_customer_credit_and_contract


class FuelCustomerContract(Document):
	pass


@frappe.whitelist()
def get_customer_credit_summary(contract_name):
	"""Return real-time live credit evaluation for the contract."""
	contract = frappe.get_doc("Fuel Customer Contract", contract_name)
	res = check_customer_credit_and_contract(
		customer=contract.customer,
		contract=contract.name,
		requested_amount=0,
		requested_quantity=0,
	)
	return {
		"customer": contract.customer,
		"credit_limit": flt(contract.credit_limit),
		"status": res.get("status"),
		"allowed": res.get("allowed"),
		"message": res.get("message"),
		"details": res.get("details", {}),
	}


@frappe.whitelist()
def make_payment_entry(contract_name):
	"""Draft a standard ERPNext Payment Entry (Receive) for this customer."""
	contract = frappe.get_doc("Fuel Customer Contract", contract_name)
	company = contract.company or frappe.db.get_single_value("Global Defaults", "default_company")
	paid_from = frappe.db.get_value("Account", {"company": company, "account_type": "Receivable", "is_group": 0}, "name")
	paid_to = frappe.db.get_value("Account", {"company": company, "account_type": "Bank", "is_group": 0}, "name")
	pe = frappe.get_doc({
		"doctype": "Payment Entry",
		"payment_type": "Receive",
		"party_type": "Customer",
		"party": contract.customer,
		"company": company,
		"paid_from": paid_from,
		"paid_to": paid_to,
		"posting_date": frappe.utils.nowdate(),
		"paid_amount": 100.0,
		"received_amount": 100.0,
		"reference_no": f"CONT-{contract.name}",
		"reference_date": frappe.utils.nowdate(),
	})
	pe.insert(ignore_permissions=True)
	return pe.name
