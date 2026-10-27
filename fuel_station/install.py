import click
import frappe

from fuel_station.setup import after_install as setup_customizations


def after_install():
	try:
		print("Setting up Fuel Station customizations...")
		setup_customizations()

		from fuel_station.setup.company import setup_company
		from fuel_station.setup.install import setup_all

		# البيانات الأساسية ثم تهيئة كل شركة موجودة
		setup_all()
		for company in frappe.get_all("Company", pluck="name"):
			setup_company(company)
		click.secho("Fuel Station customizations installed successfully!", fg="green")
	except Exception as e:
		click.secho("Fuel Station installation failed. Please check the logs.", fg="bright_red")
		raise e
