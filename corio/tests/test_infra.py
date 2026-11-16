import asyncio
from types import SimpleNamespace
from typing import get_args, get_type_hints

import pygit2 as vcs
import pytest
from packaging.requirements import Requirement

from corio import entrypoint
from corio import strings
from corio import version
from corio.infra.api import DocumentationRelease, PreVersion, ProjectName, Release
from corio.infra.incrementor_pyproject import IncrementorPyproject, GeneratorTestEnvs
from corio.infra.project import InvalidPinnedVersion, Versions
from corio.infra.releaser import (
    Incrementor,
    IncrementorChangelog,
    IncrementorHomeAssistantAddon,
    IncrementorVersion,
    ReleaseGithub,
    Releaser,
    ReleaseTestsFailed,
    Tester as ReleaserTester,
)
from corio.infra.repository import Repository
from corio.path import Path
from corio.paths import paths
from corio.tests.release_fixture import ReleaseRepoFixture


def _write_editable_repo(path_repo: Path, name: str, version: str) -> None:
    (path_repo / "pyproject.toml").write_text("", encoding="utf-8")
    path_package = path_repo / name
    path_package.mkdir(parents=True)
    (path_package / "pyproject.package.toml").write_text(
        f'[tool.corio.metadata]\nversion = "{version}"\n',
        encoding="utf-8",
    )


@pytest.fixture
def release_repo_factory(tmp_path):
    def make(**options):
        return ReleaseRepoFixture.create(Path(tmp_path), **options)

    return make


def _make_incrementor(
    path_repo: Path,
    pre_current: bool = False,
    test_envs: bool = True,
    editables: tuple[str, ...] = (),
) -> IncrementorPyproject:
    path_package = path_repo / "corio"
    path_package.mkdir(parents=True, exist_ok=True)
    path_tests = path_repo / "corio" / "tests"
    path_tests.mkdir(parents=True, exist_ok=True)
    parent = SimpleNamespace(
        paths=SimpleNamespace(
            repo=path_repo,
            pyproject_repo=path_repo / "pyproject.toml",
            name="corio",
            path=path_package,
            tests=path_tests,
            metadata=SimpleNamespace(
                test_envs=test_envs,
                test_pass_env=[],
                editables=list(editables),
            ),
        ),
        versions=SimpleNamespace(pre_current=pre_current),
    )
    return IncrementorPyproject(parent)


def test_pyproject_is_restored_when_tester_incrementor_fails(tmp_path, monkeypatch):
    path_repo = Path(tmp_path)
    path_pyproject = path_repo / "pyproject.toml"
    original = b"# preserved formatting\n[project]\nname = 'sample'\n"
    path_pyproject.write_bytes(original)
    pyproject_incrementor = IncrementorPyproject(SimpleNamespace(
        paths=SimpleNamespace(pyproject_repo=path_pyproject),
    ))
    failure = ReleaseTestsFailed(1, "synthetic test failure")

    def fail_tests(self):
        raise failure

    monkeypatch.setattr(
        IncrementorPyproject,
        "_enrich_toml",
        lambda self, data: {"generated": True},
    )
    monkeypatch.setattr(ReleaserTester, "run", fail_tests)

    releaser = Releaser(SimpleNamespace(
        paths=SimpleNamespace(repo=path_repo),
        repo=SimpleNamespace(origin=SimpleNamespace(url="https://example.invalid/repo")),
    ))
    releaser.incrementors = [pyproject_incrementor, ReleaserTester(releaser)]

    with pytest.raises(ReleaseTestsFailed) as result:
        releaser.increment()

    assert result.value is failure
    assert path_pyproject.read_bytes() == original


def test_release_github_body_without_previous_version(tmp_path):
    changelog = Path(tmp_path / "docs" / "changelog" / "changelog.md")
    parent = SimpleNamespace(
        incrementors=SimpleNamespace(
            cls={IncrementorChangelog: SimpleNamespace(dest=changelog)},
        ),
        repo=SimpleNamespace(
            get_most_recent_release_tag=lambda **kwargs: None,
        ),
        version="0.0.1-alpha.1",
        versions=SimpleNamespace(pre_current=True),
    )

    release = ReleaseGithub(parent)

    assert release.body == "[No Previous Version]"


def test_pin_editables_and_flatten_dependencies(tmp_path):
    path_main_repo = Path(tmp_path / "corio")
    path_main_repo.mkdir(parents=True)

    path_editable_b_repo = Path(tmp_path / "editable_b")
    path_editable_b_repo.mkdir(parents=True)
    _write_editable_repo(path_editable_b_repo, name="editable_b", version="1.2.3")

    incrementor = _make_incrementor(path_main_repo, editables=("editable_b",))

    assert incrementor._pin_editable("editable_b") == "editable_b~=1.2.3"
    assert incrementor._pin_editable("requests") == "requests"

    install, extras = incrementor._flatten_dependencies(
        {
            "install": ["editable_b", "requests"],
            "dev": ["editable_b"],
        }
    )

    assert install == ["editable_b", "requests"]
    assert extras == {"dev": ["editable_b"], "all": ["editable_b"]}


def test_pin_editables_resolves_metadata_editable_sibling(tmp_path):
    path_main_repo = Path(tmp_path / "app")
    path_main_repo.mkdir(parents=True)

    path_corio_repo = Path(tmp_path / "corio")
    path_corio_repo.mkdir(parents=True)
    _write_editable_repo(path_corio_repo, name="corio", version="1.2.3")

    incrementor = _make_incrementor(path_main_repo, editables=("corio",))
    assert incrementor._pin_editable("corio") == "corio~=1.2.3"


def test_infra_dispatches_cli_subcommands():
    assert issubclass(entrypoint.Infra, entrypoint.sets.SubCommand)
    assert entrypoint.Infra.run is entrypoint.sets.SubCommand.run


