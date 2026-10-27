from frappe import _


def get_data():
	return {
		"internal_links": {
			"Fuel Pump Invoice Batch": ["invoice_batch"],
			"Fuel Reconciliation Exception": ["exception_reference"],
		},
		"transactions": [
			{
				"label": _("Resolution & Invoicing"),
				"items": ["Fuel Pump Invoice Batch", "Fuel Reconciliation Exception"],
			},
		],
	}
