from corio.import_tools import MissingExtraMockModule
from corio.path_tools.path_tools import Path, PackagePaths, root

try:
    from corio.path_tools.app_path_tools import AppPaths
except ModuleNotFoundError as exception:
    AppPaths = MissingExtraMockModule('path.app', exception)

try:
    from corio.path_tools.type_path_tools import guess
except ModuleNotFoundError as exception:
    guess = MissingExtraMockModule('path.type', exception)
