frappe.ui.form.on("Purchase Receipt", {
	refresh: function (frm) {
		if (!frm.is_new()) {
			// Check if linked to Fuel Delivery
			frappe.db.get_value(
				"Fuel Delivery",
				{ purchase_receipt: frm.doc.name },
				"name",
				function (r) {
					if (r && r.name) {
						frm.add_custom_button(__("Fuel Tank Delivery"), function () {
							frappe.set_route("Form", "Fuel Delivery", r.name);
						}, __("Fuel Station"));
					}
				}
			);
		}
	},
});
