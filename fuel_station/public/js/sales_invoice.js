frappe.ui.form.on("Sales Invoice", {
	refresh: function (frm) {
		if (!frm.is_new()) {
			// Check if linked to Fuel Station
			if (frm.doc.fuel_station || frm.doc.fuel_shift) {
				frm.add_custom_button(__("Fuel Dispense Events"), function () {
					frappe.route_options = { invoice: frm.doc.name };
					frappe.set_route("List", "Fuel Dispense Event");
				}, __("Fuel Station"));

				frm.add_custom_button(__("Fuel Tax Invoice (A4)"), function () {
					const url = `/printview?doctype=Sales%20Invoice&name=${encodeURIComponent(frm.doc.name)}&format=Fuel%20Standard%20Tax%20Invoice&no_letterhead=1`;
					window.open(url, "_blank");
				}, __("Print"));

				frm.add_custom_button(__("POS Thermal Receipt (80mm)"), function () {
					const url = `/printview?doctype=Sales%20Invoice&name=${encodeURIComponent(frm.doc.name)}&format=Fuel%20POS%20Thermal%20Receipt&no_letterhead=1`;
					window.open(url, "_blank");
				}, __("Print"));
			}
		}
	},
});
