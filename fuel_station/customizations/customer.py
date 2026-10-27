from typing import ClassVar
from fuel_station.setup import BaseDoctypeCustomization


class CustomerCustomization(BaseDoctypeCustomization):
	doctype = "Customer"

	custom_fields: ClassVar[list] = [
		{"fieldname": "fuel_customer_type", "label": "Fuel Customer Type", "fieldtype": "Select", "options": "\nCash\nCredit\nGovernment\nTransport\nEmployee\nContract", "insert_after": "customer_group"},
		{"fieldname": "contract_number", "label": "Contract Number", "fieldtype": "Data", "insert_after": "fuel_customer_type"},
		{"fieldname": "contract_start_date", "label": "Contract Start Date", "fieldtype": "Date", "insert_after": "contract_number"},
		{"fieldname": "contract_end_date", "label": "Contract End Date", "fieldtype": "Date", "insert_after": "contract_start_date"},
		{"fieldname": "purchase_order_required", "label": "Purchase Order Required", "fieldtype": "Check", "insert_after": "contract_end_date"},
		{"fieldname": "vehicle_required", "label": "Vehicle Required", "fieldtype": "Check", "insert_after": "purchase_order_required"},
		{"fieldname": "driver_required", "label": "Driver Required", "fieldtype": "Check", "insert_after": "vehicle_required"},
		{"fieldname": "credit_policy", "label": "Credit Policy", "fieldtype": "Select", "options": "BLOCK\nWARN_AND_ALLOW\nREQUIRE_SUPERVISOR_APPROVAL\nREQUIRE_FINANCE_APPROVAL\nALLOW_WITH_REASON\nCredit Not Allowed", "default": "BLOCK", "insert_after": "driver_required"},
		{"fieldname": "credit_control_policy", "label": "Credit Control Policy", "fieldtype": "Select", "options": "BLOCK\nWARN_AND_ALLOW\nREQUIRE_SUPERVISOR_APPROVAL\nREQUIRE_FINANCE_APPROVAL\nALLOW_WITH_REASON\nCredit Not Allowed", "default": "BLOCK", "insert_after": "credit_policy"},
		{"fieldname": "credit_days", "label": "Credit Days", "fieldtype": "Int", "insert_after": "credit_control_policy"},
		{"fieldname": "preferred_payment_method", "label": "Preferred Payment Method", "fieldtype": "Select", "options": "\nCash\nCard\nCredit\nPrepaid", "insert_after": "credit_days"},
		{"fieldname": "station_scope", "label": "Station Scope", "fieldtype": "Link", "options": "Fuel Station", "insert_after": "preferred_payment_method"},
		{"fieldname": "daily_fuel_limit", "label": "Daily Fuel Limit", "fieldtype": "Float", "insert_after": "station_scope"},
		{"fieldname": "monthly_fuel_limit", "label": "Monthly Fuel Limit", "fieldtype": "Float", "insert_after": "daily_fuel_limit"},
		{"fieldname": "active_fuel_customer", "label": "Active Fuel Customer", "fieldtype": "Check", "default": "1", "insert_after": "monthly_fuel_limit"},
	]


CUSTOMIZATIONS = [CustomerCustomization()]


def apply_customizations():
	# bench execute fuel_station.customizations.customer.apply_customizations
	CustomerCustomization().uninstall()
	CustomerCustomization().install()
	print("Customizations have been applied to the Customer doctype.")

