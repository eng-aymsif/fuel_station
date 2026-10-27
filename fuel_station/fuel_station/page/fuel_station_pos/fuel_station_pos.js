frappe.pages["fuel-station-pos"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Fuel Fast POS"),
		single_column: true,
	});

	page.set_title_sub(__("Rapid Forecourt Dispense Terminal"));

	page.add_button(__("Dashboard"), function () {
		frappe.set_route("fuel-station-dashboard");
	}, "octicon octicon-dashboard");

	page.add_button(__("Dispense Log"), function () {
		frappe.set_route("List", "Fuel Dispense Event");
	});

	const $container = $(wrapper).find(".layout-main-section");
	$container.html(`<div class="fuel-pos-wrapper" id="fuel-pos-root"><div class="text-muted p-4">${__("Initializing Fast POS Terminal...")}</div></div>`);

	let state = {
		stations: [],
		current_station: null,
		shift: null,
		pumps: [],
		items: [],
		customers: [],
		issue_orders: [],
		selected_pump: null,
		quantity: 20.0,
		rate: 2.0,
		payment_method: "Cash",
		customer: "",
		vehicle_plate: "",
		driver_name: "",
		issue_order: "",
	};

	function format_currency(val) {
		return Number(val || 0).toLocaleString(undefined, {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2,
		});
	}

	function load_init_data(station = null) {
		frappe.call({
			method: "fuel_station.fuel_station.page.fuel_station_pos.fuel_station_pos.get_pos_init_data",
			args: { station: station || state.current_station },
			callback: function (r) {
				if (r.message) {
					const m = r.message;
					state.stations = m.stations || [];
					state.current_station = m.current_station;
					state.shift = m.shift;
					state.pumps = m.pumps || [];
					state.items = m.items || [];
					state.customers = m.customers || [];
					state.issue_orders = m.issue_orders || [];

					if (state.pumps.length > 0 && !state.selected_pump) {
						state.selected_pump = state.pumps[0];
						state.rate = state.selected_pump.rate || 2.0;
					}
					render_pos();
				}
			},
		});
	}

	function render_pos() {
		// 1. Station Select
		let st_opts = "";
		state.stations.forEach((s) => {
			const sel = s.name === state.current_station ? "selected" : "";
			st_opts += `<option value="${frappe.utils.escape_html(s.name)}" ${sel}>${frappe.utils.escape_html(s.station_name || s.name)}</option>`;
		});

		// 2. Pumps buttons
		let pumps_html = "";
		state.pumps.forEach((p) => {
			const is_act = state.selected_pump && state.selected_pump.name === p.name ? "active" : "";
			pumps_html += `
				<div class="pos-pump-btn ${is_act}" data-pump="${frappe.utils.escape_html(p.name)}">
					<div class="pos-pump-label">⛽ ${frappe.utils.escape_html(p.pump_number || p.name)}</div>
					<div class="pos-pump-grade">${frappe.utils.escape_html(p.item)}</div>
					<div class="pos-pump-meter">${__("Meter")}: ${format_currency(p.current_meter_reading)}</div>
				</div>
			`;
		});

		// 3. Customer & fleet extra inputs
		let fleet_fields = "";
		if (state.payment_method === "Customer Credit") {
			let cust_opts = `<option value="">-- ${__("Select Fleet Customer")} --</option>`;
			state.customers.forEach((c) => {
				const s = state.customer === c.name ? "selected" : "";
				cust_opts += `<option value="${frappe.utils.escape_html(c.name)}" ${s}>${frappe.utils.escape_html(c.customer_name || c.name)}</option>`;
			});

			fleet_fields = `
				<div class="pos-field" style="margin-top: 10px;">
					<label>${__("Fleet Corporate Client")}</label>
					<select class="pos-input" id="pos-customer-select">${cust_opts}</select>
				</div>
				<div class="fuel-pos-inputs" style="margin-top: 10px;">
					<div class="pos-field">
						<label>${__("Vehicle Plate No")}</label>
						<input type="text" class="pos-input" id="pos-plate-input" value="${frappe.utils.escape_html(state.vehicle_plate)}" placeholder="e.g. ABC-1234">
					</div>
					<div class="pos-field">
						<label>${__("Driver Name")}</label>
						<input type="text" class="pos-input" id="pos-driver-input" value="${frappe.utils.escape_html(state.driver_name)}" placeholder="Driver Full Name">
					</div>
				</div>
			`;
		} else if (state.payment_method === "Issue Order") {
			let order_opts = `<option value="">-- ${__("Select Active Issue Order")} --</option>`;
			state.issue_orders.forEach((o) => {
				const s = state.issue_order === o.name ? "selected" : "";
				order_opts += `<option value="${frappe.utils.escape_html(o.name)}" ${s}>${frappe.utils.escape_html(o.name)} (${frappe.utils.escape_html(o.plate_number || o.vehicle || "")} - Rem: ${o.remaining_quantity}L)</option>`;
			});

			fleet_fields = `
				<div class="pos-field" style="margin-top: 10px;">
					<label>${__("Internal Issue Order Voucher")}</label>
					<select class="pos-input" id="pos-order-select">${order_opts}</select>
				</div>
			`;
		}

		const total_amount = round_number(state.quantity * state.rate, 2);

		const html = `
			<div class="fuel-pos-wrapper">
				<div class="fuel-pos-layout">
					<!-- Left Section: Transaction builder -->
					<div class="fuel-pos-main">
						<!-- Station & Shift bar -->
						<div class="fuel-pos-card" style="padding: 12px 18px;">
							<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
								<div style="display: flex; align-items: center; gap: 8px;">
									<span style="font-size: 13px; font-weight: 700; color: #475569;">${__("Station")}:</span>
									<select class="pos-input" style="padding: 6px 12px; width: auto;" id="pos-station-select">
										${st_opts}
									</select>
								</div>
								<div>
									${state.shift ? `<span class="badge badge-success">✓ ${__("Open Shift")}: ${frappe.utils.escape_html(state.shift.name)}</span>` : `<span class="badge badge-danger">! ${__("No Open Shift")}</span>`}
								</div>
							</div>
						</div>

						<!-- Step 1: Pump Selection -->
						<div class="fuel-pos-card">
							<div class="fuel-pos-title">
								<span>1️⃣</span>
								<span>${__("Select Pump / Nozzle")}</span>
							</div>
							<div class="fuel-pos-pumps">
								${pumps_html || `<div class="text-muted">${__("No pumps available")}</div>`}
							</div>
						</div>

						<!-- Step 2: Volume / Quantity Presets -->
						<div class="fuel-pos-card">
							<div class="fuel-pos-title">
								<span>2️⃣</span>
								<span>${__("Dispense Quantity (Liters)")}</span>
							</div>
							<div class="fuel-preset-buttons">
								<div class="pos-preset-btn ${state.quantity === 10 ? "active" : ""}" data-qty="10">10 L</div>
								<div class="pos-preset-btn ${state.quantity === 20 ? "active" : ""}" data-qty="20">20 L</div>
								<div class="pos-preset-btn ${state.quantity === 30 ? "active" : ""}" data-qty="30">30 L</div>
								<div class="pos-preset-btn ${state.quantity === 50 ? "active" : ""}" data-qty="50">50 L</div>
								<div class="pos-preset-btn ${state.quantity === 80 ? "active" : ""}" data-qty="80">Full (80L)</div>
							</div>
							<div class="fuel-pos-inputs">
								<div class="pos-field">
									<label>${__("Quantity (Liters)")}</label>
									<input type="number" step="0.01" class="pos-input" id="pos-qty-input" value="${state.quantity}">
								</div>
								<div class="pos-field">
									<label>${__("Unit Rate")}</label>
									<input type="number" step="0.01" class="pos-input" id="pos-rate-input" value="${state.rate}">
								</div>
							</div>
						</div>

						<!-- Step 3: Payment & Customer -->
						<div class="fuel-pos-card">
							<div class="fuel-pos-title">
								<span>3️⃣</span>
								<span>${__("Payment Method & Customer")}</span>
							</div>
							<div class="pos-pay-methods">
								<div class="pos-pay-btn ${state.payment_method === "Cash" ? "active" : ""}" data-method="Cash">💵 ${__("Cash")}</div>
								<div class="pos-pay-btn ${state.payment_method === "Card" ? "active" : ""}" data-method="Card">💳 ${__("POS Card")}</div>
								<div class="pos-pay-btn ${state.payment_method === "Customer Credit" ? "active" : ""}" data-method="Customer Credit">🏢 ${__("Fleet Credit")}</div>
								<div class="pos-pay-btn ${state.payment_method === "Issue Order" ? "active" : ""}" data-method="Issue Order">🎫 ${__("Issue Order")}</div>
							</div>
							${fleet_fields}
						</div>
					</div>

					<!-- Right Section: Receipt Ticket Preview -->
					<div class="fuel-pos-sidebar">
						<div class="fuel-pos-summary">
							<div class="fuel-summary-title">🧾 ${__("Ticket Summary")}</div>
							<div class="fuel-summary-row">
								<span>${__("Station")}:</span>
								<b>${frappe.utils.escape_html(state.current_station || "-")}</b>
							</div>
							<div class="fuel-summary-row">
								<span>${__("Pump")}:</span>
								<b>${frappe.utils.escape_html(state.selected_pump ? state.selected_pump.pump_number || state.selected_pump.name : "-")}</b>
							</div>
							<div class="fuel-summary-row">
								<span>${__("Product")}:</span>
								<b>${frappe.utils.escape_html(state.selected_pump ? state.selected_pump.item : "-")}</b>
							</div>
							<div class="fuel-summary-row">
								<span>${__("Volume")}:</span>
								<b>${format_currency(state.quantity)} L</b>
							</div>
							<div class="fuel-summary-row">
								<span>${__("Tariff Rate")}:</span>
								<b>${format_currency(state.rate)}</b>
							</div>
							<div class="fuel-summary-row">
								<span>${__("Payment")}:</span>
								<b>${frappe.utils.escape_html(state.payment_method)}</b>
							</div>

							<div class="fuel-summary-total">
								${format_currency(total_amount)}
							</div>

							<button class="pos-btn-submit" id="pos-submit-btn" ${!state.selected_pump || state.quantity <= 0 ? "disabled" : ""}>
								✓ ${__("Confirm Dispense & Print")}
							</button>
						</div>
					</div>
				</div>
			</div>
		`;

		$("#fuel-pos-root").html(html);

		// Wire Event Handlers
		bind_pos_events();
	}

	function round_number(val, dec = 2) {
		return Math.round(val * Math.pow(10, dec)) / Math.pow(10, dec);
	}

	function bind_pos_events() {
		// Station change
		$("#pos-station-select").on("change", function () {
			load_init_data($(this).val());
		});

		// Pump click
		$(".pos-pump-btn").on("click", function () {
			const pump_id = $(this).data("pump");
			const found = state.pumps.find((p) => p.name === pump_id);
			if (found) {
				state.selected_pump = found;
				state.rate = found.rate || 2.0;
				render_pos();
			}
		});

		// Preset click
		$(".pos-preset-btn").on("click", function () {
			state.quantity = Number($(this).data("qty"));
			render_pos();
		});

		// Manual inputs
		$("#pos-qty-input").on("input", function () {
			state.quantity = Math.max(0, Number($(this).val()));
			const total = round_number(state.quantity * state.rate, 2);
			$(".fuel-summary-total").text(format_currency(total));
			$(".fuel-summary-row:contains('" + __("Volume") + "') b").text(format_currency(state.quantity) + " L");
		});

		$("#pos-rate-input").on("input", function () {
			state.rate = Math.max(0, Number($(this).val()));
			const total = round_number(state.quantity * state.rate, 2);
			$(".fuel-summary-total").text(format_currency(total));
		});

		// Payment method click
		$(".pos-pay-btn").on("click", function () {
			state.payment_method = $(this).data("method");
			render_pos();
		});

		// Fleet customer change
		$("#pos-customer-select").on("change", function () {
			state.customer = $(this).val();
		});

		$("#pos-plate-input").on("input", function () {
			state.vehicle_plate = $(this).val();
		});

		$("#pos-driver-input").on("input", function () {
			state.driver_name = $(this).val();
		});

		$("#pos-order-select").on("change", function () {
			state.issue_order = $(this).val();
		});

		// Submit transaction
		$("#pos-submit-btn").on("click", function () {
			submit_transaction();
		});
	}

	function submit_transaction() {
		if (!state.selected_pump) {
			frappe.msgprint(__("Please select a pump."));
			return;
		}
		if (state.quantity <= 0) {
			frappe.msgprint(__("Quantity must be greater than zero."));
			return;
		}

		frappe.dom.freeze(__("Recording Dispense & Finalizing Ticket..."));

		const payload = {
			station: state.current_station,
			shift: state.shift ? state.shift.name : null,
			pump: state.selected_pump.name,
			quantity: state.quantity,
			rate: state.rate,
			payment_method: state.payment_method,
			customer: state.customer,
			vehicle_plate_number: state.vehicle_plate,
			driver_name: state.driver_name,
			issue_order: state.issue_order,
		};

		frappe.call({
			method: "fuel_station.fuel_station.page.fuel_station_pos.fuel_station_pos.submit_pos_dispense",
			args: { payload: payload },
			callback: function (r) {
				frappe.dom.unfreeze();
				if (r.message) {
					const res = r.message;
					frappe.show_alert({
						message: __("Fuel Dispense Event {0} recorded successfully!", [res.name]),
						indicator: "green",
					});

					// Update pump meter locally
					state.selected_pump.current_meter_reading = res.reading_after;

					// Print Dialog
					frappe.msgprint({
						title: __("Dispense Completed Successfully"),
						indicator: "green",
						message: `
							<div class="text-center p-3">
								<div style="font-size: 32px;">⛽</div>
								<div style="font-size: 18px; font-weight: 800; margin: 8px 0;">${res.name}</div>
								<div class="text-muted">${__("Quantity")}: <b>${format_currency(res.quantity)} L</b> | ${__("Total")}: <b>${format_currency(res.grand_total)}</b></div>
								<div style="margin-top: 16px;">
									<a href="/printview?doctype=Fuel%20Dispense%20Event&name=${encodeURIComponent(res.name)}&format=Fuel%20Dispense%20Thermal%20Receipt&no_letterhead=1" target="_blank" class="btn btn-primary btn-sm">
										🖨️ ${__("Print 80mm Thermal Receipt")}
									</a>
								</div>
							</div>
						`,
					});

					render_pos();
				}
			},
			error: function () {
				frappe.dom.unfreeze();
			},
		});
	}

	load_init_data();
};
