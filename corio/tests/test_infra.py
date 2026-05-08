from types import SimpleNamespace

from packaging.requirements import Requirement

from corio.infra.incrementor_pyproject import IncrementorPyproject
from corio.infra.releaser import Tester as ReleaserTester
from corio.path import Path


def _write_editable_repo(path_repo: Path, name: str, version: str) -> None:
    (path_repo / "pyproject.toml").write_text("", encoding="utf-8")
    path_package = path_repo / name
    path_package.mkdir(parents=True)
    (path_package / "pyproject.package.toml").write_text(
        f'[tool.corio.metadata]\nversion = "{version}"\n',
        encoding="utf-8",
    )


def _make_incrementor(path_repo: Path, is_pre: bool = False) -> IncrementorPyproject:
    parent = SimpleNamespace(
        paths=SimpleNamespace(
            repo=path_repo,
            pyproject_repo=path_repo / "pyproject.toml",
            name_ns="corio",
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

    assert incrementor._pin_editable("haco") == "haco==1.2.3"
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
    assert incrementor._pin_editable("corio") == "corio==1.2.3"


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
    assert str(req.specifier) == "==1.2.3"

    assert incrementor._pin_editable("haco==1.0.0") == "haco==1.2.3"
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

    assert incrementor._pin_editable("haco") == "haco==1.2.3-rc.1"


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

    assert incrementor._process_deps(dependencies) == ["haco==1.2.3", "requests>=2"]
    assert incrementor._process_deps(optional_dev) == ["haco[logging]==1.2.3", "pytest"]


def _make_tester(path_repo: Path, *, test_envs: bool) -> ReleaserTester:
    path_tests = path_repo / "corio" / "tests"
    path_tests.mkdir(parents=True)
    path_pyproject = path_repo / "pyproject.toml"
    path_pyproject.write_text(
        "\n".join(
            [
                "[project]",
                'name = "corio"',
                'version = "0.0.0"',
                "",
                "[project.optional-dependencies]",
                'test = ["pytest", "pytest-cov"]',
                'path = []',
                '"path.app" = ["appdirs"]',
                '"path.type" = ["filetype"]',
                "strings = []",
                "",
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
            metadata=SimpleNamespace(test_envs=test_envs),
        ),
    )
    return ReleaserTester(parent)


def test_tester_get_extras_module_merges_module_and_dotted_children(tmp_path):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    tester = _make_tester(path_repo, test_envs=True)

    assert tester.get_extras_module("path") == ["path.app", "path.type", "path", "test"]
    assert tester.get_extras_module("strings") == ["strings", "test"]
    assert tester.get_extras_module("missing") == ["test"]


def test_tester_get_deps_extras_resolves_recursive_dependencies(tmp_path):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    tester = _make_tester(path_repo, test_envs=True)

    deps = tester.get_deps_extras(["path.app", "path.type", "test"])
    assert "pytest" in deps
    assert "pytest-cov" in deps

    deps_missing = tester.get_deps_extras(["missing"])
    assert deps_missing == []


def test_tester_envs_use_file_module_name_with_test_envs(tmp_path):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    tester = _make_tester(path_repo, test_envs=True)
    (tester.paths.tests / "test_path.py").write_text("", encoding="utf-8")
    (tester.paths.tests / "test_strings.py").write_text("", encoding="utf-8")

    envs = tester.envs

    assert set(envs) == {"corio.path", "corio.strings"}
    assert envs["corio.path"]["extras"] == ["path.app", "path.type", "path", "test"]
    assert envs["corio.strings"]["extras"] == ["strings", "test"]
    assert "pytest" in envs["corio.path"]["deps"]


def test_tester_envs_fall_back_to_single_env_when_test_envs_disabled(tmp_path):
    path_repo = Path(tmp_path / "corio")
    path_repo.mkdir(parents=True)
    tester = _make_tester(path_repo, test_envs=False)
    (tester.paths.tests / "test_path.py").write_text("", encoding="utf-8")

    envs = tester.envs

    assert set(envs) == {"corio"}
    assert envs["corio"]["extras"] == ["test"]
