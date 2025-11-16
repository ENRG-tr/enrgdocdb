import importlib
import os
import pkgutil


def get_blueprints():
    blueprints = []
    current_dir = os.path.dirname(__file__)
    for _, module_name, _ in pkgutil.iter_modules([current_dir]):
        module = importlib.import_module(
            f".{module_name}", package="src.enrgdocdb.views"
        )
        if hasattr(module, "blueprint") and module.blueprint:
            blueprints.append(module.blueprint)

    return blueprints
