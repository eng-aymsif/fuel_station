import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime
from fuel_station.services.settings_service import get_effective_settings


class CashTransfer(Document):
	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("Transfer amount must be greater than zero."))
		if not self.transfer_time:
			self.transfer_time = now_datetime()

		settings = get_effective_settings(station=self.station)
		if self.status in ("Confirmed", "Approved"):
			if cint(settings.cash_transfer_requires_receiver_confirmation) and not cint(self.receiver_confirmed):
				frappe.throw(_("Cash Transfer cannot be marked as Confirmed or Approved before the receiver confirms receipt."))
			if cint(self.receiver_confirmed) and not self.receiver_confirmed_at:
				self.receiver_confirmed_at = now_datetime()

	def on_update(self):
		self._sync_box_and_safe_totals()

	def _sync_box_and_safe_totals(self):
		if self.from_cash_box and frappe.db.exists("Fuel Cash Box", self.from_cash_box):
			total_out = frappe.db.sql(
				"""
				SELECT COALESCE(SUM(amount), 0)
				FROM `tabCash Transfer`
				WHERE from_cash_box = %s AND status IN ('Confirmed', 'Approved') AND receiver_confirmed = 1
				""",
				(self.from_cash_box,),
			)[0][0]
			box = frappe.get_doc("Fuel Cash Box", self.from_cash_box)
			box.cash_transfers_out = flt(total_out)
			box.save(ignore_permissions=True)

		if self.to_safe and frappe.db.exists("Fuel Station Safe", self.to_safe):
			total_in = frappe.db.sql(
				"""
				SELECT COALESCE(SUM(amount), 0)
				FROM `tabCash Transfer`
				WHERE to_safe = %s AND status IN ('Confirmed', 'Approved') AND receiver_confirmed = 1
				""",
				(self.to_safe,),
			)[0][0]
			safe = frappe.get_doc("Fuel Station Safe", self.to_safe)
			safe.cash_received_from_boxes = flt(total_in)
			safe.save(ignore_permissions=True)
