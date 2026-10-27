import frappe
from frappe.model.document import Document
from frappe.utils import flt


class FuelReconciliationException(Document):
	def validate(self):
		self.difference = flt(flt(self.actual_quantity) - flt(self.expected_quantity), 4)
