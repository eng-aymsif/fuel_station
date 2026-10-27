frappe.ui.form.on("Fuel Pump Reconciliation", {
	refresh: function (frm) {
		if (!frm.is_new()) {
			// View Dispenses
			frm.add_custom_button(__("Dispense Events"), function () {
				frappe.route_options = {
					pump: frm.doc.pump,
					shift: frm.doc.shift || "",
				};
				frappe.set_route("List", "Fuel Dispense Event");
			}, __("View"));

			// Print Shortcut
			frm.add_custom_button(__("Pump Audit Report (A4)"), function () {
				const url = `/printview?doctype=Fuel%20Pump%20Reconciliation&name=${encodeURIComponent(frm.doc.name)}&format=Fuel%20Pump%20Audit%20Report&no_letterhead=1`;
				window.open(url, "_blank");
			}, __("Print"));
		}
	},
});