def test_releaser_executes_tester_before_release_metadata(tmp_path, monkeypatch):
    events = []

    class _Index:
        def write(self):
            pass

    incrementor_events = [
        (IncrementorVersion, "version"),
        (IncrementorPyproject, "pyproject"),
        (ReleaserTester, "tests"),
        (IncrementorHomeAssistantAddon, "addon"),
        (IncrementorChangelog, "changelog"),
    ]
    for incrementor, event in incrementor_events:
        monkeypatch.setattr(
            incrementor,
            "apply",
            lambda self, event=event: events.append(event),
        )

    releaser = Releaser(SimpleNamespace(
        paths=SimpleNamespace(repo=Path(tmp_path)),
        repo=SimpleNamespace(origin=SimpleNamespace(url="https://example.invalid/repo")),
    ))
    monkeypatch.setattr(Releaser, "index", property(lambda self: _Index()))

    releaser.increment()

    assert issubclass(ReleaserTester, Incrementor)
    assert events == ["version", "pyproject", "tests", "addon", "changelog"]


@pytest.mark.parametrize(
    ("with_changelog", "with_addon"),
    [(True, True), (True, False), (False, True), (False, False)],
)
@pytest.mark.parametrize(
    ("current_version", "pre", "expected_version", "is_prerelease"),
    [
        ("8.3.1", False, "8.3.2", False),
        ("8.3.1", True, "8.3.2-alpha.0", True),
        ("8.3.2-alpha.0", True, "8.3.2-alpha.1", True),
        ("8.3.2-alpha.0", False, "8.3.2", False),
    ],
)
def test_release_updates_real_repo_history_and_files(
    release_repo_factory,
    monkeypatch,
    current_version,
    pre,
    expected_version,
    is_prerelease,
    with_changelog,
    with_addon,
):
    scenario = release_repo_factory(
        current_version=current_version,
        pre=pre,
        with_changelog=with_changelog,
        with_addon=with_addon,
    )
    test_runs = []

    def pass_tests(self):
        test_runs.append(self.paths.repo)
        return 0

    monkeypatch.setattr(ReleaserTester, "run_subprocess", pass_tests)
    path_draft = scenario.path_repo / "docs" / "changelog" / "changelog.md"
    draft_before = path_draft.read_bytes() if path_draft.exists() else None

    scenario.project.releaser.run(release=False)

    data = (scenario.path_repo / "pyproject.toml").read_toml()
    assert data["project"]["version"] == expected_version
    assert data["tool"]["corio"]["metadata"]["version"] == expected_version
    assert data["project"]["dependencies"] == ["editable_support~=2.6.4"]
    assert data["tool"]["tox"]["env_list"] == ["release_target"]
    assert data["tool"]["uv"]["sources"]["editable_support"] == {
        "path": "../editable_support",
        "editable": True,
    }
    if is_prerelease:
        assert data["tool"]["uv"]["prerelease"] == "if-necessary"
        assert data["tool"]["uv"]["prerelease-package"] == {"editable_support": "if-necessary"}
    else:
        assert "prerelease" not in data["tool"]["uv"]

    assert test_runs == [scenario.path_repo]
    path_addon = scenario.path_repo / "ha" / "addon" / "config.yaml"
    if with_addon and not is_prerelease:
        assert path_addon.read_yaml()["version"] == expected_version
    elif with_addon:
        assert path_addon.read_yaml()["version"] == current_version
    else:
        assert not path_addon.exists()

    path_latest = scenario.path_repo / "CHANGELOG.md"
    path_versioned = scenario.path_repo / "docs" / "changelog" / f"{expected_version}.md"
    if not with_changelog:
        assert not path_latest.exists()
        assert not path_draft.exists()
    elif is_prerelease:
        assert path_draft.read_bytes() == draft_before
        assert not path_versioned.exists()
        assert str(path_latest.readlink()) == f"docs/changelog/{current_version}.md"
    else:
        assert not path_draft.exists()
        assert path_versioned.read_bytes() == draft_before
        assert str(path_latest.readlink()) == f"docs/changelog/{expected_version}.md"

    repository = scenario.project.repo
    main_commit = repository.lookup_reference("refs/heads/main").peel(vcs.Commit)
    release_commit = repository.lookup_reference("refs/heads/release").peel(vcs.Commit)
    assert str(main_commit.parent_ids[0]) == scenario.main_head
    assert release_commit.id == main_commit.id
    assert repository.merge_base(main_commit.id, vcs.Oid(hex=scenario.release_head)) == vcs.Oid(
        hex=scenario.release_head
    )
    assert repository.tags.all == scenario.tags | {f"v{expected_version}"}
    assert repository.status() == {}

    remote = vcs.Repository(str(scenario.path_remote))
    assert remote.lookup_reference("refs/heads/main").target == main_commit.id
    assert remote.lookup_reference("refs/heads/release").target == main_commit.id
    remote_tag = remote.lookup_reference(f"refs/tags/v{expected_version}").peel(vcs.Commit)
    assert remote_tag.id == main_commit.id


def test_stable_release_indexes_changelog_created_after_main_commit(
    release_repo_factory,
    monkeypatch,
):
    scenario = release_repo_factory(with_changelog=False)
    path_draft = scenario.path_repo / "docs" / "changelog" / "changelog.md"
    path_draft.parent.mkdir(parents=True)
    changelog = "- Added a synthetic release note.\n"
    path_draft.write_text(changelog, encoding="utf-8")

    monkeypatch.setattr(ReleaserTester, "run_subprocess", lambda self: 0)

    scenario.project.releaser.run(release=False)

    path_versioned = scenario.path_repo / "docs" / "changelog" / "8.3.2.md"
    assert path_versioned.read_text(encoding="utf-8") == changelog
    assert not path_draft.exists()
    assert str((scenario.path_repo / "CHANGELOG.md").readlink()) == "docs/changelog/8.3.2.md"


