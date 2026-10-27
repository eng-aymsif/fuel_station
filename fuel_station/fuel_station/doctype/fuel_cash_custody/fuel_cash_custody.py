import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime


class FuelCashCustody(Document):
	def validate(self):
		self.expected_amount = flt(
			flt(self.opening_amount)
			+ flt(self.cash_sales)
			+ flt(self.approved_receipts)
			- flt(self.approved_expenses),
			2,
		)
		if self.denominations:
			total = 0.0
			for row in self.denominations:
				row.subtotal = flt(flt(row.banknote_or_coin) * cint(row.quantity), 2)
				if not row.counted_at:
					row.counted_at = now_datetime()
				total += row.subtotal
			self.actual_amount = flt(total, 2)
		self.variance_amount = flt(flt(self.actual_amount) - flt(self.expected_amount), 2)
