from typing import ClassVar
from fuel_station.setup import BaseDoctypeCustomization


class PaymentEntryCustomization(BaseDoctypeCustomization):
	doctype = "Payment Entry"

	custom_fields: ClassVar[list] = [
		{"fieldname": "fuel_station", "label": "Fuel Station", "fieldtype": "Link", "options": "Fuel Station", "insert_after": "company"},
		{"fieldname": "fuel_shift", "label": "Fuel Shift", "fieldtype": "Link", "options": "Fuel Shift", "insert_after": "fuel_station"},
		{"fieldname": "fuel_cash_box", "label": "Fuel Cash Box", "fieldtype": "Link", "options": "Fuel Cash Box", "insert_after": "fuel_shift"},
		{"fieldname": "card_provider", "label": "Card Provider", "fieldtype": "Data", "insert_after": "fuel_cash_box"},
		{"fieldname": "source_key", "label": "Fuel Source Key", "fieldtype": "Data", "read_only": 1, "insert_after": "card_provider"},
	]


CUSTOMIZATIONS = [PaymentEntryCustomization()]


def apply_customizations():
	# bench execute fuel_station.customizations.payment_entry.apply_customizations
	PaymentEntryCustomization().uninstall()
	PaymentEntryCustomization().install()
	print("Customizations have been applied to the Payment Entry doctype.")