@pytest.mark.parametrize("pre", [False, True])
def test_release_test_failure_restores_pyproject_and_does_not_publish(
    release_repo_factory,
    monkeypatch,
    pre,
):
    scenario = release_repo_factory(pre=pre)
    failure = ReleaseTestsFailed(1, "synthetic test failure")
    path_pyproject = scenario.path_repo / "pyproject.toml"
    pyproject_before = path_pyproject.read_bytes()
    path_addon = scenario.path_repo / "ha" / "addon" / "config.yaml"
    addon_before = path_addon.read_bytes()
    path_draft = scenario.path_repo / "docs" / "changelog" / "changelog.md"
    draft_before = path_draft.read_bytes()
    path_latest = scenario.path_repo / "CHANGELOG.md"
    latest_target = str(path_latest.readlink())
    failed_version = "8.3.2-alpha.0" if pre else "8.3.2"

    def fail_tests(self):
        raise failure

    monkeypatch.setattr(ReleaserTester, "run_subprocess", fail_tests)

    with pytest.raises(ReleaseTestsFailed) as result:
        scenario.project.releaser.run(release=False)

    repository = scenario.project.repo
    remote = vcs.Repository(str(scenario.path_remote))
    assert result.value is failure
    assert path_pyproject.read_bytes() == pyproject_before
    assert path_addon.read_bytes() == addon_before
    assert path_draft.read_bytes() == draft_before
    assert str(path_latest.readlink()) == latest_target
    assert not (scenario.path_repo / "docs" / "changelog" / f"{failed_version}.md").exists()
    assert str(repository.lookup_reference("refs/heads/main").target) == scenario.main_head
    assert str(repository.lookup_reference("refs/heads/release").target) == scenario.release_head
    assert repository.tags.all == scenario.tags
    assert str(remote.lookup_reference("refs/heads/main").target) == scenario.main_head
    assert str(remote.lookup_reference("refs/heads/release").target) == scenario.release_head
    remote_tags = {
        reference.removeprefix("refs/tags/")
        for reference in remote.references
        if reference.startswith("refs/tags/")
    }
    assert remote_tags == scenario.tags
    assert repository.status() == {}


def test_release_rejects_prerelease_editable_dependency_without_changes(
    release_repo_factory,
):
    scenario = release_repo_factory(editable_version="2.6.5-alpha.1")
    path_pyproject = scenario.path_repo / "pyproject.toml"
    pyproject_before = path_pyproject.read_bytes()

    with pytest.raises(ValueError):
        scenario.project.releaser.run(release=False)

    assert path_pyproject.read_bytes() == pyproject_before
    assert scenario.project.repo.status() == {}
    assert str(scenario.project.repo.lookup_reference("refs/heads/main").target) == scenario.main_head
    assert scenario.project.repo.tags.all == scenario.tags
    editable = vcs.Repository(str(scenario.path_editable))
    assert "v2.6.5-alpha.1" in {reference.removeprefix("refs/tags/") for reference in editable.references}


def test_prerelease_requires_a_tag_for_the_current_version(release_repo_factory):
    scenario = release_repo_factory(pre=True, tag_current=False)
    path_pyproject = scenario.path_repo / "pyproject.toml"
    pyproject_before = path_pyproject.read_bytes()

    with pytest.raises(RuntimeError):
        scenario.project.releaser.run(release=False)

    assert path_pyproject.read_bytes() == pyproject_before
    assert scenario.project.repo.status() == {}
    assert str(scenario.project.repo.lookup_reference("refs/heads/main").target) == scenario.main_head
    assert scenario.project.repo.tags.all == scenario.tags


def test_release_rejects_an_existing_pinned_tag_without_changes(release_repo_factory):
    scenario = release_repo_factory(pinned="8.3.2", tag_next=True)
    path_pyproject = scenario.path_repo / "pyproject.toml"
    pyproject_before = path_pyproject.read_bytes()

    with pytest.raises(RuntimeError):
        scenario.project.releaser.run(release=False)

    assert path_pyproject.read_bytes() == pyproject_before
    assert scenario.project.repo.status() == {}
    assert str(scenario.project.repo.lookup_reference("refs/heads/main").target) == scenario.main_head
    assert scenario.project.repo.tags.all == scenario.tags


def test_release_without_tests_skips_tox_and_still_releases(release_repo_factory, monkeypatch):
    scenario = release_repo_factory(with_tests=False)
    monkeypatch.setattr(
        ReleaserTester,
        "run_subprocess",
        lambda self: pytest.fail("No test modules should invoke tox."),
    )

    scenario.project.releaser.run(release=False)

    assert (scenario.path_repo / "pyproject.toml").read_toml()["project"]["version"] == "8.3.2"
    assert scenario.project.repo.tags.all == scenario.tags | {"v8.3.2"}


def test_generate_editable_uv_sources_and_compat_from_metadata(tmp_path):
    path_main_repo = Path(tmp_path / "app")
    path_main_repo.mkdir(parents=True)
    incrementor = _make_incrementor(path_main_repo, editables=("corio", "editable_a"))
    data = {
        "tool": {
            "uv": {
                "sources": {
                    "corio": {"path": "old-corio", "editable": True},
                    "stale": {"path": "../stale", "editable": True},
                    "remote": {"index": "private"},
                },
                "config-settings-package": {
                    "corio": {"editable_mode": "strict", "other": "keep"},
                    "stale": {"editable_mode": "compat", "other": "keep"},
                    "remote": {"setting": "keep"},
                },
            }
        }
    }

    incrementor._generate_editables(data)

    assert data["tool"]["uv"]["sources"] == {
        "corio": {"path": "../corio", "editable": True},
        "editable_a": {"path": "../editable_a", "editable": True},
        "remote": {"index": "private"},
    }
    assert data["tool"]["uv"]["config-settings-package"] == {
        "corio": {"editable_mode": "compat", "other": "keep"},
        "stale": {"other": "keep"},
        "editable_a": {"editable_mode": "compat"},
        "remote": {"setting": "keep"},
    }


def test_generate_prerelease_uv_policies_for_editables(tmp_path):
    path_main_repo = Path(tmp_path / "app")
    path_main_repo.mkdir(parents=True)
    incrementor = _make_incrementor(
        path_main_repo,
        pre_current=True,
        editables=("corio", "editable_a"),
    )
    data = {"tool": {"uv": {"prerelease-package": {"external": "allow"}}}}

    incrementor._generate_editables(data)

    assert data["tool"]["uv"]["prerelease"] == "if-necessary"
    assert data["tool"]["uv"]["prerelease-package"] == {
        "corio": "if-necessary",
        "editable_a": "if-necessary",
    }


