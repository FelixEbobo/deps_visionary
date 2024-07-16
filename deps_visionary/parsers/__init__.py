from inspect import isclass
from pkgutil import iter_modules
from pathlib import Path
from importlib import import_module

# iterate through the modules in the current package
# pylint: disable=invalid-name
package_dir = str(Path(__file__).resolve().parent)
for module_info in iter_modules([package_dir]):

    # import the module and iterate through its attributes
    module = import_module(f"{__name__}.{module_info.name}")
    for attribute_name in dir(module):
        attribute = getattr(module, attribute_name)

        if isclass(attribute):
            # Add the class to this package's variables
            globals()[attribute_name] = attribute
