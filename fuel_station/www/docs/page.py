# /docs/<slug> يُوجَّه إلى هذه الصفحة عبر website_route_rules في hooks.py
import frappe

no_cache = 1


def get_context(context):
	from fuel_station.www.docs_utils import get_doc_context

	get_doc_context("guide", frappe.form_dict.get("slug"), context)