def test_generate_prerelease_uv_policies_are_removed_for_stable_versions(tmp_path):
    path_main_repo = Path(tmp_path / "app")
    path_main_repo.mkdir(parents=True)
    incrementor = _make_incrementor(path_main_repo, editables=("corio",))
    data = {
        "tool": {
            "uv": {
                "prerelease": "if-necessary",
                "prerelease-package": {
                    "corio": "if-necessary",
                    "obsolete": "if-necessary",
                    "external": "allow",
                },
                "sources": {
                    "corio": {"path": "../corio", "editable": True},
                    "obsolete": {"path": "../obsolete", "editable": True},
                },
            }
        }
    }

    incrementor._generate_editables(data)

    assert "prerelease" not in data["tool"]["uv"]
    assert "prerelease-package" not in data["tool"]["uv"]
    assert data["tool"]["uv"]["sources"] == {
        "corio": {"path": "../corio", "editable": True},
    }


def test_pin_editables_preserves_extras_and_skips_existing_specifiers(tmp_path):
    path_main_repo = Path(tmp_path / "corio")
    path_main_repo.mkdir(parents=True)

    path_editable_b_repo = Path(tmp_path / "editable_b")
    path_editable_b_repo.mkdir(parents=True)
    _write_editable_repo(path_editable_b_repo, name="editable_b", version="1.2.3")

    incrementor = _make_incrementor(path_main_repo, editables=("editable_b",))

    dep = incrementor._pin_editable("editable_b[dev,logging,sets,yaml,debug,caching,api,mqtt]")
    req = Requirement(dep)
    assert req.name == "editable_b"
    assert req.extras == {"dev", "logging", "sets", "yaml", "debug", "caching", "api", "mqtt"}
    assert str(req.specifier) == "~=1.2.3"

    assert incrementor._pin_editable("editable_b==1.0.0") == "editable_b==1.0.0"
    assert incrementor._pin_editable("editable_b~=1.0.0") == "editable_b~=1.2.3"
    assert incrementor._pin_editable("editable_b>=1.0.0") == "editable_b>=1.0.0"


def test_pin_editables_raises_on_prerelease_when_current_is_release(tmp_path):
    path_main_repo = Path(tmp_path / "corio")
    path_main_repo.mkdir(parents=True)

    path_editable_b_repo = Path(tmp_path / "editable_b")
    path_editable_b_repo.mkdir(parents=True)
    _write_editable_repo(path_editable_b_repo, name="editable_b", version="1.2.3-rc.1")

    incrementor = _make_incrementor(path_main_repo, pre_current=False, editables=("editable_b",))

    try:
        _ = incrementor.editables
    except ValueError as exception:
        assert 'Editable dependency "editable_b" is pre-release' in str(exception)
    else:
        raise AssertionError("Expected ValueError for prerelease editable dependency")


def test_pin_editables_allows_prerelease_when_current_pre_currentrelease(tmp_path):
    path_main_repo = Path(tmp_path / "corio")
    path_main_repo.mkdir(parents=True)

    path_editable_b_repo = Path(tmp_path / "editable_b")
    path_editable_b_repo.mkdir(parents=True)
    _write_editable_repo(path_editable_b_repo, name="editable_b", version="1.2.3-rc.1")

    incrementor = _make_incrementor(path_main_repo, pre_current=True, editables=("editable_b",))

    assert incrementor._pin_editable("editable_b") == "editable_b~=1.2.3-rc.1"


def test_versions_next_pre_uses_alpha_dot_zero():
    parent = SimpleNamespace(
        paths=SimpleNamespace(
            metadata=SimpleNamespace(version_obj=version.parse("0.1.0")),
        )
    )

    assert str(Versions(parent).next_pre) == "0.1.1-alpha.0"


def test_versions_next_pre_returns_none_for_prerelease():
    parent = SimpleNamespace(
        paths=SimpleNamespace(
            metadata=SimpleNamespace(version_obj=version.parse("0.1.0-alpha.1")),
        )
    )

    assert Versions(parent).next_pre is None


@pytest.mark.parametrize(
    ("current", "pinned", "pre", "expected"),
    [
        ("2.2.0", None, False, "2.2.1"),
        ("2.2.0", None, True, "2.2.1-alpha.0"),
        ("2.2.0", None, None, "2.2.1"),
        ("2.2.0", "3.0.0", False, "3.0.0"),
        ("2.2.0", "3.0.0", True, "3.0.0-alpha.0"),
        ("2.2.0", "3.0.0", None, "3.0.0"),
        ("2.2.0-alpha.1", None, False, "2.2.0"),
        ("2.2.0-alpha.1", None, True, "2.2.0-alpha.2"),
        ("2.2.0-alpha.1", None, None, "2.2.0-alpha.2"),
        ("2.2.0-alpha.1", "3.0.0", False, "3.0.0"),
        ("2.2.0-alpha.1", "3.0.0", True, "3.0.0-alpha.0"),
        ("2.2.0-alpha.1", "3.0.0", None, "3.0.0-alpha.0"),
    ],
)
def test_versions_next_covers_release_version_matrix(current, pinned, pre, expected):
    parent = SimpleNamespace(
        paths=SimpleNamespace(
            metadata=SimpleNamespace(version_obj=version.parse(current)),
        )
    )

    assert str(Versions(parent, pinned=pinned, pre=pre).next) == expected


def test_versions_rejects_pinned_prerelease():
    parent = SimpleNamespace(
        paths=SimpleNamespace(
            metadata=SimpleNamespace(version_obj=version.parse("2.2.0")),
        )
    )

    with pytest.raises(InvalidPinnedVersion):
        Versions(parent, pinned="3.0.0-alpha.1")


def test_incrementor_version_writes_stable_version_from_prerelease():
    metadata = SimpleNamespace(
        version="2.2.0-alpha.1",
        version_obj=version.parse("2.2.0-alpha.1"),
    )
    parent = SimpleNamespace(
        paths=SimpleNamespace(name="corio", metadata=metadata),
        repo=SimpleNamespace(tags=SimpleNamespace(all={"v2.2.0-alpha.1"})),
    )
    parent.versions = Versions(parent)

    IncrementorVersion(parent).apply()

    assert metadata.version == "2.2.0"


