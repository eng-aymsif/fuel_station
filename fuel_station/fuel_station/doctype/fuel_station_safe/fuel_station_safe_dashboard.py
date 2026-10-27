from frappe import _


def get_data():
	return {
		"fieldname": "to_safe",
		"transactions": [
			{
				"label": _("Treasury Inflows"),
				"items": ["Cash Transfer"],
			},
		],
	}
