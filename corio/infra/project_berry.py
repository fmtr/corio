import socket
from functools import cached_property

from corio.infra.project import ProjectBase
from corio.path import Path
from tappack.dm import manifest


class BerryPaths:
    def __init__(self, repo: Path):
        self.repo = Path(repo).resolve()
        manifests = sorted(self.repo.rglob(manifest.MANIFEST_FILENAME), key=str)
        if not manifests:
            raise ValueError(f'Berry project has no "{manifest.MANIFEST_FILENAME}" in {self.repo}.')
        if len(manifests) > 1:
            paths = ", ".join(str(path) for path in manifests)
            raise ValueError(f'Berry project has multiple manifests: {paths}.')

        self.manifest_path = manifests[0]
        self.path = self.manifest_path.parent
        self.manifest = manifest.Manifest.in_directory(self.path)
        self.metadata = self.manifest.metadata
        self.name = self.repo.name
        self.docs = self.repo / "docs"
        self.changelog = self.repo / "CHANGELOG.md"
        self.docs_changelog = self.docs / "changelog" / "changelog.md"
        self.tests = self.path / "tests"

    @property
    def package_name(self) -> str:
        return self.manifest.name or self.name


class ProjectBerry(ProjectBase):
    def __init__(
        self,
        path: Path,
        pinned: str | None = None,
        pre: bool | None = False,
    ):
        paths = BerryPaths(path)
        paths.metadata.version_obj
        super().__init__(paths, pinned=pinned, pre=pre)

    @cached_property
    def docs_port(self) -> int:
        with socket.socket() as server_socket:
            server_socket.bind(("0.0.0.0", 0))
            return server_socket.getsockname()[1]

    @cached_property
    def package(self) -> str:
        return self.paths.package_name

    @cached_property
    def releaser(self):
        from corio.infra.releaser_berry import ReleaserBerry

        return ReleaserBerry(self)
