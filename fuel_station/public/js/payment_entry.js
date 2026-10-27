frappe.ui.form.on("Payment Entry", {
	refresh: function (frm) {
		if (!frm.is_new()) {
			// Check if linked to Fuel Station Safe
			frappe.db.get_value(
				"Fuel Station Safe",
				{ bank_deposit_payment_entry: frm.doc.name },
				"name",
				function (r) {
					if (r && r.name) {
						frm.add_custom_button(__("Fuel Station Safe"), function () {
							frappe.set_route("Form", "Fuel Station Safe", r.name);
						}, __("Fuel Station"));
					}
				}
			);
		}
	},
});
