from typing import ClassVar
from fuel_station.setup import BaseDoctypeCustomization


class SalesInvoiceCustomization(BaseDoctypeCustomization):
	doctype = "Sales Invoice"

	custom_fields: ClassVar[list] = [
		{"fieldname": "fuel_station", "label": "Fuel Station", "fieldtype": "Link", "options": "Fuel Station", "insert_after": "company"},
		{"fieldname": "branch", "label": "Branch", "fieldtype": "Data", "insert_after": "fuel_station"},
		{"fieldname": "business_date", "label": "Business Date", "fieldtype": "Date", "insert_after": "posting_date"},
		{"fieldname": "fuel_shift", "label": "Fuel Shift", "fieldtype": "Link", "options": "Fuel Shift", "insert_after": "business_date"},
		{"fieldname": "fuel_invoice_type", "label": "Fuel Invoice Type", "fieldtype": "Data", "insert_after": "fuel_shift"},
		{"fieldname": "contract_number", "label": "Contract Number", "fieldtype": "Link", "options": "Fuel Customer Contract", "insert_after": "fuel_invoice_type"},
		{"fieldname": "customer_purchase_order", "label": "Customer Purchase Order", "fieldtype": "Data", "insert_after": "contract_number"},
		{"fieldname": "fuel_issue_order", "label": "Fuel Issue Order", "fieldtype": "Link", "options": "Fuel Issue Order", "insert_after": "customer_purchase_order"},
		{"fieldname": "authorization_number", "label": "Fuel Authorization", "fieldtype": "Link", "options": "Fuel Authorization", "insert_after": "fuel_issue_order"},
		{"fieldname": "payment_method_type", "label": "Payment Method Type", "fieldtype": "Data", "insert_after": "authorization_number"},
		{"fieldname": "payment_reference", "label": "Payment Reference", "fieldtype": "Data", "insert_after": "payment_method_type"},
		{"fieldname": "card_provider", "label": "Card Provider", "fieldtype": "Data", "insert_after": "payment_reference"},
		{"fieldname": "card_last_four_only_if_allowed", "label": "Card Last Four Digits", "fieldtype": "Data", "insert_after": "card_provider"},
		{"fieldname": "source_key", "label": "Fuel Source Key", "fieldtype": "Data", "read_only": 1, "insert_after": "card_last_four_only_if_allowed"},
		{"fieldname": "e_invoice_uuid", "label": "E-Invoice UUID", "fieldtype": "Data", "read_only": 1, "insert_after": "source_key"},
		{"fieldname": "e_invoice_status", "label": "E-Invoice Status", "fieldtype": "Select", "options": "\nPending\nAccepted\nRejected", "read_only": 1, "insert_after": "e_invoice_uuid"},
		{"fieldname": "e_invoice_qr", "label": "E-Invoice QR Payload", "fieldtype": "Small Text", "read_only": 1, "insert_after": "e_invoice_status"},
		{"fieldname": "e_invoice_submitted_at", "label": "E-Invoice Submitted At", "fieldtype": "Datetime", "read_only": 1, "insert_after": "e_invoice_qr"},
		{"fieldname": "e_invoice_response", "label": "E-Invoice Response", "fieldtype": "Small Text", "read_only": 1, "insert_after": "e_invoice_submitted_at"},
	]


class SalesInvoiceItemCustomization(BaseDoctypeCustomization):
	doctype = "Sales Invoice Item"

	custom_fields: ClassVar[list] = [
		{"fieldname": "fuel_station", "label": "Fuel Station", "fieldtype": "Link", "options": "Fuel Station", "insert_after": "item_code"},
		{"fieldname": "pump", "label": "Pump", "fieldtype": "Link", "options": "Fuel Pump", "insert_after": "fuel_station"},
		{"fieldname": "fuel_tank", "label": "Fuel Tank", "fieldtype": "Link", "options": "Fuel Tank", "insert_after": "pump"},
		{"fieldname": "fuel_dispense_event", "label": "Fuel Dispense Event", "fieldtype": "Link", "options": "Fuel Dispense Event", "insert_after": "fuel_tank"},
		{"fieldname": "opening_meter_reading", "label": "Opening Meter Reading", "fieldtype": "Float", "insert_after": "fuel_dispense_event"},
		{"fieldname": "closing_meter_reading", "label": "Closing Meter Reading", "fieldtype": "Float", "insert_after": "opening_meter_reading"},
		{"fieldname": "meter_quantity", "label": "Meter Quantity", "fieldtype": "Float", "insert_after": "closing_meter_reading"},
		{"fieldname": "vehicle", "label": "Vehicle", "fieldtype": "Link", "options": "Customer Vehicle", "insert_after": "meter_quantity"},
		{"fieldname": "vehicle_plate_number", "label": "Vehicle Plate Number", "fieldtype": "Data", "insert_after": "vehicle"},
		{"fieldname": "driver", "label": "Driver", "fieldtype": "Link", "options": "Customer Driver", "insert_after": "vehicle_plate_number"},
		{"fieldname": "driver_reference", "label": "Driver Reference", "fieldtype": "Data", "insert_after": "driver"},
		{"fieldname": "vehicle_odometer_reading", "label": "Vehicle Odometer Reading", "fieldtype": "Float", "insert_after": "driver_reference"},
		{"fieldname": "attendant", "label": "Attendant", "fieldtype": "Link", "options": "Employee", "insert_after": "vehicle_odometer_reading"},
		{"fieldname": "shift", "label": "Shift", "fieldtype": "Link", "options": "Fuel Shift", "insert_after": "attendant"},
		{"fieldname": "issue_order", "label": "Fuel Issue Order", "fieldtype": "Link", "options": "Fuel Issue Order", "insert_after": "shift"},
		{"fieldname": "authorization", "label": "Fuel Authorization", "fieldtype": "Link", "options": "Fuel Authorization", "insert_after": "issue_order"},
		{"fieldname": "rate_before_discount", "label": "Rate Before Discount", "fieldtype": "Currency", "insert_after": "rate"},
		{"fieldname": "rate_after_discount", "label": "Rate After Discount", "fieldtype": "Currency", "insert_after": "rate_before_discount"},
		{"fieldname": "amount_before_discount", "label": "Amount Before Discount", "fieldtype": "Currency", "insert_after": "amount"},
		{"fieldname": "amount_after_discount", "label": "Amount After Discount", "fieldtype": "Currency", "insert_after": "amount_before_discount"},
		{"fieldname": "discount_source", "label": "Discount Source", "fieldtype": "Data", "insert_after": "amount_after_discount"},
	]


CUSTOMIZATIONS = [SalesInvoiceCustomization(), SalesInvoiceItemCustomization()]


def apply_customizations():
	# bench execute fuel_station.customizations.sales_invoice.apply_customizations
	for c in CUSTOMIZATIONS:
		c.uninstall()
		c.install()
	print("Customizations have been applied to the Sales Invoice doctype.")

