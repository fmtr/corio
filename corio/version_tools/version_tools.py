from corio import environment_tools as env
from corio.inspection_tools import get_call_path
from corio.path_tools import PackagePaths, Path


def read() -> str:
    """

    Read version from the calling package metadata.

    """

    path_package = Path(get_call_path(offset=2).parent)
    paths = PackagePaths(path_package)
    text = paths.metadata.version
    return get(text)


def read_path(path) -> str:
    """

    Read in version from specified path

    """
    from corio import Constants
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
    from corio.tools import Constants
    from corio.version_tools import parse

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(Constants.DATETIME_SEMVER_BUILD_FORMAT)

    version = parse(text)
    version = version.bump_patch()
    version = version.replace(prerelease=Constants.DEVELOPMENT, build=timestamp)
    text = str(version)

    return text
