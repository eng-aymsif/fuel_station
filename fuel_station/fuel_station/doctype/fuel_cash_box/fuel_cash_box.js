frappe.ui.form.on("Fuel Cash Box", {
	refresh: function (frm) {
		if (!frm.is_new()) {
			// Action: Transfer to Safe
			if (frm.doc.status !== "Closed") {
				frm.add_custom_button(__("Transfer to Station Safe"), function () {
					frappe.prompt(
						[
							{
								label: __("Target Safe"),
								fieldname: "target_safe",
								fieldtype: "Link",
								options: "Fuel Station Safe",
								default: frappe.db.get_value("Fuel Station Safe", { station: frm.doc.station }, "name"),
							},
							{
								label: __("Amount to Handover"),
								fieldname: "amount",
								fieldtype: "Currency",
								default: frm.doc.counted_cash || frm.doc.expected_cash,
								reqd: 1,
							},
						],
						function (values) {
							frappe.call({
								method: "fuel_station.fuel_station.doctype.fuel_cash_box.fuel_cash_box.make_safe_transfer",
								args: {
									cash_box_name: frm.doc.name,
									target_safe: values.target_safe,
									amount: values.amount,
								},
								freeze: true,
								freeze_message: __("Recording Safe Transfer..."),
								callback: function (r) {
									frappe.show_alert({
										message: __("Transferred cash to Safe successfully!"),
										indicator: "green",
									});
									frm.reload_doc();
								},
							});
						},
						__("Handover Cash to Safe"),
						__("Transfer")
					);
				}, __("Actions"));
			}

			// Print Shortcuts
			frm.add_custom_button(__("Denomination Sheet (A4)"), function () {
				const url = `/printview?doctype=Fuel%20Cash%20Box&name=${encodeURIComponent(frm.doc.name)}&format=Fuel%20Cash%20Box%20Denomination%20Sheet&no_letterhead=1`;
				window.open(url, "_blank");
			}, __("Print"));

			frm.add_custom_button(__("Handover Receipt (80mm)"), function () {
				const url = `/printview?doctype=Fuel%20Cash%20Box&name=${encodeURIComponent(frm.doc.name)}&format=Fuel%20Cash%20Box%20Handover%20Receipt&no_letterhead=1`;
				window.open(url, "_blank");
			}, __("Print"));
		}
	},
});
