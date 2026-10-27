from frappe import _


def get_data():
	return {
		"fieldname": "fuel_delivery",
		"non_standard_fieldnames": {
			"Purchase Receipt": "name",
			"Purchase Order": "name",
		},
		"transactions": [
			{
				"label": _("Procurement & Stock"),
				"items": ["Purchase Receipt", "Purchase Order"],
			},
		],
	}
