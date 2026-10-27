from typing import ClassVar
from fuel_station.setup import BaseDoctypeCustomization


class ItemCustomization(BaseDoctypeCustomization):
	doctype = "Item"

	custom_fields: ClassVar[list] = [
		{"fieldname": "is_fuel_item", "label": "Is Fuel Item", "fieldtype": "Check", "default": "0", "insert_after": "item_group"},
		{"fieldname": "fuel_grade", "label": "Fuel Grade", "fieldtype": "Data", "insert_after": "is_fuel_item"},
		{"fieldname": "density_if_required", "label": "Standard Density", "fieldtype": "Float", "insert_after": "fuel_grade"},
		{"fieldname": "meter_uom", "label": "Meter UOM", "fieldtype": "Link", "options": "UOM", "default": "Liter", "insert_after": "density_if_required"},
		{"fieldname": "allow_meter_sale", "label": "Allow Meter Sale", "fieldtype": "Check", "default": "1", "insert_after": "meter_uom"},
	]


CUSTOMIZATIONS = [ItemCustomization()]


def apply_customizations():
	# bench execute fuel_station.customizations.item.apply_customizations
	ItemCustomization().uninstall()
	ItemCustomization().install()
	print("Customizations have been applied to the Item doctype.")

