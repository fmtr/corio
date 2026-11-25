import io
import zipfile
from types import SimpleNamespace

import pytest

from corio import yml
from corio.entrypoint import DocServe, project_for_path
from corio.infra.api import project_for_name
from corio.infra.project_berry import ProjectBerry
from corio.infra.releaser import (
    IncrementorVersion,
    ReleaseDocumentation,
    ReleaseGithub,
)
from corio.infra.releaser_berry import (
    IncrementorManifest,
    IncrementorTappack,
    ReleaseShortlink,
)
from corio.path import Path
from corio.tests.release_fixture import BerryReleaseRepoFixture


@pytest.fixture
def berry_release_repo_factory(tmp_path):
    def make(**options):
        return BerryReleaseRepoFixture.create(Path(tmp_path), **options)

    return make


def test_project_factory_finds_berry_manifest_below_repository_root(
    berry_release_repo_factory,
):
    scenario = berry_release_repo_factory()

    project = project_for_path(scenario.path_repo, name="release-target")

    assert isinstance(project, ProjectBerry)
    assert project.paths.manifest_path == scenario.path_repo / "module" / "manifest.yml"
    assert project.paths.metadata.version == "2.5.1"


def test_api_entrypoint_selects_berry_projects(tmp_path, monkeypatch):
    project_root = tmp_path / "api_target"
    module = project_root / "module"
    module.mkdir(parents=True)
    (module / "manifest.yml").write_text(
        yml.to_yaml({
            "name": "api_bundle",
            "metadata": {"version": "3.7.2"},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "corio.infra.api.paths",
        SimpleNamespace(dev_repo=tmp_path),
    )

    project = project_for_name(project_root.name)

    assert isinstance(project, ProjectBerry)
    assert project.paths.manifest_path == module / "manifest.yml"


def test_project_factory_rejects_multiple_berry_manifests(berry_release_repo_factory):
    scenario = berry_release_repo_factory()
    nested_manifest = scenario.path_repo / "examples" / "manifest.yml"
    nested_manifest.parent.mkdir()
    nested_manifest.write_text(
        yml.to_yaml({"name": "secondary"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="multiple manifests"):
        project_for_path(scenario.path_repo, name="release-target")


def test_docserve_uses_berry_project_documentation_path(
    berry_release_repo_factory,
    monkeypatch,
):
    scenario = berry_release_repo_factory()
    served = []
    docs_port = scenario.project.docs_port
    assert 0 < docs_port < 65_536

    def serve(self, **options):
        served.append((self.paths.docs, options))
        return "documentation server"

    monkeypatch.setattr(ReleaseDocumentation, "serve", serve)
    monkeypatch.setattr(ProjectBerry, "docs_port", docs_port)
    monkeypatch.chdir(scenario.path_repo)

    assert DocServe().run() == "documentation server"
    assert served == [
        (
            scenario.path_repo / "docs",
            {"host": "0.0.0.0", "port": docs_port},
        )
    ]


def test_berry_increment_updates_manifest_and_builds_archive_in_memory(
    berry_release_repo_factory,
):
    scenario = berry_release_repo_factory()
    manifest_path = scenario.project.paths.manifest_path
    source_archive = scenario.path_repo / "release_bundle.tapp"
    original_manifest = manifest_path.read_data()
    expected_manifest = {
        **original_manifest,
        "metadata": {**original_manifest["metadata"], "version": "2.5.2"},
    }

    scenario.project.releaser.increment()

    assert manifest_path.read_data() == expected_manifest
    assert scenario.project.paths.metadata.version == "2.5.2"
    assert source_archive.exists() is False
    assert scenario.project.releaser.assets.keys() == {"release_bundle.tapp"}

    archive = io.BytesIO(scenario.project.releaser.assets["release_bundle.tapp"])
    with zipfile.ZipFile(archive) as package:
        assert package.read("version.be") == b"var VERSION = '2.5.2'\n"
        manifest_data = yml.from_yaml(package.read("manifest.yml").decode())
        assert manifest_data == expected_manifest

    assert scenario.project.releaser.incrementors.cls[IncrementorTappack].asset[0] == (
        "release_bundle.tapp"
    )


def test_manifest_incrementor_restores_original_file_on_rollback(
    berry_release_repo_factory,
):
    scenario = berry_release_repo_factory()
    releaser = scenario.project.releaser
    path = scenario.project.paths.manifest_path
    original = path.read_bytes()
    version_incrementor = releaser.incrementors.cls[IncrementorVersion]
    version_incrementor.apply()
    incrementor = IncrementorManifest(releaser)

    incrementor.apply()
    incrementor.rollback()
    version_incrementor.rollback()

    assert path.read_bytes() == original
    assert scenario.project.paths.manifest.metadata.version == "2.5.1"


def test_package_build_failure_rolls_back_manifest_version(
    berry_release_repo_factory,
    monkeypatch,
):
    scenario = berry_release_repo_factory()
    manifest_path = scenario.project.paths.manifest_path
    original_manifest = manifest_path.read_bytes()
    changelog_path = scenario.project.paths.docs_changelog

    def fail_build(self):
        raise RuntimeError("synthetic package failure")

    monkeypatch.setattr(IncrementorTappack, "apply", fail_build)

    with pytest.raises(RuntimeError, match="synthetic package failure"):
        scenario.project.releaser.increment()

    assert manifest_path.read_bytes() == original_manifest
    assert scenario.project.paths.metadata.version == "2.5.1"
    assert changelog_path.exists()


def test_github_release_uploads_assets_as_bytes(monkeypatch):
    calls = []

    class Response:
        def raise_for_status(self):
            return None

    class Client:
        def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return Response()

    monkeypatch.setattr("corio.infra.releaser.https.client", Client())
    release = ReleaseGithub(
        SimpleNamespace(
            assets={"release_bundle.tapp": b"synthetic archive bytes"},
            token="synthetic-token",
        )
    )

    release.upload_assets(
        {"upload_url": "https://uploads.invalid/releases/9/assets{?name,label}"}
    )

    assert calls == [
        (
            "https://uploads.invalid/releases/9/assets",
            {
                "params": {"name": "release_bundle.tapp"},
                "content": b"synthetic archive bytes",
                "headers": {
                    "Authorization": "Bearer synthetic-token",
                    "Accept": "application/vnd.github+json",
                    "Content-Type": "application/octet-stream",
                },
            },
        )
    ]


def test_berry_release_reuses_docs_and_updates_configured_shortlink(
    berry_release_repo_factory,
    monkeypatch,
):
    scenario = berry_release_repo_factory()
    releaser = scenario.project.releaser
    calls = []

    class Response:
        def raise_for_status(self):
            return None

    class Client:
        def patch(self, url, **kwargs):
            calls.append((url, kwargs))
            return Response()

    monkeypatch.setattr("corio.infra.releaser_berry.https.client", Client())
    monkeypatch.setattr(
        "corio.infra.releaser_berry.env.get",
        lambda name: "synthetic-token",
    )
    releases = releaser.releases
    shortlink = next(release for release in releases if isinstance(release, ReleaseShortlink))

    shortlink.release()

    assert any(isinstance(release, ReleaseDocumentation) for release in releases)
    assert calls == [
        (
            "https://fmtr.link/rest/v3/short-urls/synthetic-release-asset",
            {
                "json": {
                    "longUrl": "https://github.com/synthetic-org/release-target/releases/download/"
                    "v2.5.1/release_bundle.tapp"
                },
                "headers": {
                    "Content-Type": "application/json",
                    "X-Api-Key": "synthetic-token",
                },
            },
        )
    ]
