import importlib

from corio import api_tools as api
from corio.constants import Constants
from corio.infrastructure_tools import Project
from corio.infrastructure_tools.stack import ProductionPublic


class Api(api.Base):
    TITLE = f'Infrastructure API'
    URL_DOCS = '/'
    PORT = 9100  # todo fix

    def get_endpoints(self):
        endpoints = [
            api.Endpoint(method_http=self.app.get, path='/{name}/recreate', method=self.recreate),
            api.Endpoint(method_http=self.app.get, path='/{name}/release', method=self.release),
            api.Endpoint(method_http=self.app.get, path='/{name}/build', method=self.build),

        ]

        return endpoints

    def get_project(self, name: str, **kwargs) -> Project:
        mod = importlib.import_module(f"{name}.project")
        mod = importlib.reload(mod)
        return mod.Project(**kwargs)

    async def recreate(self, name: str, extra: str = 'all'):
        project = Project(name, extras=[extra])
        project.stacks.channel[Constants.DEVELOPMENT].recreate()

    async def build(self, name: str, extra: str = 'all', context: str = None):
        project = Project(name, context=context, extras=[extra])
        project.stacks.cls[ProductionPublic].build()

    async def release(self, name: str, pinned: str = None):
        project = Project(name, pinned=pinned)

        project.releaser.run()


if __name__ == '__main__':
    Api.launch()
