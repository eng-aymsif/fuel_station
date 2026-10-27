import frappe
from frappe.utils import cint


def extend_bootinfo(bootinfo):
	# يظهر زر دليل المستخدم في desk
	bootinfo.fuel_station_show_user_guide_button = True

