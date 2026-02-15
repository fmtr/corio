from corio.import_tools import MissingExtraMockModule

try:
    from corio.interface_tools.interface_tools import Base, update, progress
    from corio.interface_tools import controls
    from corio.interface_tools.context import Context
except ModuleNotFoundError as exception:
    Interface = update = progress = controls = MissingExtraMockModule('interface', exception)
