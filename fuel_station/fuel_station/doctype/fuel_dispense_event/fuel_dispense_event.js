frappe.ui.form.on("Fuel Dispense Event", {
	refresh: function (frm) {
		if (!frm.is_new() && frm.doc.status !== "Cancelled") {
			// Create Sales Invoice if un-invoiced
			if (!frm.doc.invoice && frm.doc.payment_method !== "Internal Issue") {
				frm.add_custom_button(__("Sales Invoice"), function () {
					frappe.call({
						method: "fuel_station.fuel_station.doctype.fuel_dispense_event.fuel_dispense_event.make_sales_invoice",
						args: { event_name: frm.doc.name },
						freeze: true,
						freeze_message: __("Creating ERPNext Sales Invoice..."),
						callback: function (r) {
							if (r.message) {
								frm.reload_doc();
								frappe.set_route("Form", "Sales Invoice", r.message);
							}
						},
					});
				}, __("Create"));
			}

			// View Links
			if (frm.doc.invoice) {
				frm.add_custom_button(__("Sales Invoice"), function () {
					frappe.set_route("Form", "Sales Invoice", frm.doc.invoice);
				}, __("View"));

				frm.add_custom_button(__("Accounting Ledger"), function () {
					frappe.route_options = {
						voucher_no: frm.doc.invoice,
					};
					frappe.set_route("query-report", "General Ledger");
				}, __("View"));
			}

			if (frm.doc.warehouse && frm.doc.item) {
				frm.add_custom_button(__("Stock Ledger"), function () {
					frappe.route_options = {
						warehouse: frm.doc.warehouse,
						item_code: frm.doc.item,
					};
					frappe.set_route("query-report", "Stock Ledger");
				}, __("View"));
			}

			// Print Shortcuts
			frm.add_custom_button(__("Thermal Receipt (80mm)"), function () {
				const url = `/printview?doctype=Fuel%20Dispense%20Event&name=${encodeURIComponent(frm.doc.name)}&format=Fuel%20Dispense%20Thermal%20Receipt&no_letterhead=1`;
				window.open(url, "_blank");
			}, __("Print"));

			frm.add_custom_button(__("Dispense Slip (A4/A5)"), function () {
				const url = `/printview?doctype=Fuel%20Dispense%20Event&name=${encodeURIComponent(frm.doc.name)}&format=Fuel%20Dispense%20Slip&no_letterhead=1`;
				window.open(url, "_blank");
			}, __("Print"));
		}
	},
});
