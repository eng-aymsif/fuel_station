from frappe import _


def get_data():
	return {
		"fieldname": "from_cash_box",
		"non_standard_fieldnames": {
			"Fuel Pump Assignment": "cash_box",
			"Fuel Cash Custody": "cash_box",
			"Payment Entry": "fuel_cash_box",
		},
		"transactions": [
			{
				"label": _("Treasury Transfers"),
				"items": ["Cash Transfer"],
			},
			{
				"label": _("Assignments & Custody"),
				"items": ["Fuel Pump Assignment", "Fuel Cash Custody"],
			},
			{
				"label": _("Payments"),
				"items": ["Payment Entry"],
			},
		],
	}
