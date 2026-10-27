from frappe import _


def get_data():
	return {
		"fieldname": "contract",
		"non_standard_fieldnames": {
			"Sales Invoice": "contract_number",
		},
		"transactions": [
			{
				"label": _("Fleet Activity"),
				"items": ["Fuel Dispense Event", "Sales Invoice"],
			},
		],
	}
