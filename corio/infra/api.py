import importlib

from corio import api as api
from corio.constants import Constants
from corio.infra import Project
from corio.infra.stack import ProductionPublic
from corio.paths import paths


class Api(api.Base):
    TITLE = f'Infrastructure API'
    URL_DOCS = '/'
    PORT = api.Base.PORT + paths.metadata.port

    def get_endpoints(self):
        endpoints = [
            api.Endpoint(method_http=self.app.get, path='/{name}/recreate', method=self.recreate),
            api.Endpoint(method_http=self.app.get, path='/{name}/release', method=self.release),
            api.Endpoint(method_http=self.app.get, path='/{name}/build', method=self.build),

        ]

        return endpoints

    def get_project(self, name: str, **kwargs) -> Project:  # todo allow pre-project override
        mod = importlib.import_module(f"{name}.project")
        mod = importlib.reload(mod)
        return mod.Project(**kwargs)

    async def recreate(self, name: str, extra: str = 'all', cache: bool = True):
        project = Project(name, extras=[extra])
        project.stacks.channel[Constants.DEVELOPMENT].recreate(cache=cache)

    async def build(self, name: str, extra: str = 'all', context: str = None, cache: bool = True):
        project = Project(name, context=context, extras=[extra])
        project.stacks.cls[ProductionPublic].build(cache=cache)

    async def release(
            self,
            name: str,
            pinned: str = None,
            build: bool = False,
            release: bool = True,
            cache: bool = True,
    ):
        project = Project(name, pinned=pinned)

        project.releaser.run(build=build, release=release, cache=cache)
