import click

from fuel_station.setup import before_uninstall as remove_fuel_station_customizations


def before_uninstall():
	try:
		print("Removing Fuel Station customizations...")
		remove_fuel_station_customizations()
		click.secho("Fuel Station customizations removed successfully!", fg="green")
	except Exception as e:
		click.secho("Fuel Station uninstall failed. Please check the logs.", fg="bright_red")
		raise e

