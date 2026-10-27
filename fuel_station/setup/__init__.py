from typing import ClassVar

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import (
	delete_property_setter,
	make_property_setter,
)


class BaseDoctypeCustomization:
	"""الأساس المشترك لتخصيص أي DocType قياسي (نفس نمط تطبيق mueen و hajzzy)."""

	doctype = None
	custom_fields: ClassVar[list] = []
	property_setters: ClassVar[list] = []
	# عند False يتجاوز install() خاصية field_order، بينما uninstall() يحذفها دائماً.
	apply_field_order = False

	def create_custom_fields(self):
		if not self.custom_fields:
			return
		for field in self.custom_fields:
			exists = frappe.db.exists("Custom Field", {"dt": self.doctype, "fieldname": field["fieldname"]})
			if not exists:
				create_custom_fields({self.doctype: [field]}, ignore_validate=True)
		frappe.clear_cache(doctype=self.doctype)

	def delete_custom_fields(self):
		if not self.custom_fields:
			return
		fieldnames = [f["fieldname"] for f in self.custom_fields]
		frappe.db.delete("Custom Field", {"dt": self.doctype, "fieldname": ("in", fieldnames)})
		frappe.clear_cache(doctype=self.doctype)

	def create_property_setters(self):
		if not self.property_setters:
			return
		for ps in self.property_setters:
			if ps["property"] == "field_order" and not self.apply_field_order:
				continue
			exists = frappe.db.exists(
				"Property Setter",
				{"doc_type": self.doctype, "field_name": ps.get("field_name"), "property": ps["property"]},
			)
			if not exists:
				make_property_setter(
					doctype=self.doctype,
					fieldname=ps.get("field_name"),
					property=ps["property"],
					value=ps["value"],
					property_type=ps["property_type"],
					for_doctype=ps.get("for_doctype", False),
					validate_fields_for_doctype=False,
				)
		frappe.clear_cache(doctype=self.doctype)

	def delete_property_setters(self):
		if not self.property_setters:
			return
		for ps in self.property_setters:
			delete_property_setter(
				doc_type=self.doctype, property=ps["property"], field_name=ps.get("field_name")
			)
		frappe.clear_cache(doctype=self.doctype)

	def install(self):
		self.create_custom_fields()
		self.create_property_setters()

	def uninstall(self):
		self.delete_property_setters()
		self.delete_custom_fields()


def after_install():
	from fuel_station.customizations import CUSTOMIZATIONS

	for customization in CUSTOMIZATIONS:
		customization.install()


def before_uninstall():
	from fuel_station.customizations import CUSTOMIZATIONS

	for customization in CUSTOMIZATIONS:
		customization.uninstall()
