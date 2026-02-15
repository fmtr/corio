from fmtr.tools import environment_tools as env
from fmtr.tools.constants import Constants
from fmtr.tools.inspection_tools import get_call_path


def read() -> str:
    """

    Read a generic version file from the calling package path.

    """

    path = get_call_path(offset=2).parent / Constants.FILENAME_VERSION
    return read_path(path)


def read_path(path) -> str:
    """

    Read in version from specified path

    """
    from fmtr.tools.tools import Constants
    text = path.read_text(encoding=Constants.ENCODING).strip()

    text = get(text)
    return text


def get(text) -> str:
    """

    Optionally add dev build info to raw version string.

    """

    if not env.IS_DEV:
        return text

    import datetime
    from fmtr.tools.tools import Constants
    from fmtr.tools.version_tools import parse

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(Constants.DATETIME_SEMVER_BUILD_FORMAT)

    version = parse(text)
    version = version.bump_patch()
    version = version.replace(prerelease=Constants.DEVELOPMENT, build=timestamp)
    text = str(version)

    return text
