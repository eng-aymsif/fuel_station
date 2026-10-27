import importlib
import pkgutil

# يستورد كل ملفات التخصيص تلقائياً ويجمع قوائم CUSTOMIZATIONS منها (نفس نمط mueen)
CUSTOMIZATIONS = []

for _importer, modname, _ispkg in pkgutil.iter_modules(__path__):
	if modname == "__init__":
		continue
	module = importlib.import_module(f"{__name__}.{modname}")
	if hasattr(module, "CUSTOMIZATIONS"):
		CUSTOMIZATIONS.extend(module.CUSTOMIZATIONS)

