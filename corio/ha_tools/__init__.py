from fmtr.tools.import_tools import MissingExtraMockModule

try:
    from fmtr.tools.ha_tools import core, supervisor, constants
    from fmtr.tools.ha_tools.utils import apply_addon_env

except ModuleNotFoundError as exception:
    core = supervisor = constants = apply_addon_env = MissingExtraMockModule('ha', exception)
