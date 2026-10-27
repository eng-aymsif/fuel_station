from frappe import _


def get_data():
	return {
		"fieldname": "shift",
		"non_standard_fieldnames": {
			"Sales Invoice": "fuel_shift",
		},
		"transactions": [
			{
				"label": _("Forecourt Operations"),
				"items": ["Fuel Pump Assignment", "Fuel Dispense Event", "Fuel Pump Reconciliation"],
			},
			{
				"label": _("Cash & Treasury"),
				"items": ["Fuel Cash Box", "Fuel Station Safe"],
			},
			{
				"label": _("Billing"),
				"items": ["Sales Invoice"],
			},
		],
	}
