frappe.ui.form.on("Stock Entry", {
	refresh: function (frm) {
		if (!frm.is_new()) {
			// Check if linked to Fuel Issue Order
			frappe.db.get_value(
				"Fuel Issue Order",
				{ stock_entry: frm.doc.name },
				"name",
				function (r) {
					if (r && r.name) {
						frm.add_custom_button(__("Fuel Issue Order"), function () {
							frappe.set_route("Form", "Fuel Issue Order", r.name);
						}, __("Fuel Station"));
					}
				}
			);
		}
	},
});
