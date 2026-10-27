from typing import ClassVar
from fuel_station.setup import BaseDoctypeCustomization


class PurchaseReceiptCustomization(BaseDoctypeCustomization):
	doctype = "Purchase Receipt"

	custom_fields: ClassVar[list] = [
		{"fieldname": "fuel_station", "label": "Fuel Station", "fieldtype": "Link", "options": "Fuel Station", "insert_after": "company"},
		{"fieldname": "fuel_delivery", "label": "Fuel Delivery", "fieldtype": "Link", "options": "Fuel Delivery", "insert_after": "fuel_station"},
		{"fieldname": "source_key", "label": "Fuel Source Key", "fieldtype": "Data", "read_only": 1, "insert_after": "fuel_delivery"},
	]


CUSTOMIZATIONS = [PurchaseReceiptCustomization()]


def apply_customizations():
	# bench execute fuel_station.customizations.purchase_receipt.apply_customizations
	PurchaseReceiptCustomization().uninstall()
	PurchaseReceiptCustomization().install()
	print("Customizations have been applied to the Purchase Receipt doctype.")

