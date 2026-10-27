frappe.pages["fuel-station-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Fuel Station Control Center"),
		single_column: true,
	});

	page.set_title_sub(__("Live Forecourt Operations & Tanks Cockpit"));

	// Primary & Secondary Actions
	page.set_primary_action(__("New Dispense Event"), function () {
		frappe.new_doc("Fuel Dispense Event");
	}, "octicon octicon-plus");

	page.add_button(__("POS Terminal"), function () {
		frappe.set_route("fuel-station-pos");
	});

	page.add_button(__("Refresh"), function () {
		load_dashboard_data();
	}, "octicon octicon-sync");

	const $container = $(wrapper).find(".layout-main-section");
	$container.html(`<div class="fuel-dash-wrapper" id="fuel-dash-root"><div class="text-muted p-4">${__("Loading Fuel Station live operations...")}</div></div>`);

	let current_station = null;

	function format_number(val, decimals = 2) {
		return Number(val || 0).toLocaleString(undefined, {
			minimumFractionDigits: decimals,
			maximumFractionDigits: decimals,
		});
	}

	function load_dashboard_data(station = null) {
		frappe.call({
			method: "fuel_station.fuel_station.page.fuel_station_dashboard.fuel_station_dashboard.get_dashboard_data",
			args: { station: station || current_station },
			callback: function (r) {
				if (r.message) {
					render_dashboard(r.message);
				}
			},
		});
	}

	function render_dashboard(data) {
		current_station = data.current_station;

		// 1. Station Select Options
		let station_options = "";
		(data.stations || []).forEach((st) => {
			const selected = st.name === current_station ? "selected" : "";
			station_options += `<option value="${frappe.utils.escape_html(st.name)}" ${selected}>${frappe.utils.escape_html(st.station_name || st.name)}</option>`;
		});

		// 2. Active Shift Banner
		let shift_badge = "";
		if (data.shift) {
			shift_badge = `
				<span class="fuel-dash-shift-tag tag-open">
					<span class="indicator-pill green"></span>
					${__("Active Shift")}: <b>${frappe.utils.escape_html(data.shift.name)}</b> (${frappe.utils.escape_html(data.shift.shift_type || "")})
				</span>
			`;
		} else {
			shift_badge = `
				<span class="fuel-dash-shift-tag tag-closed">
					<span class="indicator-pill red"></span>
					${__("No Open Shift")}
				</span>
			`;
		}

		// 3. Tanks Cards
		let tanks_html = "";
		(data.tanks || []).forEach((t) => {
			const is_alert = t.is_low ? `border-color: #f87171; background: #fff5f5;` : "";
			tanks_html += `
				<div class="fuel-tank-card" style="${is_alert}">
					<div class="fuel-tank-head">
						<span class="fuel-tank-name">🛢️ ${frappe.utils.escape_html(t.tank_number)}</span>
						<span class="fuel-tank-grade">${frappe.utils.escape_html(t.item)}</span>
					</div>
					<div class="fuel-tank-gauge-bg">
						<div class="fuel-tank-gauge-fill" style="width: ${t.percentage}%;"></div>
					</div>
					<div class="fuel-tank-stats">
						<span><b>${format_number(t.current_stock, 0)} L</b> (${t.percentage}%)</span>
						<span class="text-muted">${__("Cap")}: ${format_number(t.capacity, 0)} L</span>
					</div>
				</div>
			`;
		});
		if (!tanks_html) {
			tanks_html = `<div class="text-muted p-3">${__("No underground tanks configured for this station.")}</div>`;
		}

		// 4. Pumps Cards
		let pumps_html = "";
		(data.pumps || []).forEach((p) => {
			const assigned_label = p.attendant
				? `<span class="text-success">● ${frappe.utils.escape_html(p.attendant)}</span>`
				: `<span class="text-muted">○ ${__("Unassigned")}</span>`;

			pumps_html += `
				<div class="fuel-pump-card">
					<div class="fuel-pump-head">
						<span class="fuel-pump-name">⛽ ${frappe.utils.escape_html(p.pump_number)}</span>
						<span class="badge badge-secondary">${frappe.utils.escape_html(p.item)}</span>
					</div>
					<div class="fuel-meter-display">${format_number(p.current_meter_reading, 2)}</div>
					<div class="fuel-pump-attendant">
						<span>${__("Attendant")}:</span>
						<span><b>${assigned_label}</b></span>
					</div>
				</div>
			`;
		});
		if (!pumps_html) {
			pumps_html = `<div class="text-muted p-3">${__("No pumps configured for this station.")}</div>`;
		}

		// 5. Recent Dispense Rows
		let recent_rows = "";
		(data.recent_dispenses || []).forEach((d) => {
			recent_rows += `
				<tr>
					<td><a href="/app/fuel-dispense-event/${encodeURIComponent(d.name)}"><b>${frappe.utils.escape_html(d.name)}</b></a></td>
					<td>${frappe.datetime.comment_when(d.creation)}</td>
					<td>${frappe.utils.escape_html(d.pump || "-")}</td>
					<td><b>${format_number(d.quantity, 2)} L</b></td>
					<td><b>${format_number(d.grand_total || d.amount, 2)}</b></td>
					<td><span class="badge badge-light">${frappe.utils.escape_html(d.payment_method || "Cash")}</span></td>
					<td>${frappe.utils.escape_html(d.vehicle_plate_number || d.customer || "-")}</td>
				</tr>
			`;
		});
		if (!recent_rows) {
			recent_rows = `<tr><td colspan="7" class="text-center text-muted p-4">${__("No recent dispense events found.")}</td></tr>`;
		}

		const k = data.kpis || {};

		const html = `
			<div class="fuel-dash-wrapper">
				<!-- Top Bar -->
				<div class="fuel-dash-topbar">
					<div class="fuel-dash-title">
						<span>⛽</span>
						<span>${__("Station Operations Monitor")}</span>
					</div>
					<div class="fuel-dash-controls">
						<select class="fuel-dash-select" id="station-picker">
							${station_options}
						</select>
						${shift_badge}
					</div>
				</div>

				<!-- KPIs Grid -->
				<div class="fuel-kpi-grid">
					<div class="fuel-kpi-card kpi-orange">
						<div class="fuel-kpi-title">${__("Volume Dispensed Today")}</div>
						<div class="fuel-kpi-val">${format_number(k.today_liters, 2)} <span style="font-size: 15px; font-weight: 600;">L</span></div>
						<div class="fuel-kpi-sub">${k.dispense_count || 0} ${__("transactions recorded")}</div>
					</div>
					<div class="fuel-kpi-card kpi-green">
						<div class="fuel-kpi-title">${__("Total Revenue Today")}</div>
						<div class="fuel-kpi-val">${format_number(k.today_sales, 2)}</div>
						<div class="fuel-kpi-sub">${__("Across all payment channels")}</div>
					</div>
					<div class="fuel-kpi-card kpi-blue">
						<div class="fuel-kpi-title">${__("Cash vs Card Collections")}</div>
						<div class="fuel-kpi-val" style="font-size: 19px;">
							💵 ${format_number(k.cash_amount || k.cash_sales, 2)}
						</div>
						<div class="fuel-kpi-sub">💳 ${__("Cards / POS")}: ${format_number(k.card_amount || k.card_sales, 2)}</div>
					</div>
					<div class="fuel-kpi-card kpi-purple">
						<div class="fuel-kpi-title">${__("Forecourt Pumps Active")}</div>
						<div class="fuel-kpi-val">${k.active_pumps_count || 0} / ${k.total_pumps_count || 0}</div>
						<div class="fuel-kpi-sub">${k.open_boxes_count || 0} ${__("open attendant cash boxes")}</div>
					</div>
				</div>

				<!-- Underground Tanks Status -->
				<div class="fuel-section-header">
					<span>🛢️</span>
					<span>${__("Underground Storage Tanks (Live Stock Balances)")}</span>
				</div>
				<div class="fuel-tanks-grid">
					${tanks_html}
				</div>

				<!-- Forecourt Pumps Matrix -->
				<div class="fuel-section-header">
					<span>⛽</span>
					<span>${__("Forecourt Dispenser Totalizers & Attendants")}</span>
				</div>
				<div class="fuel-pumps-grid">
					${pumps_html}
				</div>

				<!-- Recent Transactions Feed -->
				<div class="fuel-section-header">
					<span>🧾</span>
					<span>${__("Recent Forecourt Dispense Stream")}</span>
				</div>
				<div class="fuel-table-card">
					<table class="fuel-dash-table">
						<thead>
							<tr>
								<th>${__("Event ID")}</th>
								<th>${__("Time")}</th>
								<th>${__("Pump")}</th>
								<th>${__("Volume")}</th>
								<th>${__("Total Amount")}</th>
								<th>${__("Method")}</th>
								<th>${__("Vehicle / Client")}</th>
							</tr>
						</thead>
						<tbody>
							${recent_rows}
						</tbody>
					</table>
				</div>
			</div>
		`;

		$("#fuel-dash-root").html(html);

		// Event listener for Station dropdown
		$("#station-picker").on("change", function () {
			const selected = $(this).val();
			load_dashboard_data(selected);
		});
	}

	// Initial Load
	load_dashboard_data();
};
