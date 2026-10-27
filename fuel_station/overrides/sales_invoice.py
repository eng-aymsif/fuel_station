import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice


class CustomSalesInvoice(SalesInvoice):
	def validate(self):
		super().validate()
		self.validate_fuel_invoice()

	def validate_fuel_invoice(self):
		if self.get("fuel_station") and self.get("source_key"):
			# Ensure uniqueness of source_key if set
			existing = frappe.db.get_value(
				"Sales Invoice",
				{"source_key": self.source_key, "name": ["!=", self.name or ""], "docstatus": ["!=", 2]},
				"name",
			)
			if existing:
				frappe.throw(_("Duplicate Fuel Sales Invoice detected for source key {0}: {1}").format(self.source_key, existing))

	def on_submit(self):
		super().on_submit()
		self.after_fuel_submit()

	def after_fuel_submit(self):
		if self.get("fuel_station"):
			from fuel_station.services.business_logic import log_audit_event
			log_audit_event(
				"Sales Invoice Submitted",
				"Sales Invoice",
				self.name,
				station=self.fuel_station,
				new_value=str(self.grand_total),
			)

	def on_cancel(self):
		super().on_cancel()
		self.after_fuel_cancel()

	def after_fuel_cancel(self):
		if self.get("fuel_station"):
			from fuel_station.services.business_logic import log_audit_event
			log_audit_event(
				"Sales Invoice Cancelled",
				"Sales Invoice",
				self.name,
				station=self.fuel_station,
				previous_value=str(self.grand_total),
			)

