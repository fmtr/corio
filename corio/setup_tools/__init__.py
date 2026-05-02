from corio.import_tools import MissingExtraMockModule

try:
    from setuptools import find_namespace_packages, find_packages, setup as setup_setuptools
except ModuleNotFoundError as exception:
    find_namespace_packages = find_packages = setup_setuptools = MissingExtraMockModule('setup', exception)
