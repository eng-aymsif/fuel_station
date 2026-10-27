import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt
from fuel_station.services.settings_service import get_effective_settings


class FuelPumpAssignment(Document):
	def validate(self):
		# Synchronize alias fields
		if flt(self.opening_reading) and not flt(self.opening_meter_reading):
			self.opening_meter_reading = flt(self.opening_reading)
		elif flt(self.opening_meter_reading) and not flt(self.opening_reading):
			self.opening_reading = flt(self.opening_meter_reading)

		if flt(self.closing_reading) and not flt(self.closing_meter_reading):
			self.closing_meter_reading = flt(self.closing_reading)
		elif flt(self.closing_meter_reading) and not flt(self.closing_reading):
			self.closing_reading = flt(self.closing_meter_reading)

		if self.start_time and not self.assignment_start:
			self.assignment_start = self.start_time
		elif self.assignment_start and not self.start_time:
			self.start_time = self.assignment_start

		if self.end_time and not self.assignment_end:
			self.assignment_end = self.end_time
		elif self.assignment_end and not self.end_time:
			self.end_time = self.assignment_end

		if self.employee and not self.user:
			self.user = frappe.db.get_value("Employee", self.employee, "user_id")

		settings = get_effective_settings(station=self.station, pump=self.pump)

		# Prevent duplicate active assignment on the same pump in the same shift unless allowed
		if self.status == "Active" and not cint(settings.allow_multiple_attendants_per_pump):
			filters = {
				"pump": self.pump,
				"status": "Active",
				"name": ["!=", self.name or ""],
			}
			if self.shift:
				filters["shift"] = self.shift
			elif self.business_date:
				filters["business_date"] = self.business_date

			conflicts = frappe.get_all("Fuel Pump Assignment", filters=filters, pluck="name")
			if conflicts:
				frappe.throw(
					_("Pump {0} already has an active attendant assignment ({1}). Multiple attendants per pump are disabled.").format(
						self.pump, ", ".join(conflicts)
					)
				)

		# Prevent modifying employee or pump after dispense events exist unless approved correction
		if not self.is_new():
			old = self.get_doc_before_save()
			if old and (old.employee != self.employee or old.pump != self.pump):
				has_events = frappe.db.exists("Fuel Dispense Event", {"assignment": self.name, "status": ["!=", "Cancelled"]})
				if has_events and not (cint(self.correction_approved) and self.correction_reason):
					frappe.throw(_("Cannot modify assignment employee or pump after dispense events have been recorded without an approved correction."))
