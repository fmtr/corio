from __future__ import annotations

from corio import api as api
from corio.infra.project import Project
from corio.paths import paths


class Api(api.Base):
    TITLE = 'Infrastructure API'
    URL_DOCS = '/'
    PORT = api.Base.PORT + paths.metadata.port

    @property
    def ENDPOINTS(self):
        """

        Infrastructure endpoint classes.

        """
        return [Release, PreVersion]


class Release(api.endpoint.API):
    """

    Run the project release workflow.

    """

    PATH = "/{name}/release"

    async def run(
            self,
            name: str,
            pinned: str = None,
            build: bool = False,
            release: bool = True,
    ):
        """

        Run a project's release workflow.

        """
        project = Project(name, pinned=pinned)
        project.releaser.run(build=build, release=release)


class PreVersion(api.endpoint.API):
    """

    Get the next pre-release version for a project.

    """

    PATH = "/{name}/pre-version"

    async def run(self, name: str):
        """

        Return the next pre-release version string, or None if already pre-release.

        """
        project = Project(name)
        version = project.versions.next_pre
        if version is None:
            return None
        return str(version)