def test_incrementor_version_writes_numeric_prerelease():
    metadata = SimpleNamespace(
        version="2.2.0-alpha.1",
        version_obj=version.parse("2.2.0-alpha.1"),
    )
    parent = SimpleNamespace(
        paths=SimpleNamespace(name="corio", metadata=metadata),
        repo=SimpleNamespace(tags=SimpleNamespace(all={"v2.2.0-alpha.1"})),
    )
    parent.versions = Versions(parent, pre=True)

    IncrementorVersion(parent).apply()

    assert metadata.version == "2.2.0-alpha.2"


def test_release_endpoint_propagates_release_failure(monkeypatch):
    failure = RuntimeError("package build failed")

    class DummyProject:
        def __init__(self, name, pinned=None, pre=False):
            assert name == "demo"
            assert pinned == "1.2.3"
            assert pre is False
            self.releaser = SimpleNamespace(run=self.run)

        @staticmethod
        def run(**kwargs):
            assert kwargs == {"release": True}
            raise failure

    monkeypatch.setattr("corio.infra.api.Project", DummyProject)

    endpoint = Release(SimpleNamespace())

    with pytest.raises(RuntimeError, match="package build failed") as caught:
        asyncio.run(endpoint.run("demo", pinned="1.2.3"))

    assert caught.value is failure


def test_infra_endpoint_project_names_are_repo_directory_literals():
    expected = tuple(sorted(path.name for path in paths.dev_repo.iterdir() if path.is_dir()))

    assert get_args(ProjectName) == expected
    for endpoint in (Release, DocumentationRelease, PreVersion):
        assert get_type_hints(endpoint.run)["name"] is ProjectName


def test_documentation_release_endpoint_only_releases_documentation(monkeypatch):
    releaser = SimpleNamespace()
    events = []

    class DummyProject:
        def __init__(self, name):
            assert name == "demo"
            self.releaser = releaser

    class DummyDocumentationRelease:
        def __init__(self, parent):
            assert parent is releaser

        def release(self):
            events.append("documentation")

    monkeypatch.setattr("corio.infra.api.Project", DummyProject)
    monkeypatch.setattr("corio.infra.api.ReleaseDocumentation", DummyDocumentationRelease)

    endpoint = DocumentationRelease(SimpleNamespace())
    asyncio.run(endpoint.run("demo"))

    assert endpoint.path == "/{name}/release-documentation"
    assert events == ["documentation"]


def test_pre_version_endpoint_returns_next_pre_release(monkeypatch):
    class DummyProject:
        def __init__(self, name):
            assert name == "demo"
            self.versions = SimpleNamespace(next_pre=version.parse("0.1.1-alpha.0"))

    monkeypatch.setattr("corio.infra.api.Project", DummyProject)

    endpoint = PreVersion(SimpleNamespace())

    assert asyncio.run(endpoint.run("demo")) == "0.1.1-alpha.0"


def test_process_deps_pins_project_dependencies(tmp_path):
    path_main_repo = Path(tmp_path / "corio")
    path_main_repo.mkdir(parents=True)

    path_editable_b_repo = Path(tmp_path / "editable_b")
    path_editable_b_repo.mkdir(parents=True)
    _write_editable_repo(path_editable_b_repo, name="editable_b", version="1.2.3")

    incrementor = _make_incrementor(path_main_repo, editables=("editable_b",))

    dependencies = ["editable_b", "requests>=2"]
    optional_dev = ["editable_b[logging]", "pytest"]

    assert incrementor._process_deps(dependencies) == ["editable_b~=1.2.3", "requests>=2"]
    assert incrementor._process_deps(optional_dev) == ["editable_b[logging]~=1.2.3", "pytest"]


def test_pyproject_cli_endpoint_returns_success_exit_code(monkeypatch):
    events = []
    releaser = SimpleNamespace()
    project = SimpleNamespace(
        releaser=releaser,
        versions=SimpleNamespace(new="1.2.3", pinned=None),
    )

    class _Project:
        def __init__(self, name, path=None):
            events.append(("project", name))

        @property
        def releaser(self):
            return project.releaser

        @property
        def versions(self):
            return project.versions

    class _IncrementorPyproject:
        def __init__(self, value):
            events.append(("incrementor", value))

        def apply(self):
            events.append(("apply", None))
            return Path("/repo/pyproject.toml")

    monkeypatch.setattr("corio.infra.project.Project", _Project)
    monkeypatch.setattr("corio.infra.incrementor_pyproject.IncrementorPyproject", _IncrementorPyproject)
    monkeypatch.setattr("corio.path.PackagePaths", lambda path: SimpleNamespace(name="target", repo=Path("/repo")))

    assert entrypoint.Pyproject().run() == 0
    assert project.versions.pinned == "1.2.3"
    assert events == [
        ("project", "target"),
        ("incrementor", releaser),
        ("apply", None),
    ]


def _make_test_env_generator(
    path_repo: Path,
    *,
    test_envs: bool,
    dependencies: dict[str, list[str]],
    editables: tuple[str, ...] = (),
) -> GeneratorTestEnvs:
    incrementor = _make_incrementor(path_repo, test_envs=test_envs, editables=editables)
    return GeneratorTestEnvs(paths=incrementor.paths, optionals=dependencies)


def _make_tester(path_repo: Path, *, env_list: list[str] | None = None) -> ReleaserTester:
    path_tests = path_repo / "corio" / "tests"
    path_tests.mkdir(parents=True)
    path_pyproject = path_repo / "pyproject.toml"
    if env_list is None:
        env_list = []

    env_lines = ", ".join(f'"{name}"' for name in env_list)
    path_pyproject.write_text(
        "\n".join(
            [
                "[tool.tox]",
                f"env_list = [{env_lines}]",
                "",
                "[project]",
                'name = "corio"',
                'version = "0.0.0"',
            ]
        ),
        encoding="utf-8",
    )
    parent = SimpleNamespace(
        name="corio",
        paths=SimpleNamespace(
            repo=path_repo,
            tests=path_tests,
            pyproject_repo=path_pyproject,
            name="corio",
            metadata=SimpleNamespace(editables=[]),
        ),
        incrementors=SimpleNamespace(
            cls={IncrementorPyproject: SimpleNamespace(editables={})},
        ),
    )
    return ReleaserTester(parent)


