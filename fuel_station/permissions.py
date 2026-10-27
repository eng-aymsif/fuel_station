import frappe


def get_allowed_stations_for_user(user=None):
	"""Return list of allowed Fuel Station names if user has station User Permissions,
	or None if user has unrestricted access across stations.
	"""
	user = user or frappe.session.user
	if user == "Administrator":
		return None

	roles = frappe.get_roles(user)
	if "System Manager" in roles or "System Administrator" in roles:
		# Even if System Manager, check if explicit User Permission for Fuel Station is set for testing
		pass

	perms = frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": "Fuel Station"},
		pluck="for_value",
	)
	if perms:
		return perms
	return None


def _station_condition(table_name, fieldname="station", user=None):
	allowed = get_allowed_stations_for_user(user)
	if allowed is None:
		return ""
	if not allowed:
		return "1=0"
	escaped = ", ".join(frappe.db.escape(s) for s in allowed)
	return f"`tab{table_name}`.`{fieldname}` IN ({escaped})"


def get_station_query_conditions(user=None):
	return _station_condition("Fuel Station", "name", user)


def get_tank_query_conditions(user=None):
	return _station_condition("Fuel Tank", "station", user)


def get_pump_query_conditions(user=None):
	return _station_condition("Fuel Pump", "station", user)


def get_shift_query_conditions(user=None):
	return _station_condition("Fuel Shift", "station", user)


def get_assignment_query_conditions(user=None):
	return _station_condition("Fuel Pump Assignment", "station", user)


def get_reading_query_conditions(user=None):
	return _station_condition("Fuel Meter Reading", "station", user)


def get_dispense_query_conditions(user=None):
	return _station_condition("Fuel Dispense Event", "station", user)


def get_reconciliation_query_conditions(user=None):
	return _station_condition("Fuel Pump Reconciliation", "station", user)


def get_cash_box_query_conditions(user=None):
	return _station_condition("Fuel Cash Box", "station", user)


def get_safe_query_conditions(user=None):
	return _station_condition("Fuel Station Safe", "station", user)


def has_station_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	allowed = get_allowed_stations_for_user(user)
	if allowed is None:
		return True
	station_val = doc.name if doc.doctype == "Fuel Station" else doc.get("station")
	if station_val and station_val not in allowed:
		return False
	return True

