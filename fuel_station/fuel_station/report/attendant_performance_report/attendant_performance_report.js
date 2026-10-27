frappe.query_reports["Attendant Performance Report"] = {
	"filters": [
		{"fieldname": "station", "label": __("Station"), "fieldtype": "Link", "options": "Fuel Station"},
		{"fieldname": "shift", "label": __("Shift"), "fieldtype": "Link", "options": "Fuel Shift"},
		{"fieldname": "business_date", "label": __("Date"), "fieldtype": "Date"}
	]
};
