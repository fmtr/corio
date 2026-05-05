import builtins

from corio.import_ import MissingExtraMockModule
from corio.tools import MissingExtraError


_ORIGINAL_IMPORT = builtins.__import__


def _corio_import_hook(name, globals=None, locals=None, fromlist=(), level=0):
    caller_name = (globals or {}).get('__name__', '')
    try:
        return _ORIGINAL_IMPORT(name, globals, locals, fromlist, level)
    except ModuleNotFoundError as exception:
        if not caller_name.startswith('corio'):
            raise
        if caller_name == 'corio':
            raise
        extra=caller_name[len('corio.'):]
        raise MissingExtraError(extra) from exception


builtins.__import__ = _corio_import_hook

from corio.constants import Constants
from corio.path.path import Path, PackagePaths

try:
    from corio.logging import logger
except ImportError as exception:
    logger = MissingExtraMockModule('logging', exception)

try:
    from corio.path.path import Path
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
