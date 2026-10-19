from functools import cached_property

from corio import version
from corio.infra.repository import Repository
from corio.inherit import Inherit
from corio.iterator import ilist
from corio.path import PackagePaths


class InvalidPinnedVersion(Exception):
    """A pinned release version contains a pre-release suffix."""


class Project:
    """

    Represents a canonical project with associated settings, runtime configuration, and paths.

    """

    def __init__(self, name=None, context='gex', channel='dev', extras=None, pinned=None, pre=False, path=None):
        self.paths = PackagePaths(path or PackagePaths.dev_repo / name)

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

        self.name = self.paths.name if name is None else name

        self.versions = Versions(self, pinned=pinned, pre=pre)

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
    def package(self):
        return self.paths.name

    @cached_property
    def repo_name(self):
        return f"{self.paths.metadata.org_github}/{self.paths.name}"

    @cached_property
    def repo_url(self):
        return f"https://github.com/{self.repo_name}"

    @cached_property
    def repo_api_url(self):
        return f"https://api.github.com/repos/{self.repo_name}"

    @cached_property
    def stacks(self):
        from corio.infra.stack import Production, Stack
        return ilist[Stack]([Production(self)])

    @cached_property
    def releaser(self):
        from corio.infra.releaser import Releaser
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

    def __init__(self, project: Project, pinned: str | None = None, pre: bool = False):
        super().__init__(project)
        self.pre_next = pre
        self.pinned = None
        if pinned:
            self.pinned = version.Version.parse(pinned)
            if self.pinned.prerelease:
                raise InvalidPinnedVersion(
                    f'Pinned version "{pinned}" must be a regular semantic version without a pre-release suffix. '
                    "Set pre=True to create a pre-release."
                )

    def get(self):
        return self.paths.metadata.version_obj

    @property
    def new(self):
        return self.get()

    @property
    def pre_current(self):
        return bool(self.new.prerelease)

    @property
    def next_pre(self):
        if self.pre_current:
            return None

        return self.new.bump_patch().replace(prerelease="alpha.0")

    @property
    def next(self):
        if self.pinned:
            if not self.pre_next:
                return self.pinned
            return self.pinned.replace(prerelease="alpha.0")

        if self.pre_current:
            return self.new.bump_prerelease()

        if self.pre_next:
            return self.next_pre

        return self.new.bump_patch()
