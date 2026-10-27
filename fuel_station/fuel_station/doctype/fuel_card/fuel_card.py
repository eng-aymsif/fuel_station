import frappe
from frappe.model.document import Document
from frappe.utils import flt


class FuelCard(Document):
	def validate(self):
		if flt(self.quantity_limit) > 0:
			self.remaining_quantity = max(0.0, flt(self.quantity_limit) - flt(self.used_quantity))
		if flt(self.amount_limit) > 0:
			self.remaining_amount = max(0.0, flt(self.amount_limit) - flt(self.used_amount))

		if self.status == "Active":
			if (flt(self.quantity_limit) > 0 and self.remaining_quantity <= 0.0001) or (
				flt(self.amount_limit) > 0 and self.remaining_amount <= 0.01
			):
				self.status = "Exhausted"
