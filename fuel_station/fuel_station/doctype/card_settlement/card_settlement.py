import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate


class CardSettlement(Document):
	def validate(self):
		if self.station and not self.company:
			self.company = frappe.db.get_value("Fuel Station", self.station, "company")
		self.difference_amount = flt(flt(self.terminal_report_amount) - flt(self.station_card_amount), 2)

		if self.status == "Settled" and not self.journal_entry and flt(self.terminal_report_amount) > 0:
			prov = frappe.get_doc("Fuel Card Provider Settings", self.provider)
			station_doc = frappe.get_doc("Fuel Station", self.station)
			cc = station_doc.default_cost_center or frappe.db.get_value("Company", self.company, "cost_center")
			clearing_acc = prov.clearing_account
			bank_acc = prov.settlement_account
			fee_acc = prov.fee_account or station_doc.default_expense_account

			accounts = [
				{
					"account": bank_acc,
					"debit_in_account_currency": flt(self.bank_transferred_amount),
					"credit_in_account_currency": 0,
					"cost_center": cc,
				},
				{
					"account": clearing_acc,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": flt(self.bank_transferred_amount) + flt(self.provider_fee_amount),
					"cost_center": cc,
				},
			]
			if flt(self.provider_fee_amount) > 0 and fee_acc:
				accounts.append(
					{
						"account": fee_acc,
						"debit_in_account_currency": flt(self.provider_fee_amount),
						"credit_in_account_currency": 0,
						"cost_center": cc,
					}
				)
			je = frappe.get_doc(
				{
					"doctype": "Journal Entry",
					"voucher_type": "Journal Entry",
					"company": self.company,
					"posting_date": self.business_date or nowdate(),
					"user_remark": f"Card Settlement {self.name} for {self.provider}",
					"accounts": accounts,
				}
			)
			je.flags.ignore_permissions = True
			je.insert(ignore_permissions=True)
			je.submit()
			self.journal_entry = je.name
