no_cache = 1


def get_context(context):
	from fuel_station.www.docs_utils import get_landing_context

	get_landing_context("guide", context)

