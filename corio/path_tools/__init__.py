from fmtr.tools.import_tools import MissingExtraMockModule
from fmtr.tools.path_tools.path_tools import Path, PackagePaths, root

try:
    from fmtr.tools.path_tools.app_path_tools import AppPaths
except ModuleNotFoundError as exception:
    AppPaths = MissingExtraMockModule('path.app', exception)

try:
    from fmtr.tools.path_tools.type_path_tools import guess
except ModuleNotFoundError as exception:
    guess = MissingExtraMockModule('path.type', exception)
