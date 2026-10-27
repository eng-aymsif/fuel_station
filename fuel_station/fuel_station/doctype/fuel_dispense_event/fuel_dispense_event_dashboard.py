from frappe import _


def get_data():
	return {
		"internal_links": {
			"Sales Invoice": ["sales_invoice"],
			"Stock Entry": ["stock_entry"],
		},
		"transactions": [
			{
				"label": _("Billing & Stock"),
				"items": ["Sales Invoice", "Stock Entry"],
			},
		],
	}
