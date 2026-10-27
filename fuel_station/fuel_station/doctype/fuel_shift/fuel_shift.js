frappe.ui.form.on("Fuel Shift", {
	refresh: function (frm) {
		if (!frm.is_new()) {
			// Action: Batch generate Sales Invoices
			if (frm.doc.status === "Closed" || frm.doc.status === "In Operation") {
				frm.add_custom_button(__("Batch Invoices"), function () {
					frappe.confirm(
						__("Generate consolidated Sales Invoices for un-invoiced pump events in this shift?"),
						function () {
							frappe.call({
								method: "fuel_station.fuel_station.doctype.fuel_shift.fuel_shift.generate_shift_sales_invoices",
								args: { shift_name: frm.doc.name },
								freeze: true,
								freeze_message: __("Batch generating sales invoices..."),
								callback: function (r) {
									frappe.show_alert({
										message: __("Generated sales invoices successfully!"),
										indicator: "green",
									});
									frm.reload_doc();
								},
							});
						}
					);
				}, __("Create"));
			}

			// View Links
			frm.add_custom_button(__("Dispense Events"), function () {
				frappe.route_options = { shift: frm.doc.name };
				frappe.set_route("List", "Fuel Dispense Event");
			}, __("View"));

			frm.add_custom_button(__("Cash Boxes"), function () {
				frappe.route_options = { shift: frm.doc.name };
				frappe.set_route("List", "Fuel Cash Box");
			}, __("View"));

			frm.add_custom_button(__("Pump Reconciliations"), function () {
				frappe.route_options = { shift: frm.doc.name };
				frappe.set_route("List", "Fuel Pump Reconciliation");
			}, __("View"));

			// Print Shortcuts
			frm.add_custom_button(__("Shift Summary Report"), function () {
				const url = `/printview?doctype=Fuel%20Shift&name=${encodeURIComponent(frm.doc.name)}&format=Fuel%20Shift%20Summary%20Report&no_letterhead=1`;
				window.open(url, "_blank");
			}, __("Print"));

			frm.add_custom_button(__("Attendant Handover Sheet"), function () {
				const url = `/printview?doctype=Fuel%20Shift&name=${encodeURIComponent(frm.doc.name)}&format=Fuel%20Shift%20Handover%20Sheet&no_letterhead=1`;
				window.open(url, "_blank");
			}, __("Print"));
		}
	},
});
