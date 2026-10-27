import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime
from fuel_station.services.business_logic import log_audit_event, validate_meter_sequence


class FuelMeterReading(Document):
	def validate(self):
		if not self.reading_time:
			self.reading_time = now_datetime()

		if not self.is_new():
			old = self.get_doc_before_save()
			if old and flt(old.previous_reading) != flt(self.previous_reading):
				roles = frappe.get_roles(frappe.session.user)
				if "Fuel Attendant" in roles and not any(
					r in roles for r in ("Shift Supervisor", "Station Manager", "Fuel Operations Manager", "System Manager", "System Administrator")
				):
					frappe.throw(_("Fuel Attendant is not permitted to modify previous meter readings."))

		if not flt(self.previous_reading) and self.pump and self.reading_type != "Opening":
			self.previous_reading = flt(frappe.db.get_value("Fuel Pump", self.pump, "current_meter_reading"))

		validate_meter_sequence(
			pump=self.pump,
			reading_value=self.reading_value,
			previous_reading=self.previous_reading,
			reading_type=self.reading_type,
			is_meter_reset=self.is_meter_reset,
			correction_reason=self.correction_reason,
			approved_by=self.approved_by,
			station=self.station,
		)

		if flt(self.reading_value) >= flt(self.previous_reading):
			self.meter_quantity = flt(flt(self.reading_value) - flt(self.previous_reading), 4)
		else:
			self.meter_quantity = 0.0

		if self.reading_type in ("Correction", "Calibration"):
			log_audit_event(
				f"Meter Reading {self.reading_type}",
				"Fuel Meter Reading",
				self.name or "New",
				station=self.station,
				previous_value=self.previous_reading,
				new_value=self.reading_value,
				reason=self.correction_reason,
			)

	def on_update(self):
		if self.status in ("Recorded", "Approved") and self.pump:
			frappe.db.set_value("Fuel Pump", self.pump, "current_meter_reading", flt(self.reading_value))
