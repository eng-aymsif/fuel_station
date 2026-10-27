frappe.ui.form.on("Fuel Delivery", {
	refresh: function (frm) {
		if (frm.doc.docstatus < 2 && !frm.is_new()) {
			// Action button: Create Purchase Receipt
			if (!frm.doc.purchase_receipt) {
				frm.add_custom_button(__("Purchase Receipt"), function () {
					frappe.call({
						method: "fuel_station.fuel_station.doctype.fuel_delivery.fuel_delivery.make_purchase_receipt",
						args: { delivery_name: frm.doc.name },
						freeze: true,
						freeze_message: __("Creating ERPNext Purchase Receipt..."),
						callback: function (r) {
							if (r.message) {
								frm.reload_doc();
								frappe.set_route("Form", "Purchase Receipt", r.message);
							}
						},
					});
				}, __("Create"));
			}

			// Action button: Create Purchase Invoice
			frm.add_custom_button(__("Purchase Invoice"), function () {
				frappe.call({
					method: "fuel_station.fuel_station.doctype.fuel_delivery.fuel_delivery.make_purchase_invoice",
					args: { delivery_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Creating ERPNext Purchase Invoice..."),
					callback: function (r) {
						if (r.message) {
							frappe.set_route("Form", "Purchase Invoice", r.message);
						}
					},
				});
			}, __("Create"));

			// View buttons
			if (frm.doc.warehouse && frm.doc.item) {
				frm.add_custom_button(__("Stock Ledger"), function () {
					frappe.route_options = {
						voucher_no: frm.doc.purchase_receipt || "",
						warehouse: frm.doc.warehouse,
						item_code: frm.doc.item,
					};
					frappe.set_route("query-report", "Stock Ledger");
				}, __("View"));
			}

			// Print button
			frm.add_custom_button(__("Receiving Report"), function () {
				const url = `/printview?doctype=Fuel%20Delivery&name=${encodeURIComponent(frm.doc.name)}&format=Fuel%20Delivery%20Receiving%20Report&no_letterhead=1`;
				window.open(url, "_blank");
			}, __("Print"));
		}
	},
});
