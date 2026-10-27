import frappe
from frappe.model.document import Document
from frappe.utils import flt
from fuel_station.services.business_logic import create_purchase_receipt_from_delivery


class FuelDelivery(Document):
	def validate(self):
		if self.station and not self.company:
			self.company = frappe.db.get_value("Fuel Station", self.station, "company")
		if self.tank and frappe.db.exists("Fuel Tank", self.tank):
			tank_doc = frappe.get_doc("Fuel Tank", self.tank)
			if not self.warehouse:
				self.warehouse = tank_doc.warehouse
			if not self.item:
				self.item = tank_doc.item

		self.variance_quantity = flt(flt(self.received_quantity) - flt(self.document_quantity), 4)
		if not self.source_key and self.name:
			self.source_key = f"FDL-PR-{self.name}"

	def create_purchase_receipt(self, submit=True):
		return create_purchase_receipt_from_delivery(self, submit=submit)


@frappe.whitelist()
def make_purchase_receipt(delivery_name):
	"""Create or fetch an ERPNext Purchase Receipt from Fuel Delivery."""
	doc = frappe.get_doc("Fuel Delivery", delivery_name)
	if doc.purchase_receipt and frappe.db.exists("Purchase Receipt", doc.purchase_receipt):
		return doc.purchase_receipt

	pr = create_purchase_receipt_from_delivery(doc, submit=False)
	if pr:
		doc.db_set("purchase_receipt", pr.name)
		doc.db_set("status", "Received")
		return pr.name
	return None


@frappe.whitelist()
def make_purchase_invoice(delivery_name):
	"""Create an ERPNext Purchase Invoice from Fuel Delivery / Purchase Receipt."""
	doc = frappe.get_doc("Fuel Delivery", delivery_name)
	if doc.purchase_receipt:
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice as pr_make_pi
		pi = pr_make_pi(doc.purchase_receipt)
		pi.insert(ignore_permissions=True)
		return pi.name

	# Create directly
	pi = frappe.get_doc({
		"doctype": "Purchase Invoice",
		"supplier": doc.supplier,
		"company": doc.company,
		"bill_no": doc.supplier_document_no,
		"posting_date": doc.delivery_date or frappe.utils.nowdate(),
		"items": [{
			"item_code": doc.item,
			"qty": flt(doc.received_quantity or doc.document_quantity),
			"rate": flt(doc.rate),
			"uom": doc.uom or "Liter",
			"warehouse": doc.warehouse,
		}],
	})
	pi.insert(ignore_permissions=True)
	return pi.name
