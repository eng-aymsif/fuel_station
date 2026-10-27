import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt
from fuel_station.services.settings_service import get_effective_settings


class PumpHandover(Document):
	def validate(self):
		settings = get_effective_settings(station=self.station, pump=self.pump)
		if cint(settings.handover_requires_meter_reading) and self.meter_reading_at_handover is None:
			frappe.throw(_("Meter Reading at Handover is required."))

		if cint(self.unclassified_events) > 0 and not (self.supervisor_approval and self.override_reason):
			frappe.throw(_("Cannot complete handover while there are unclassified dispense events without Supervisor approval and override reason."))

		if self.status in ("Confirmed", "Approved"):
			if self.outgoing_assignment and frappe.db.exists("Fuel Pump Assignment", self.outgoing_assignment):
				frappe.db.set_value(
					"Fuel Pump Assignment",
					self.outgoing_assignment,
					{
						"closing_reading": flt(self.meter_reading_at_handover),
						"closing_meter_reading": flt(self.meter_reading_at_handover),
						"end_time": self.handover_time,
						"assignment_end": self.handover_time,
						"status": "Handed Over",
					},
				)
			if self.pump and self.meter_reading_at_handover is not None:
				frappe.db.set_value("Fuel Pump", self.pump, "current_meter_reading", flt(self.meter_reading_at_handover))
