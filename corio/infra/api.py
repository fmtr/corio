
from __future__ import annotations

from corio import api as api
from corio.constants import Constants
from corio.infra import Project
from corio.infra.stack import ProductionPublic
from corio.paths import paths


class Api(api.Base):
    TITLE = f'Infrastructure API'
    URL_DOCS = '/'
    PORT = api.Base.PORT + paths.metadata.port

    @property
    def ENDPOINTS(self):
        """

        Infrastructure endpoint classes.

        """
        return [Recreate, Release, Build]


class Recreate(api.endpoint.API):
    """

    Recreate the development stack for a project.

    """

    PATH = "/{name}/recreate"

    async def run(self, name: str, extra: str = "all", cache: bool = True):
        """

        Recreate a project's development stack.

        """
        project = Project(name, extras=[extra])
        project.stacks.channel[Constants.DEVELOPMENT].recreate(cache=cache)


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
            cache: bool = True,
    ):
        """

        Run a project's release workflow.

        """
        project = Project(name, pinned=pinned)
        project.releaser.run(build=build, release=release, cache=cache)


class Build(api.endpoint.API):
    """

    Build the public production stack for a project.

    """

    PATH = "/{name}/build"

    async def run(self, name: str, extra: str = "all", context: str = None, cache: bool = True):
        """

        Build a project's public production stack.

        """
        project = Project(name, context=context, extras=[extra])
        project.stacks.cls[ProductionPublic].build(cache=cache)
