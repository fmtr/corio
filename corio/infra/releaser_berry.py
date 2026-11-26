from functools import cached_property

from corio import Path, env, https, iterator
from corio.infra.releaser import (
    Incrementor,
    IncrementorChangelog,
    IncrementorVersion,
    Release,
    ReleaseDocumentation,
    ReleaseGithub,
    Releaser,
)
from tappack import package as tappack_package


class IncrementorManifest(Incrementor):
    def __init__(self, parent):
        super().__init__(parent)
        self._original: bytes | None = None

    @property
    def path(self):
        return self.paths.manifest_path

    def apply(self):
        manifest = self.paths.manifest
        self._original = self.path.read_bytes()
        manifest.metadata.version = str(self.version)
        data = manifest.model_dump(mode="json", by_alias=True, exclude_unset=True)
        self.path.write_data(data)
        return self.path

    def rollback(self) -> None:
        if self._original is None:
            return

        self.path.write_bytes(self._original)
        self._original = None


class IncrementorTappack(Incrementor):
    def apply(self) -> Path:
        package = tappack_package.Package(
            self.paths.path,
            version=str(self.version),
        )
        self.asset = (f"{package.name}.tapp", package.build_archive().getvalue())
        return package.autoexec_path


class ReleaseShortlink(Release):
    URL = "https://fmtr.link/rest/v3/short-urls/{}"

    @property
    def token(self) -> str:
        return env.get("SHLINK_API_KEY")

    @property
    def asset_url(self) -> str:
        filename = f"{self.paths.package_name}.tapp"
        return f"{self.repo_url}/releases/download/{self.tag}/{filename}"

    def release(self) -> None:
        url = self.URL.format(self.paths.metadata.link_id)
        response = https.client.patch(
            url,
            json={"longUrl": self.asset_url},
            headers={
                "Content-Type": "application/json",
                "X-Api-Key": self.token,
            },
        )
        response.raise_for_status()


class ReleaserBerry(Releaser):
    @property
    def should_build_image(self) -> bool:
        return False

    @property
    def assets(self) -> dict[str, bytes]:
        incrementor = self.incrementors.cls[IncrementorTappack]
        name, content = incrementor.asset
        return {name: content}

    @cached_property
    def incrementors(self):
        return iterator.ilist[Incrementor](
            [
                IncrementorVersion(self),
                IncrementorManifest(self),
                IncrementorTappack(self),
                IncrementorChangelog(self),
            ]
        )

    @property
    def packagers(self):
        return []

    @property
    def releases(self):
        releases = [ReleaseGithub(self), ReleaseDocumentation(self)]
        if self.paths.metadata.link_id:
            releases.append(ReleaseShortlink(self))
        return releases
