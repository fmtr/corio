from corio.import_tools import MissingExtraMockModule

from corio.version_tools.version_tools import read, read_path, get

try:
    import semver

    semver = semver
    parse = semver.VersionInfo.parse
    Version = semver.Version

except ModuleNotFoundError as exception:
    Version = semver = parse = MissingExtraMockModule('version.dev', exception)
