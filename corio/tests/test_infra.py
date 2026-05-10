from types import SimpleNamespace

from packaging.requirements import Requirement

from corio import version
from corio.infra.incrementor_pyproject import IncrementorPyproject, GeneratorTestEnvs
from corio.infra.releaser import Releaser, IncrementorVersion, Tester as ReleaserTester
from corio.infra.repository import Repository
from corio.path import Path


def _write_editable_repo(path_repo: Path, name: str, version: str) -> None:
    (path_repo / "pyproject.toml").write_text("", encoding="utf-8")
    path_package = path_repo / name
    path_package.mkdir(parents=True)
    (path_package / "pyproject.package.toml").write_text(
        f'[tool.corio.metadata]\nversion = "{version}"\n',
        encoding="utf-8",
    )


def _make_incrementor(path_repo: Path, is_pre: bool = False, test_envs: bool = True) -> IncrementorPyproject:
    path_package = path_repo / "corio"
    path_package.mkdir(parents=True, exist_ok=True)
    path_tests = path_repo / "corio" / "tests"
    path_tests.mkdir(parents=True, exist_ok=True)
    parent = SimpleNamespace(
        paths=SimpleNamespace(
            repo=path_repo,
            pyproject_repo=path_repo / "pyproject.toml",
            name_ns="corio",
            path=path_package,
            tests=path_tests,
            metadata=SimpleNamespace(test_envs=test_envs),
        ),
        versions=SimpleNamespace(is_pre=is_pre),
    )
    return IncrementorPyproject(parent)


def test_pin_editables_and_flatten_dependencies(tmp_path):
    path_main_repo = Path(tmp_path / "corio")
    path_main_repo.mkdir(parents=True)

    path_haco_repo = Path(path_main_repo / "haco")
    path_haco_repo.mkdir(parents=True)
    _write_editable_repo(path_haco_repo, name="haco", version="1.2.3")

    (path_main_repo / "pyproject.toml").write_text(
        '[tool.uv.sources.haco]\npath = "haco"\neditable = true\n',
        encoding="utf-8",
    )

    incrementor = _make_incrementor(path_main_repo)

    assert incrementor._pin_editable("haco") == "haco~=1.2.3"
    assert incrementor._pin_editable("requests") == "requests"

    install, extras = incrementor._flatten_dependencies(
        {
            "install": ["haco", "requests"],
            "dev": ["haco"],
        }
    )

    assert install == ["haco", "requests"]
    assert extras == {"dev": ["haco"], "all": ["haco"]}


def test_pin_editables_resolves_uv_source_path(tmp_path):
    path_main_repo = Path(tmp_path / "app")
    path_main_repo.mkdir(parents=True)

    path_corio_repo = Path(tmp_path / "corio")
    path_corio_repo.mkdir(parents=True)
    _write_editable_repo(path_corio_repo, name="corio", version="1.2.3")

    (path_main_repo / "pyproject.toml").write_text(
        '[tool.uv.sources.corio]\npath = "../corio"\neditable = true\n',
        encoding="utf-8",
    )

    incrementor = _make_incrementor(path_main_repo)
    assert incrementor._pin_editable("corio") == "corio~=1.2.3"


def test_pin_editables_preserves_extras_and_skips_existing_specifiers(tmp_path):
    path_main_repo = Path(tmp_path / "corio")
    path_main_repo.mkdir(parents=True)

    path_haco_repo = Path(path_main_repo / "haco")
    path_haco_repo.mkdir(parents=True)
    _write_editable_repo(path_haco_repo, name="haco", version="1.2.3")

    (path_main_repo / "pyproject.toml").write_text(
        '[tool.uv.sources.haco]\npath = "haco"\neditable = true\n',
        encoding="utf-8",
    )

    incrementor = _make_incrementor(path_main_repo)

    dep = incrementor._pin_editable("haco[version.dev,logging,sets,yaml,debug,caching,api,mqtt]")
    req = Requirement(dep)
    assert req.name == "haco"
    assert req.extras == {"version.dev", "logging", "sets", "yaml", "debug", "caching", "api", "mqtt"}
    assert str(req.specifier) == "~=1.2.3"

    assert incrementor._pin_editable("haco==1.0.0") == "haco==1.0.0"
    assert incrementor._pin_editable("haco~=1.0.0") == "haco~=1.2.3"
    assert incrementor._pin_editable("haco>=1.0.0") == "haco>=1.0.0"


def test_pin_editables_raises_on_prerelease_when_current_is_release(tmp_path):
    path_main_repo = Path(tmp_path / "corio")
    path_main_repo.mkdir(parents=True)

    path_haco_repo = Path(path_main_repo / "haco")
    path_haco_repo.mkdir(parents=True)
    _write_editable_repo(path_haco_repo, name="haco", version="1.2.3-rc.1")

    (path_main_repo / "pyproject.toml").write_text(
        '[tool.uv.sources.haco]\npath = "haco"\neditable = true\n',
        encoding="utf-8",
    )

    incrementor = _make_incrementor(path_main_repo, is_pre=False)

    try:
        _ = incrementor.editables
    except ValueError as exception:
        assert 'Editable dependency "haco" is pre-release' in str(exception)
    else:
        raise AssertionError("Expected ValueError for prerelease editable dependency")


