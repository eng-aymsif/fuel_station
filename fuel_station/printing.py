"""دوال مساعدة لطباعة نماذج محطة الوقود مسجلة في hooks.py (jinja.methods)."""

import base64
from io import BytesIO
import frappe
from frappe.utils import flt, fmt_money, escape_html
from markupsafe import Markup
import qrcode


def fuel_money(value, currency=None):
	"""تنسيق المبالغ المالية مع رمز العملة."""
	if value is None or value == "":
		return ""
	val = flt(value)
	currency = currency or frappe.db.get_default("currency") or "SAR"
	formatted = fmt_money(val, precision=2, currency=currency)
	return Markup(f'<span class="money-val" dir="ltr">{escape_html(formatted)}</span>')


def fuel_format_qty(value, uom="L"):
	"""تنسيق الكميات واللترات."""
	if value is None or value == "":
		return ""
	val = flt(value)
	formatted = f"{val:,.2f}"
	uom_str = uom or "L"
	return Markup(f'<span class="qty-val" dir="ltr">{formatted} {escape_html(uom_str)}</span>')


def fuel_qr_code(data, size=4):
	"""توليد باركود QR كصورة base64 مدمجة في HTML بدون الحاجة لخدمات خارجية."""
	if not data:
		return ""
	try:
		qr = qrcode.QRCode(
			version=1,
			error_correction=qrcode.constants.ERROR_CORRECT_M,
			box_size=size,
			border=1,
		)
		qr.add_data(str(data))
		qr.make(fit=True)
		img = qr.make_image(fill_color="#111827", back_color="#ffffff")
		buf = BytesIO()
		img.save(buf, format="PNG")
		b64 = base64.b64encode(buf.getvalue()).decode("ascii")
		return Markup(f'<img class="fuel-qr-img" src="data:image/png;base64,{b64}" alt="QR" width="110" height="110" />')
	except Exception:
		return ""


def fuel_zatca_qr(doc):
	"""توليد QR متوافق مع الفاتورة الضريبية الإلكترونية المبسطة."""
	seller_name = doc.get("company") or frappe.db.get_default("company") or "Fuel Station"
	tax_id = doc.get("tax_id") or frappe.db.get_value("Company", seller_name, "tax_id") or "300000000000003"
	timestamp = f"{doc.get('posting_date') or ''}T{doc.get('posting_time') or '00:00:00'}Z"
	total = f"{flt(doc.get('grand_total')):0.2f}"
	tax = f"{flt(doc.get('total_taxes_and_charges')):0.2f}"

	# TLV encoding for ZATCA
	def to_tlv(tag, val):
		b = val.encode("utf-8")
		return bytes([tag, len(b)]) + b

	try:
		tlv_bytes = (
			to_tlv(1, seller_name)
			+ to_tlv(2, tax_id)
			+ to_tlv(3, timestamp)
			+ to_tlv(4, total)
			+ to_tlv(5, tax)
		)
		b64_qr = base64.b64encode(tlv_bytes).decode("ascii")
		return fuel_qr_code(b64_qr, size=3)
	except Exception:
		return fuel_qr_code(doc.name)


def fuel_station_info(station_name):
	"""إرجاع بيانات المحطة للطباعة."""
	if not station_name or not frappe.db.exists("Fuel Station", station_name):
		return frappe._dict()
	return frappe.get_cached_doc("Fuel Station", station_name)


def fuel_bidi(val):
	if val is None:
		return ""
	return Markup(f'<span dir="auto">{escape_html(str(val))}</span>')
