// زر «Go To User Guide» في custom-actions بصفحة Workspaces لمحطة الوقود.
frappe.provide("frappe.views");

const USER_GUIDE_URL = "/docs";

// أيقونات SVG بنفس نمط أيقونات موقع الوثائق (stroke، بلا تعبئة)
const svg = (paths, size) =>
	`<svg class="fuel-guide-svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none"
		stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
		aria-hidden="true">${paths}</svg>`;

const BOOK_ICON = svg(
	'<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
	15
);
const ARROW_ICON = svg('<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>', 13);

function open_user_guide() {
	window.open(USER_GUIDE_URL, "_blank", "noopener");
}

function add_user_guide_button(page) {
	if (page.custom_actions.find(".fuel-guide-btn").length) return;

	const label = __("Go To User Guide");
	$(`<a class="fuel-guide-btn" href="${USER_GUIDE_URL}" target="_blank" rel="noopener"
			title="${label}" aria-label="${label}">
			<span class="fuel-guide-btn-icon">${BOOK_ICON}</span>
			<span class="fuel-guide-btn-label">${label}</span>
			<span class="fuel-guide-btn-arrow">${ARROW_ICON}</span>
		</a>`).appendTo(page.custom_actions);
	page.custom_actions.removeClass("hide");

	if (!page.menu.find(".fuel-guide-menu-item").length) {
		page.add_dropdown_item({
			label,
			click: open_user_guide,
			standard: true,
			parent: page.menu,
			show_parent: false,
		})
			.parent()
			.addClass("fuel-guide-menu-item hidden-xl");
	}

	if (page.menu_btn_group.hasClass("hide")) {
		page.menu_btn_group.removeClass("hide").addClass("hidden-xl");
	}
}

if (frappe.views.Workspace) {
	const original_setup_actions = frappe.views.Workspace.prototype.setup_actions;

	frappe.views.Workspace.prototype.setup_actions = function (page) {
		original_setup_actions.call(this, page);
		// يظهر الزر في مساحة العمل
		if (this.is_read_only && (frappe.boot.fuel_station_show_user_guide_button !== false)) {
			add_user_guide_button(this.page);
		}
	};
}

