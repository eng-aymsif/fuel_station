frappe.ui.form.on("Fuel Customer Contract", {
	refresh: function (frm) {
		if (!frm.is_new()) {
			// Action: Create Payment Entry
			frm.add_custom_button(__("Payment Entry (Receipt)"), function () {
				frappe.call({
					method: "fuel_station.fuel_station.doctype.fuel_customer_contract.fuel_customer_contract.make_payment_entry",
					args: { contract_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Preparing Payment Entry..."),
					callback: function (r) {
						if (r.message) {
							frappe.set_route("Form", "Payment Entry", r.message);
						}
					},
				});
			}, __("Create"));

			// Action: Check Credit Exposure
			frm.add_custom_button(__("Credit Health Check"), function () {
				frappe.call({
					method: "fuel_station.fuel_station.doctype.fuel_customer_contract.fuel_customer_contract.get_customer_credit_summary",
					args: { contract_name: frm.doc.name },
					callback: function (r) {
						if (r.message) {
							const res = r.message;
							const d = res.details || {};
							const indicator = res.allowed ? "green" : "red";
							frappe.msgprint({
								title: __("Fleet Credit Evaluation"),
								indicator: indicator,
								message: `
									<div class="p-2">
										<p><b>${__("Status")}:</b> <span class="indicator-pill ${indicator}"></span> ${res.status || "-"}</p>
										<p><b>${__("Approved Credit Limit")}:</b> ${format_currency(res.credit_limit)}</p>
										<p><b>${__("Posted Ledger Outstanding (AR)")}:</b> ${format_currency(d.current_outstanding)}</p>
										<p><b>${__("Un-invoiced Approved Dispenses")}:</b> ${format_currency(d.pending_commitments)}</p>
										<hr>
										<p style="font-size: 14px; font-weight: 700;">
											<b>${__("Available Remaining Credit")}:</b> ${format_currency(d.available_credit)}
										</p>
									</div>
								`,
							});
						}
					},
				});
			}, __("Actions"));

			// View Links
			frm.add_custom_button(__("Dispense Events"), function () {
				frappe.route_options = { customer: frm.doc.customer };
				frappe.set_route("List", "Fuel Dispense Event");
			}, __("View"));

			frm.add_custom_button(__("Sales Invoices"), function () {
				frappe.route_options = { customer: frm.doc.customer };
				frappe.set_route("List", "Sales Invoice");
			}, __("View"));

			// Print Shortcut
			frm.add_custom_button(__("Contract Agreement"), function () {
				const url = `/printview?doctype=Fuel%20Customer%20Contract&name=${encodeURIComponent(frm.doc.name)}&format=Fuel%20Customer%20Contract%20Agreement&no_letterhead=1`;
				window.open(url, "_blank");
			}, __("Print"));
		}
	},
});
