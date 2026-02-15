from fmtr.tools.import_tools import MissingExtraMockModule

try:
    from fmtr.tools.interface_tools.interface_tools import Base, update, progress
    from fmtr.tools.interface_tools import controls
    from fmtr.tools.interface_tools.context import Context
except ModuleNotFoundError as exception:
    Interface = update = progress = controls = MissingExtraMockModule('interface', exception)
