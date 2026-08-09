import pathlib
from datetime import timezone

import pytest

from corio import path


@pytest.mark.parametrize(
    'args',
    [
        ['/', 'opt', 'data'],
        ['dir', 'data'],
    ]
)
def test_path_args(args):
    expected = str(pathlib.Path(*args))
    actual = str(path.Path(*args))
    assert actual == expected


def test_path_module():
    """



    """
    expected = path.Path(__file__).absolute()
    expected_from_fmtr_home = path.PackagePaths.dev / expected.relative_to(path.Path.home())
    actual = path.Path.module()
    assert actual in (expected, expected_from_fmtr_home)


def test_path_package():
    """



    """
    expected = path.Path(__file__).absolute().parent
    expected_from_fmtr_home = path.PackagePaths.dev / expected.relative_to(path.Path.home())
    actual = path.Path.package()
    assert actual in (expected, expected_from_fmtr_home)


def test_read_write_data_uses_extension_and_txt_fallback(tmp_path):
    path_json = path.Path(tmp_path / "data.json")
    data = {"a": 1}
    path_json.write_data(data)
    assert path_json.read_data() == data

    path_txt = path.Path(tmp_path / "notes.unknown")
    path_txt.write_data("hello")
    assert path_txt.read_data() == "hello"


def test_with_suffix_and_get_conversion_path(tmp_path):
    path_file = path.Path(tmp_path / "yaml" / "settings.yaml")
    path_file.parent.mkdir(parents=True)
    path_file.write_text("a: 1")

    assert path_file.with_suffix("json").name == "settings.json"
    assert path_file.get_conversion_path("json") == path.Path(tmp_path / "json" / "settings.json")

    path_invalid = path.Path(tmp_path / "configs" / "settings.yaml")
    path_invalid.parent.mkdir(parents=True)
    path_invalid.write_text("a: 1")
    with pytest.raises(ValueError):
        path_invalid.get_conversion_path("json")


def test_mkdirf_exist_children_and_timestamps(tmp_path):
    path_dir = path.Path(tmp_path / "a" / "b")
    path_dir.mkdirf()
    assert path_dir.exist is True

    path_subdir = path.Path(path_dir / "subdir")
    path_subdir.mkdir()
    path_file = path.Path(path_dir / "f.txt")
    path_file.write_text("x")

    children = path_dir.children
    assert children[0] == path_subdir
    assert children[1] == path_file
    assert path_file.children is None

    assert path_file.accessed.tzinfo == timezone.utc
    assert path_file.modified.tzinfo == timezone.utc
    assert path_file.metadata_changed.tzinfo == timezone.utc
    if path_file.created is not None:
        assert path_file.created.tzinfo == timezone.utc


def test_chown_can_recurse(tmp_path, monkeypatch):
    import pwd
    import corio.path.path as path_mod

    path_root = path.Path(tmp_path / "secret")
    path_root.mkdir(parents=True)
    path_child = path.Path(path_root / "child.txt")
    path_child.write_text("x")

    chown_calls = []

    def _chown(path_obj, uid, gid):
        chown_calls.append((path.Path(path_obj), uid, gid))

    class _User:
        pw_uid = 1001
        pw_gid = 1002

    monkeypatch.setattr(pwd, "getpwnam", lambda _user: _User())
    monkeypatch.setattr(path_mod.os, "chown", _chown)

    path_root.chown("foo", recurse=True)

    assert chown_calls == [
        (path_root, 1001, 1002),
        (path_child, 1001, 1002),
    ]


def test_find_up_and_chdir(tmp_path):
    path_root = path.Path(tmp_path / "root")
    path_leaf = path.Path(path_root / "x" / "y")
    path_leaf.mkdir(parents=True)
    marker = path_root / "pyproject.toml"
    marker.write_text("[tool.corio]\n")

    found = path_leaf.find_up("pyproject.toml")
    assert found == marker

    with pytest.raises(FileNotFoundError):
        path_leaf.find_up("missing.file")

    cwd_before = path.Path.cwd()
    with path_root.chdir as cwd_inside:
        assert cwd_inside == path_root
        assert path.Path.cwd() == path_root
    assert path.Path.cwd() == cwd_before


def test_find_site_accepts_uv_archive_layout(tmp_path, monkeypatch):
    import corio.path.path as path_mod

    path_package = path.Path(
        tmp_path
        / "archive-v0"
        / "h_Y5xD0yLtWh1w4P"
        / "lib"
        / "python3.14"
        / "site-packages"
        / "corio"
    )
    path_package.mkdir(parents=True)

    monkeypatch.setattr(
        path_mod.site,
        "getsitepackages",
        lambda: [str(tmp_path / "venv" / "lib" / "python3.14" / "site-packages")],
    )
    monkeypatch.setattr(path_mod.site, "getusersitepackages", lambda: str(tmp_path / "user-site"))

    actual = path_mod.PathsSearchData.find_site(path_package)
    assert actual == path_package.parent


def test_find_site_accepts_injected_sys_path(tmp_path, monkeypatch):
    import corio.path.path as path_mod

    path_package = path.Path(tmp_path / "injected" / "corio")
    path_package.mkdir(parents=True)

    monkeypatch.setattr(
        path_mod.site,
        "getsitepackages",
        lambda: [str(tmp_path / "venv" / "lib" / "python3.14" / "site-packages")],
    )
    monkeypatch.setattr(path_mod.site, "getusersitepackages", lambda: str(tmp_path / "user-site"))
    monkeypatch.setattr(path_mod.sys, "path", [str(tmp_path / "injected"), str(tmp_path / "elsewhere")])

    actual = path_mod.PathsSearchData.find_site(path_package)
    assert actual == path_package.parent


def test_pydantic_helpers():
    value = path.Path("/tmp/a")
    assert path.Path.__serialize_pydantic__(value) == "/tmp/a"
    assert path.Path.__deserialize_pydantic__("/tmp/b") == path.Path("/tmp/b")
    assert path.Path.__deserialize_pydantic__(value) is value


def test_path_submodule_app(monkeypatch):
    from corio.path.app import AppPaths
    import appdirs

    monkeypatch.setattr(appdirs, "user_data_dir", lambda **kwargs: "/tmp/corio-user-data")

    app_paths = AppPaths()
    value = app_paths.user_data_dir(appname="corio")
    assert isinstance(value, path.Path)
    assert str(value) == "/tmp/corio-user-data"


def test_path_submodule_type_guess(monkeypatch):
    from corio.path import type as path_type

    sentinel = object()
    monkeypatch.setattr(path_type, "guess", lambda _value: sentinel)

    assert path_type.guess("anything") is sentinel
