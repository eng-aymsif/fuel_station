frappe.ui.form.on("Customer", {
	refresh: function (frm) {
		if (!frm.is_new()) {
			// Fleet buttons
			frm.add_custom_button(__("Fleet Contracts"), function () {
				frappe.route_options = { customer: frm.doc.name };
				frappe.set_route("List", "Fuel Customer Contract");
			}, __("Fuel Station"));

			frm.add_custom_button(__("Dispense Events"), function () {
				frappe.route_options = { customer: frm.doc.name };
				frappe.set_route("List", "Fuel Dispense Event");
			}, __("Fuel Station"));
		}
	},
});