def test_generator_test_envs_get_deps_merges_module_and_dotted_children(tmp_path):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    generator = _make_test_env_generator(path_repo, test_envs=True, dependencies={
        "test": ["pytest", "pytest-cov"],
        "path": [],
        "path.app": ["appdirs"],
        "path.type": ["filetype"],
        "strings": [],
    })
    assert generator.get_deps("path") == ["appdirs", "filetype", "pytest", "pytest-cov"]
    assert generator.get_deps("strings") == ["pytest", "pytest-cov"]
    assert generator.get_deps("missing") == ["pytest", "pytest-cov"]


def test_generator_test_envs_deps_resolves_superset(tmp_path):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    dependencies = {
        "test": ["pytest", "pytest-cov"],
        "path": [],
        "path.app": ["appdirs"],
        "path.type": ["filetype"],
    }
    generator = _make_test_env_generator(path_repo, test_envs=True, dependencies=dependencies)
    (generator.paths.path / "path.py").write_text("", encoding="utf-8")
    (generator.paths.tests / "test_path.py").write_text("", encoding="utf-8")

    assert generator.get_deps("path") == ["appdirs", "filetype", "pytest", "pytest-cov"]


def test_generator_test_envs_use_file_module_name_with_test_envs(tmp_path):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    dependencies = {
        "test": ["pytest", "pytest-cov"],
        "path": [],
        "path.app": ["appdirs"],
        "path.type": ["filetype"],
        "strings": [],
    }
    generator = _make_test_env_generator(path_repo, test_envs=True, dependencies=dependencies)
    (generator.paths.path / "path.py").write_text("", encoding="utf-8")
    (generator.paths.path / "strings.py").write_text("", encoding="utf-8")
    (generator.paths.tests / "test_path.py").write_text("", encoding="utf-8")
    (generator.paths.tests / "test_strings.py").write_text("", encoding="utf-8")
    envs = generator.envs

    assert set(envs) == {"path", "strings"}
    assert envs["path"]["deps"] == ["appdirs", "filetype", "pytest", "pytest-cov"]
    assert envs["path"]["commands"] == [[
        "python",
        "-m",
        "pytest",
        "-q",
        "{posargs:corio/tests/test_path.py}",
    ]]
    assert envs["strings"]["deps"] == ["pytest", "pytest-cov"]


def test_generator_test_envs_passes_configured_environment(tmp_path):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    generator = _make_test_env_generator(path_repo, test_envs=True, dependencies={"test": ["pytest"]})
    generator.paths.metadata.test_pass_env = ["PLAYWRIGHT_BROWSERS_PATH"]

    env = generator.get_env("corio", ["pytest"], path_repo / "corio" / "tests")

    assert env["corio"]["pass_env"] == ["PLAYWRIGHT_BROWSERS_PATH"]


def test_generator_test_envs_refreshes_all_editables_with_tox_uv(tmp_path):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    generator = _make_test_env_generator(
        path_repo,
        test_envs=True,
        dependencies={"test": ["editable_a[test]~=0.0.8"]},
        editables=("editable_a", "corio"),
    )
    path_test = path_repo / "corio" / "tests" / "test_path.py"

    env = generator.get_env("corio", ["editable_a[test]~=0.0.8"], path_test)["corio"]

    assert env["install_command"] == [
        "uv",
        "pip",
        "install",
        "--refresh-package",
        "corio",
        "--refresh-package",
        "editable_a",
        "{opts}",
        "{packages}",
    ]


def test_generator_test_envs_fall_back_to_single_env_when_test_envs_disabled(tmp_path):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    generator = _make_test_env_generator(path_repo, test_envs=False, dependencies={"test": ["pytest", "pytest-cov"]})
    (generator.paths.tests / "test_unmatched.py").write_text("", encoding="utf-8")
    envs = generator.envs

    assert set(envs) == {"corio"}
    assert envs["corio"]["deps"] == ["pytest", "pytest-cov"]


def test_generator_test_envs_resolves_dotted_extras(tmp_path):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    generator = _make_test_env_generator(
        path_repo,
        test_envs=True,
        dependencies={
            "test": ["pytest", "pytest-cov"],
            "env": [],
            "env.io": ["dotenv"],
        },
    )
    (generator.paths.path / "env.py").write_text("", encoding="utf-8")
    (generator.paths.tests / "test_env.py").write_text("", encoding="utf-8")
    envs = generator.envs

    assert envs["env"]["deps"] == ["dotenv", "pytest", "pytest-cov"]


def test_tester_run_skips_when_no_tests_found(tmp_path):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    tester = _make_tester(path_repo, env_list=["corio"])

    assert tester.run() is True


def test_tester_run_skips_when_no_tox_envs_found(tmp_path):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    tester = _make_tester(path_repo, env_list=[])
    (tester.paths.tests / "test_path.py").write_text("", encoding="utf-8")

    assert tester.run() is True


def test_tester_run_retries_dependency_resolution_failure(tmp_path, monkeypatch):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    tester = _make_tester(path_repo, env_list=["corio"])
    (tester.paths.tests / "test_path.py").write_text("", encoding="utf-8")
    tester.RESOLUTION_RETRY_TIMEOUT = 30
    tester.RESOLUTION_RETRY_INTERVAL = 5
    failure = ReleaseTestsFailed(
        1,
        "No solution found when resolving dependencies: "
        "Because only example<=1.0 is available and you require example>=2.0.",
    )
    attempts = []
    waits = []

    def run_subprocess(self):
        attempts.append("tox")
        if len(attempts) == 1:
            raise failure
        return 0

    monkeypatch.setattr(ReleaserTester, "run_subprocess", run_subprocess)
    monkeypatch.setattr("corio.infra.releaser.time.monotonic", lambda: 0)
    monkeypatch.setattr("corio.infra.releaser.time.sleep", waits.append)

    assert tester.run() is True
    assert attempts == ["tox", "tox"]
    assert waits == [5]


