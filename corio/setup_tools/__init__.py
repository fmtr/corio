from corio.import_tools import MissingExtraMockModule

from corio.setup_tools.setup_tools import Setup, Dependencies, Tools

try:
    from setuptools import find_namespace_packages, find_packages, setup as setup_setuptools
except ModuleNotFoundError as exception:
    find_namespace_packages = find_packages = setup_setuptools = MissingExtraMockModule('setup', exception)