def test_pin_editables_allows_prerelease_when_current_is_prerelease(tmp_path):
    path_main_repo = Path(tmp_path / "corio")
    path_main_repo.mkdir(parents=True)

    path_haco_repo = Path(path_main_repo / "haco")
    path_haco_repo.mkdir(parents=True)
    _write_editable_repo(path_haco_repo, name="haco", version="1.2.3-rc.1")

    (path_main_repo / "pyproject.toml").write_text(
        '[tool.uv.sources.haco]\npath = "haco"\neditable = true\n',
        encoding="utf-8",
    )

    incrementor = _make_incrementor(path_main_repo, is_pre=True)

    assert incrementor._pin_editable("haco") == "haco~=1.2.3-rc.1"


def test_process_deps_pins_project_dependencies(tmp_path):
    path_main_repo = Path(tmp_path / "corio")
    path_main_repo.mkdir(parents=True)

    path_haco_repo = Path(path_main_repo / "haco")
    path_haco_repo.mkdir(parents=True)
    _write_editable_repo(path_haco_repo, name="haco", version="1.2.3")

    (path_main_repo / "pyproject.toml").write_text(
        '[tool.uv.sources.haco]\npath = "haco"\neditable = true\n',
        encoding="utf-8",
    )

    incrementor = _make_incrementor(path_main_repo)

    dependencies = ["haco", "requests>=2"]
    optional_dev = ["haco[logging]", "pytest"]

    assert incrementor._process_deps(dependencies) == ["haco~=1.2.3", "requests>=2"]
    assert incrementor._process_deps(optional_dev) == ["haco[logging]~=1.2.3", "pytest"]


def _make_test_env_generator(path_repo: Path, *, test_envs: bool, dependencies: dict[str, list[str]]) -> GeneratorTestEnvs:
    incrementor = _make_incrementor(path_repo, test_envs=test_envs)
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
            name_ns="corio",
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
    assert envs["strings"]["deps"] == ["pytest", "pytest-cov"]


def test_generator_test_envs_fall_back_to_single_env_when_test_envs_disabled(tmp_path):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    generator = _make_test_env_generator(path_repo, test_envs=False, dependencies={"test": ["pytest", "pytest-cov"]})
    (generator.paths.path / "path.py").write_text("", encoding="utf-8")
    (generator.paths.tests / "test_path.py").write_text("", encoding="utf-8")
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


def test_tester_run_returns_false_when_subprocess_fails(tmp_path, monkeypatch):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    tester = _make_tester(path_repo, env_list=["corio"])
    (tester.paths.tests / "test_path.py").write_text("", encoding="utf-8")

    monkeypatch.setattr(ReleaserTester, "run_subprocess", lambda self: 1)

    assert tester.run() is False


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


def _make_version_incrementor(*, old: str, pinned: str | None, tags: set[str]):
    metadata = SimpleNamespace(version=old, version_obj=version.parse(old))
    parent = SimpleNamespace(
        paths=SimpleNamespace(name_ns="corio", metadata=metadata),
        versions=SimpleNamespace(pinned=version.parse(pinned) if pinned else None),
        repo=SimpleNamespace(tags=SimpleNamespace(all=tags)),
    )
    return IncrementorVersion(parent), metadata


def test_incrementor_version_does_not_increment_when_old_tag_missing():
    incrementor, metadata = _make_version_incrementor(
        old="1.2.3",
        pinned=None,
        tags={"v1.2.2"},
    )

    incrementor.apply()

    assert metadata.version == "1.2.3"


def test_incrementor_version_raises_when_pinned_and_old_tag_missing():
    incrementor, _ = _make_version_incrementor(
        old="1.2.3",
        pinned="2.0.0",
        tags={"v1.2.2"},
    )

    try:
        incrementor.apply()
    except RuntimeError as exception:
        assert 'Current version tag "v1.2.3" was not found.' in str(exception)
        assert 'Refusing pinned release "2.0.0"' in str(exception)
    else:
        raise AssertionError("Expected RuntimeError when old tag is missing for pinned release.")


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


def test_releaser_run_commits_only_after_tests_pass(monkeypatch):
    events = []

    class _Repo:
        def fetch(self):
            events.append("fetch")

        def push(self):
            events.append("push")

    releaser = Releaser(SimpleNamespace(
        name="corio",
        paths=SimpleNamespace(name_ns="corio", metadata=SimpleNamespace(is_dockerhub=False, is_pypi=False)),
    ))
    releaser.repo = _Repo()
    releaser.tester = SimpleNamespace(run=lambda: events.append("tests") or True)

    monkeypatch.setattr(Releaser, "increment", lambda self: events.append("increment"))
    monkeypatch.setattr(Releaser, "commit", lambda self: events.append("commit"))

    releaser.run(build=False, release=False)

    assert events == ["fetch", "increment", "tests", "commit", "push", "fetch"]


def test_releaser_run_continues_when_pre_tests_fail(monkeypatch):
    events = []

    class _Repo:
        def fetch(self):
            events.append("fetch")

        def push(self):
            events.append("push")

    releaser = Releaser(SimpleNamespace(
        name="corio",
        version=version.parse("1.2.3-rc.1"),
        versions=SimpleNamespace(is_pre=True),
        paths=SimpleNamespace(name_ns="corio", metadata=SimpleNamespace(is_dockerhub=False, is_pypi=False)),
    ))
    releaser.repo = _Repo()
    releaser.tester = SimpleNamespace(run=lambda: events.append("tests") or False)

    monkeypatch.setattr(Releaser, "increment", lambda self: events.append("increment"))
    monkeypatch.setattr(Releaser, "commit", lambda self: events.append("commit"))

    releaser.run(build=False, release=False)

    assert events == ["fetch", "increment", "tests", "commit", "push", "fetch"]


# def test_intentional_failure_for_testing():
#     assert False, "Intentional failing test for test-pipeline verification."
