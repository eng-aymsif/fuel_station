frappe.ui.form.on("Fuel Issue Order", {
	refresh: function (frm) {
		if (!frm.is_new() && frm.doc.approval_status === "Approved") {
			// Create Stock Entry
			if (!frm.doc.stock_entry) {
				frm.add_custom_button(__("Stock Entry (Material Issue)"), function () {
					frappe.call({
						method: "fuel_station.fuel_station.doctype.fuel_issue_order.fuel_issue_order.make_stock_entry",
						args: { issue_order_name: frm.doc.name },
						freeze: true,
						freeze_message: __("Creating Material Issue Stock Entry..."),
						callback: function (r) {
							if (r.message) {
								frm.reload_doc();
								frappe.set_route("Form", "Stock Entry", r.message);
							}
						},
					});
				}, __("Create"));
			}

			// View Links
			frm.add_custom_button(__("Dispense Events"), function () {
				frappe.route_options = { issue_order: frm.doc.name };
				frappe.set_route("List", "Fuel Dispense Event");
			}, __("View"));

			if (frm.doc.stock_entry) {
				frm.add_custom_button(__("Stock Entry"), function () {
					frappe.set_route("Form", "Stock Entry", frm.doc.stock_entry);
				}, __("View"));
			}

			// Print Shortcuts
			frm.add_custom_button(__("Issue Voucher (A4)"), function () {
				const url = `/printview?doctype=Fuel%20Issue%20Order&name=${encodeURIComponent(frm.doc.name)}&format=Fuel%20Issue%20Order%20Voucher&no_letterhead=1`;
				window.open(url, "_blank");
			}, __("Print"));

			frm.add_custom_button(__("Thermal Ticket (80mm)"), function () {
				const url = `/printview?doctype=Fuel%20Issue%20Order&name=${encodeURIComponent(frm.doc.name)}&format=Fuel%20Issue%20Order%20Ticket&no_letterhead=1`;
				window.open(url, "_blank");
			}, __("Print"));
		}
	},
});