def test_tester_does_not_retry_other_test_failures(tmp_path, monkeypatch):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    tester = _make_tester(path_repo, env_list=["corio"])
    (tester.paths.tests / "test_path.py").write_text("", encoding="utf-8")
    failure = ReleaseTestsFailed(1, "pytest failed")
    attempts = []

    def run_subprocess(self):
        attempts.append("tox")
        raise failure

    monkeypatch.setattr(ReleaserTester, "run_subprocess", run_subprocess)
    monkeypatch.setattr(
        "corio.infra.releaser.time.sleep",
        lambda interval: pytest.fail("Non-resolution failures must not be retried."),
    )

    with pytest.raises(ReleaseTestsFailed) as result:
        tester.run()

    assert result.value is failure
    assert attempts == ["tox"]


def test_tester_stops_retrying_resolution_failure_after_timeout(tmp_path, monkeypatch):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    tester = _make_tester(path_repo, env_list=["corio"])
    (tester.paths.tests / "test_path.py").write_text("", encoding="utf-8")
    tester.RESOLUTION_RETRY_TIMEOUT = 1
    tester.RESOLUTION_RETRY_INTERVAL = 1
    failure = ReleaseTestsFailed(
        1,
        "No solution found when resolving dependencies: "
        "Because only example<=1.0 is available and you require example>=2.0.",
    )
    now = [0]
    attempts = []
    waits = []

    def run_subprocess(self):
        attempts.append("tox")
        raise failure

    def sleep(interval):
        waits.append(interval)
        now[0] += interval

    monkeypatch.setattr(ReleaserTester, "run_subprocess", run_subprocess)
    monkeypatch.setattr("corio.infra.releaser.time.monotonic", lambda: now[0])
    monkeypatch.setattr("corio.infra.releaser.time.sleep", sleep)

    with pytest.raises(ReleaseTestsFailed) as result:
        tester.run()

    assert result.value is failure
    assert attempts == ["tox", "tox"]
    assert waits == [1]


def test_tester_run_raises_when_subprocess_fails(tmp_path, monkeypatch):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    tester = _make_tester(path_repo, env_list=["corio"])
    (tester.paths.tests / "test_path.py").write_text("", encoding="utf-8")

    monkeypatch.setattr(ReleaserTester, "run_subprocess", lambda self: 1)

    with pytest.raises(ReleaseTestsFailed, match="exit code 1"):
        tester.run()


def test_repository_get_most_recent_release_tag_filters_and_orders():
    repo = SimpleNamespace(tags=SimpleNamespace(all={
        "v1.2.1",
        "v1.2.2-rc.1",
        "v1.2.2",
        "v1.3.0-rc.1",
        "junk",
    }))

    any_tag = Repository.get_most_recent_release_tag(repo, include_pre=True)
    stable_tag = Repository.get_most_recent_release_tag(repo, include_pre=False)
    previous_stable = Repository.get_most_recent_release_tag(
        repo, include_pre=False, before=version.parse("1.2.2"),
    )
    previous_any = Repository.get_most_recent_release_tag(
        repo, include_pre=True, before=version.parse("1.2.2"),
    )

    assert any_tag == version.parse("1.3.0-rc.1")
    assert stable_tag == version.parse("1.2.2")
    assert previous_stable == version.parse("1.2.1")
    assert previous_any == version.parse("1.2.2-rc.1")
    assert stable_tag.tag == "v1.2.2"


def _make_version_incrementor(*, old: str, pinned: str | None, pre: bool | None = False, tags: set[str]):
    metadata = SimpleNamespace(version=old, version_obj=version.parse(old))
    parent = SimpleNamespace(
        paths=SimpleNamespace(name="corio", metadata=metadata),
        repo=SimpleNamespace(tags=SimpleNamespace(all=tags)),
    )
    parent.versions = Versions(parent, pinned=pinned, pre=pre)
    return IncrementorVersion(parent), metadata


def test_incrementor_version_reuses_stable_version_when_release_mode_aligned():
    incrementor, metadata = _make_version_incrementor(
        old="1.2.3",
        pinned=None,
        tags={"v1.2.2"},
    )

    incrementor.apply()

    assert metadata.version == "1.2.3"


def test_incrementor_version_raises_when_stable_tag_missing_for_pre_release():
    incrementor, _ = _make_version_incrementor(
        old="0.0.0",
        pinned=None,
        pre=True,
        tags=set(),
    )

    with pytest.raises(RuntimeError, match="Pin the intended release version"):
        incrementor.apply()


def test_incrementor_version_raises_when_pre_release_tag_missing():
    incrementor, _ = _make_version_incrementor(
        old="1.2.3-alpha.0",
        pinned=None,
        tags={"v1.2.2"},
    )

    with pytest.raises(RuntimeError, match="Pin the intended release version"):
        incrementor.apply()


def test_incrementor_version_reuses_pre_release_when_release_mode_aligned():
    incrementor, metadata = _make_version_incrementor(
        old="1.2.3-alpha.0",
        pinned=None,
        pre=True,
        tags=set(),
    )

    incrementor.apply()

    assert metadata.version == "1.2.3-alpha.0"


def test_incrementor_version_allows_pinned_release_when_old_tag_missing():
    incrementor, metadata = _make_version_incrementor(
        old="1.2.3",
        pinned="2.0.0",
        tags={"v1.2.2"},
    )

    incrementor.apply()

    assert metadata.version == "2.0.0"


def test_incrementor_version_allows_pinned_pre_release_when_old_tag_missing():
    incrementor, metadata = _make_version_incrementor(
        old="0.0.0",
        pinned="2.0.0",
        pre=True,
        tags=set(),
    )

    incrementor.apply()

    assert metadata.version == "2.0.0-alpha.0"


def test_incrementor_version_raises_when_pinned_tag_exists():
    incrementor, _ = _make_version_incrementor(
        old="1.2.3",
        pinned="2.0.0",
        tags={"v1.2.3", "v2.0.0"},
    )

    try:
        incrementor.apply()
    except RuntimeError as exception:
        assert 'Pinned version tag already exists: "v2.0.0".' in str(exception)
    else:
        raise AssertionError("Expected RuntimeError when pinned tag already exists.")


