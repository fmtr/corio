import re
from dataclasses import asdict

import corio
import corio.paths as paths_module
import pytest
from corio import path


@pytest.fixture(params=[True, False])
def package_paths(request, tmp_path):
    repo = path.Path(tmp_path / "repo")
    package = repo / "sample"
    package.mkdir(parents=True)
    pyproject = repo / "pyproject.toml"
    project_config = (
        "[project]\nname = 'sample'\n\n"
        "[tool.corio.metadata]\nversion = '1.2.3'\n"
    )
    pyproject.write_text(project_config)
    package_marker = package / "pyproject.package.toml"

    if request.param:
        package_marker.symlink_to(pyproject)
    else:
        package_marker.write_text(project_config)

    return path.PackagePaths(package)


def test_metadata_version_dev_uses_package_development_status(package_paths):
    metadata = package_paths.metadata
    actual = metadata.version_dev

    if package_paths.is_dev:
        assert re.fullmatch(
            r"1\.2\.4-development\+\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}",
            actual,
        )
        return

    assert actual == "1.2.3"


def test_metadata_context_is_hidden_from_serialization(package_paths):
    metadata = package_paths.metadata

    assert metadata.paths is package_paths
    assert "paths" not in asdict(metadata)


def test_metadata_version_dev_is_cached(package_paths):
    metadata = package_paths.metadata
    actual = metadata.version_dev
    metadata.version = "9.8.7"

    assert metadata.version_dev == actual


def test_get_version_returns_metadata_version_dev(package_paths, monkeypatch):
    monkeypatch.setattr(paths_module, "paths", package_paths)

    actual = corio.get_version()

    assert actual == package_paths.metadata.version_dev
