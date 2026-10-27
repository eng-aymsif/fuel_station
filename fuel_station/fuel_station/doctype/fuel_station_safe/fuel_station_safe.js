frappe.ui.form.on("Fuel Station Safe", {
	refresh: function (frm) {
		if (!frm.is_new()) {
			// Action: Bank Deposit
			frm.add_custom_button(__("Deposit to Bank"), function () {
				frappe.prompt(
					[
						{
							label: __("Deposit Amount"),
							fieldname: "amount",
							fieldtype: "Currency",
							default: frm.doc.counted_safe_balance || frm.doc.expected_safe_balance,
							reqd: 1,
						},
						{
							label: __("Company Bank Account"),
							fieldname: "bank_account",
							fieldtype: "Link",
							options: "Account",
						},
					],
					function (values) {
						frappe.call({
							method: "fuel_station.fuel_station.doctype.fuel_station_safe.fuel_station_safe.make_bank_deposit",
							args: {
								safe_name: frm.doc.name,
								bank_account: values.bank_account,
								amount: values.amount,
							},
							freeze: true,
							freeze_message: __("Recording Bank Deposit Payment Entry..."),
							callback: function (r) {
								if (r.message) {
									frappe.show_alert({
										message: __("Payment Entry {0} created successfully!", [r.message]),
										indicator: "green",
									});
									frm.reload_doc();
									frappe.set_route("Form", "Payment Entry", r.message);
								}
							},
						});
					},
					__("Bank Deposit from Vault"),
					__("Deposit")
				);
			}, __("Actions"));

			// Print Shortcuts
			frm.add_custom_button(__("Safe Audit Statement (A4)"), function () {
				const url = `/printview?doctype=Fuel%20Station%20Safe&name=${encodeURIComponent(frm.doc.name)}&format=Fuel%20Safe%20Audit%20Statement&no_letterhead=1`;
				window.open(url, "_blank");
			}, __("Print"));
		}
	},
});
