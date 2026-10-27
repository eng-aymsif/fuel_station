import secrets
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class FuelAuthorization(Document):
	def validate(self):
		if not self.qr_code:
			self.qr_code = "FAU-" + secrets.token_urlsafe(16)

		if flt(self.quantity_limit) > 0:
			self.remaining_quantity = max(0.0, flt(self.quantity_limit) - flt(self.used_quantity))
		if flt(self.amount_limit) > 0:
			self.remaining_amount = max(0.0, flt(self.amount_limit) - flt(self.used_amount))

		if self.status in ("Active", "Partially Used"):
			if (flt(self.quantity_limit) > 0 and self.remaining_quantity <= 0.0001) or (
				flt(self.amount_limit) > 0 and self.remaining_amount <= 0.01
			):
				self.status = "Fully Used"
			elif flt(self.used_quantity) > 0 or flt(self.used_amount) > 0:
				self.status = "Partially Used"
