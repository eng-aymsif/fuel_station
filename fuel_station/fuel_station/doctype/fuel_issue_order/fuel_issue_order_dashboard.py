from frappe import _


def get_data():
	return {
		"fieldname": "issue_order",
		"non_standard_fieldnames": {
			"Stock Entry": "fuel_issue_order",
		},
		"transactions": [
			{
				"label": _("Fulfillment & Material Issues"),
				"items": ["Fuel Dispense Event", "Stock Entry"],
			},
		],
	}
