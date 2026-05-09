from corio.version.version import read, read_path, get

import semver

semver = semver


class Version(semver.Version):
    @property
    def tag(self) -> str:
        return f"v{self}"


parse = Version.parse