def test_releaser_cleanup_removes_release_artifacts(tmp_path):
    path_repo = Path(tmp_path)
    path_package = path_repo / "package"
    paths_to_create = [
        path_repo / ".tox",
        path_repo / "site",
        path_repo / ".pytest_cache",
        path_repo / "__pycache__",
        path_package / "module" / "__pycache__",
        path_package / "tests" / "__pycache__",
        path_repo / ".venv" / "lib" / "__pycache__",
    ]
    for path in paths_to_create:
        path.mkdir(parents=True)
    (path_repo / ".coverage").write_text("coverage", encoding="utf-8")
    (path_repo / ".coverage.worker").write_text("coverage", encoding="utf-8")
    (path_repo / ".coveragerc").write_text("[run]", encoding="utf-8")

    releaser = Releaser(SimpleNamespace(
        paths=SimpleNamespace(repo=path_repo, path=path_package),
    ))

    releaser.cleanup()

    assert not (path_repo / ".tox").exists()
    assert not (path_repo / "site").exists()
    assert not (path_repo / ".pytest_cache").exists()
    assert not (path_repo / "__pycache__").exists()
    assert not (path_repo / ".coverage").exists()
    assert not (path_repo / ".coverage.worker").exists()
    assert (path_repo / ".coveragerc").exists()
    assert not (path_package / "module" / "__pycache__").exists()
    assert not (path_package / "tests" / "__pycache__").exists()
    assert (path_repo / ".venv" / "lib" / "__pycache__").exists()


def test_releaser_stages_incrementor_outputs_after_all_succeed(tmp_path, monkeypatch):
    events = []

    class _Index:
        def add(self, path):
            events.append(("stage", path))

        def remove(self, path):
            events.append(("remove", path))

        def write(self):
            events.append(("write",))

    class _Incrementor:
        def __init__(self, name, path):
            self.name = name
            self.path = path

        def apply(self):
            events.append(("apply", self.name))
            return self.path

        def rollback(self):
            events.append(("rollback", self.name))

    root = Path(tmp_path)
    paths = [root / "first.toml", root / "second.yaml"]
    for path in paths:
        path.write_text("synthetic output", encoding="utf-8")
    index = _Index()
    releaser = Releaser(SimpleNamespace(
        paths=SimpleNamespace(repo=root),
        repo=SimpleNamespace(origin=SimpleNamespace(url="https://example.invalid/repo")),
    ))
    releaser.incrementors = [
        _Incrementor("first", paths[0]),
        _Incrementor("second", paths[1]),
    ]
    monkeypatch.setattr(Releaser, "index", property(lambda self: index))

    releaser.increment()

    assert events == [
        ("apply", "first"),
        ("apply", "second"),
        ("stage", "first.toml"),
        ("stage", "second.yaml"),
        ("write",),
    ]


def test_releaser_rolls_back_incrementors_and_reraises_failure(tmp_path):
    events = []
    failure = RuntimeError("synthetic incrementor failure")

    class _Incrementor:
        def __init__(self, name, fails=False):
            self.name = name
            self.fails = fails

        def apply(self):
            events.append(("apply", self.name))
            if self.fails:
                raise failure
            return None

        def rollback(self):
            events.append(("rollback", self.name))

    root = Path(tmp_path)
    releaser = Releaser(SimpleNamespace(
        paths=SimpleNamespace(repo=root),
        repo=SimpleNamespace(origin=SimpleNamespace(url="https://example.invalid/repo")),
    ))
    releaser.incrementors = [_Incrementor("first"), _Incrementor("second", fails=True)]

    with pytest.raises(RuntimeError) as result:
        releaser.increment()

    assert result.value is failure
    assert events == [
        ("apply", "first"),
        ("apply", "second"),
        ("rollback", "second"),
        ("rollback", "first"),
    ]


def test_releaser_run_cleans_up_after_successful_release(monkeypatch):
    events = []

    class _Repo:
        def fetch(self):
            events.append("fetch")

        def push(self):
            events.append("push")

    releaser = Releaser(SimpleNamespace(
        name="corio",
        paths=SimpleNamespace(name="corio", metadata=SimpleNamespace(is_dockerhub=False, is_pypi=False, container_host=None)),
    ))
    releaser.repo = _Repo()

    monkeypatch.setattr(Releaser, "increment", lambda self: events.append("increment"))
    monkeypatch.setattr(Releaser, "commit", lambda self: events.append("commit"))
    monkeypatch.setattr(Releaser, "package", lambda self: events.append("package"))
    monkeypatch.setattr(Releaser, "release", lambda self: events.append("release"))
    monkeypatch.setattr(Releaser, "cleanup", lambda self: events.append("cleanup"))

    releaser.run()

    assert events == ["fetch", "increment", "commit", "push", "fetch", "package", "release", "cleanup"]


def test_releaser_run_commits_only_after_incrementors_succeed(monkeypatch):
    events = []

    class _Repo:
        def fetch(self):
            events.append("fetch")

        def push(self):
            events.append("push")

    releaser = Releaser(SimpleNamespace(
        name="corio",
        paths=SimpleNamespace(name="corio", metadata=SimpleNamespace(is_dockerhub=False, is_pypi=False, container_host=None)),
    ))
    releaser.repo = _Repo()

    monkeypatch.setattr(Releaser, "increment", lambda self: events.append("increment"))
    monkeypatch.setattr(Releaser, "commit", lambda self: events.append("commit"))

    releaser.run(release=False)

    assert events == ["fetch", "increment", "commit", "push", "fetch"]


def test_releaser_run_stops_on_prerelease_test_failure(monkeypatch):
    events = []
    failure = ReleaseTestsFailed(1, "synthetic test failure")

    class _Repo:
        def fetch(self):
            events.append("fetch")

        def push(self):
            events.append("push")

    releaser = Releaser(SimpleNamespace(
        name="sample",
        versions=SimpleNamespace(pre_current=True),
        paths=SimpleNamespace(name="sample", metadata=SimpleNamespace(is_dockerhub=False, is_pypi=False, container_host=None)),
    ))
    releaser.repo = _Repo()

    def fail_increment(self):
        events.append("increment")
        raise failure

    monkeypatch.setattr(Releaser, "increment", fail_increment)
    monkeypatch.setattr(Releaser, "commit", lambda self: events.append("commit"))

    with pytest.raises(ReleaseTestsFailed) as result:
        releaser.run(release=False)

    assert result.value is failure
    assert events == ["fetch", "increment"]


# def test_intentional_failure_for_testing():
#     assert False, "Intentional failing test for test-pipeline verification."
