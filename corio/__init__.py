from corio.hook import ImportHook, MissingExtraMockModule

IMPORT_HOOK = ImportHook()

from corio.constants import Constants
from corio.path.path import Path, PackagePaths
from corio.logging import logger


try:
    from corio.path.app import AppPaths
except ImportError as exception:
    AppPaths = MissingExtraMockModule('path.app', exception)

try:
    from corio.http import Client
except ImportError as exception:
    Client = MissingExtraMockModule('http', exception)

try:
    from corio.profiling import Timer
except ImportError as exception:
    Timer = MissingExtraMockModule('profiling', exception)

try:
    from corio.process import ContextProcess
except ImportError as exception:
    ContextProcess = MissingExtraMockModule('process', exception)

try:
    from corio.merging import merge
except ImportError as exception:
    merge = MissingExtraMockModule('merging', exception)


def get_version():
    """

    Defer reading version

    """
    from corio.paths import paths
    return paths.metadata.version
