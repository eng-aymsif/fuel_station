import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from fuel_station.services.business_logic import calculate_cash_residual


class FuelPumpReconciliation(Document):
	def validate(self):
		res = calculate_cash_residual(
			opening_reading=self.opening_reading,
			closing_reading=self.closing_reading,
			card_quantity=self.card_quantity,
			credit_quantity=self.credit_quantity,
			internal_quantity=self.internal_quantity,
			issue_order_quantity=self.issue_order_quantity,
			coupon_quantity=self.coupon_quantity,
			calibration_quantity=self.calibration_quantity,
			waste_quantity=self.waste_quantity,
		)
		self.meter_quantity = res.meter_quantity
		self.classified_quantity = res.classified_quantity
		self.cash_quantity = res.cash_quantity

		if flt(self.recorded_cash_events_quantity) > 0:
			self.variance_quantity = flt(self.cash_quantity - flt(self.recorded_cash_events_quantity), 4)
			self.variance_amount = flt(self.variance_quantity * flt(self.rate), 2)
