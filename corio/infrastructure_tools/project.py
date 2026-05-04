from functools import cached_property

from corio import version_tools
from corio.infrastructure_tools.repository import Repository
from corio.inherit_tools import Inherit
from corio.iterator_tools import IndexList
from corio.path_tools import PackagePaths


class Project:
    """

    Represents a canonical project with associated settings, runtime configuration, and paths.

    """

    def __init__(self, name, context='ws', channel='dev', extras=None, pinned=None):
        self.paths = PackagePaths(PackagePaths.dev_repo / name)

        # project settings:
        self.services = self.paths.metadata.services
        self.scripts = self.paths.metadata.scripts
        self.base = self.paths.metadata.base
        self.port = self.paths.metadata.port
        self.entrypoint = self.paths.metadata.entrypoint

        # runtime:
        self.context = context
        self.channel = channel
        self.extras = extras or ['all']

        self.name = name

        self.versions = Versions(self, pinned=pinned)

    @cached_property
    def repo(self):
        return Repository(self.paths.repo, project=self)

    @property
    def version(self):

        return self.versions.new

    @property
    def tag(self):
        return f'v{self.version}'


    @cached_property
    def org(self):
        return self.paths.org

    @cached_property
    def package(self):
        return self.paths.name

    @cached_property
    def repo_name(self):
        return f"{self.paths.metadata.org_github}/{self.paths.name_ns}"

    @cached_property
    def repo_url(self):
        return f"https://github.com/{self.repo_name}"

    @cached_property
    def repo_api_url(self):
        return f"https://api.github.com/repos/{self.repo_name}"

    @cached_property
    def stacks(self):
        from corio.infrastructure_tools.stack import Stack, Development, ProductionPrivate, ProductionPublic
        classes = [Development, ProductionPrivate, ProductionPublic]
        stacks = IndexList[Stack](cls(self) for cls in classes)
        return stacks

    @cached_property
    def releaser(self):
        from corio.infrastructure_tools.releaser import Releaser
        return Releaser(self)

    @cached_property
    def name_components(self):
        return self.name.split('.')

    def join_name(self, sep):
        return sep.join(self.name_components)

    @cached_property
    def name_dash(self):
        return self.join_name('-')

    @cached_property
    def extras_str(self):
        return ','.join(self.extras)

    @cached_property
    def scripts_str(self):
        return ' && '.join(self.scripts)


class Versions(Inherit[Project]):

    def __init__(self, project: Project, pinned: str | None = None):
        super().__init__(project)
        self.old = self.get()

        self.pinned = None
        if pinned:
            self.pinned = version_tools.Version.parse(pinned)

    def get(self):
        return self.paths.metadata.version_obj

    @property
    def new(self):
        return self.get()

    @property
    def is_pre(self):
        return bool(self.new.prerelease)
