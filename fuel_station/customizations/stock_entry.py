from typing import ClassVar
from fuel_station.setup import BaseDoctypeCustomization


class StockEntryCustomization(BaseDoctypeCustomization):
	doctype = "Stock Entry"

	custom_fields: ClassVar[list] = [
		{"fieldname": "fuel_station", "label": "Fuel Station", "fieldtype": "Link", "options": "Fuel Station", "insert_after": "company"},
		{"fieldname": "fuel_issue_order", "label": "Fuel Issue Order", "fieldtype": "Link", "options": "Fuel Issue Order", "insert_after": "fuel_station"},
		{"fieldname": "fuel_calibration_event", "label": "Fuel Calibration Event", "fieldtype": "Link", "options": "Fuel Calibration Event", "insert_after": "fuel_issue_order"},
		{"fieldname": "fuel_dispense_event", "label": "Fuel Dispense Event", "fieldtype": "Link", "options": "Fuel Dispense Event", "insert_after": "fuel_calibration_event"},
		{"fieldname": "vehicle", "label": "Vehicle", "fieldtype": "Link", "options": "Customer Vehicle", "insert_after": "fuel_dispense_event"},
		{"fieldname": "employee", "label": "Employee", "fieldtype": "Link", "options": "Employee", "insert_after": "vehicle"},
		{"fieldname": "department", "label": "Department", "fieldtype": "Link", "options": "Department", "insert_after": "employee"},
		{"fieldname": "source_key", "label": "Fuel Source Key", "fieldtype": "Data", "read_only": 1, "insert_after": "department"},
	]


CUSTOMIZATIONS = [StockEntryCustomization()]


def apply_customizations():
	# bench execute fuel_station.customizations.stock_entry.apply_customizations
	StockEntryCustomization().uninstall()
	StockEntryCustomization().install()
	print("Customizations have been applied to the Stock Entry doctype.")

