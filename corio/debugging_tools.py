import dataclasses

from fmtr.tools import environment_tools as env
from fmtr.tools.constants import Constants

MASK = 'Starting debugger at tcp://{host}:{port}...'


@dataclasses.dataclass
class ShellDebug:
    """

    Debugging information for shell commands

    """
    command: str
    out: str
    err: str
    status: int

    # timestamp: datetime=dataclasses.field(default_factory=datetime.now)

    @classmethod
    def from_path(cls, path_str):
        """

        Get debug info from path

        """
        from fmtr.tools import Path
        path = Path(path_str).absolute()
        data = {field.name: (path / f'{field.name}.log').read_text().strip() for field in dataclasses.fields(cls)}
        self = cls(**data)
        return self

    @property
    def env(self):
        return env.get_dict()



def trace(is_debug=None, host=None, port=None, stdoutToServer=True, stderrToServer=True, **kwargs):
    """

    Connect to PyCharm debugger if enabled

    """
    if not is_debug:
        is_debug = env.get_bool(Constants.FMTR_REMOTE_DEBUG_ENABLED_KEY, False)

    if not is_debug:
        return

    if is_debug is True and not host:
        host = Constants.FMTR_REMOTE_DEBUG_HOST_DEFAULT

    host = host or env.get(Constants.FMTR_REMOTE_DEBUG_HOST_KEY, Constants.FMTR_REMOTE_DEBUG_HOST_DEFAULT)
    port = port or Constants.FMTR_REMOTE_DEBUG_PORT_DEFAULT

    from fmtr.tools import logger

    msg = MASK.format(host=host, port=port)
    logger.info(msg)

    import pydevd_pycharm
    pydevd_pycharm.settrace(host, port=port, stdoutToServer=stdoutToServer, stderrToServer=stderrToServer, **kwargs)


def debug_shell():
    """

    Starts a debug shell by initializing a `ShellDebug` object from a given path
    and enabling tracing with debug mode turned on.

    """
    import sys
    path_str = sys.argv[1]
    data = ShellDebug.from_path(path_str)
    trace(is_debug=True)
    data


if __name__ == "__main__":
    import sys

    sys.argv = [
        'test.py',
        './fmtr-debug/34e8d492-2f15-419a-8fcb-fe4fa0fa02bb',
    ]
    debug_shell()
