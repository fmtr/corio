import pytest
from cached_classproperty import cached_classproperty

from corio import dm
from corio.path import PackagePaths, Path
from corio.sets import Base


def make_package_paths(repo):
    paths = object.__new__(PackagePaths)
    paths.repo = repo
    paths.name = 'test'
    return paths


def make_settings(package_paths):
    class Settings(Base):
        paths = package_paths
        value: str | None = None

        @classmethod
        def get_yaml_source(cls, settings_cls):
            return None

    return Settings


def test_settings_base_inherits_dm_base_and_ignores_cached_classproperty(tmp_path):
    settings_base = make_settings(make_package_paths(Path(tmp_path)))

    class Settings(settings_base):
        @cached_classproperty
        def label(cls) -> str:
            return cls.__name__

    assert issubclass(Settings, dm.Base)
    assert "value" in Settings.model_fields
    assert "label" not in Settings.model_fields
    assert Settings.FIELDS == {}
    assert Settings.label == "Settings"
    assert Settings.run is Base.run


def test_settings_run_returns_when_no_subcommand(tmp_path, monkeypatch):
    settings = make_settings(make_package_paths(Path(tmp_path)))()
    monkeypatch.setattr("pydantic_settings.get_subcommand", lambda *args, **kwargs: None)

    assert settings.run() is None


def test_settings_run_exits_with_sync_subcommand_result(tmp_path, monkeypatch):
    settings = make_settings(make_package_paths(Path(tmp_path)))()

    class Command:
        def run(self):
            return 3

    monkeypatch.setattr("pydantic_settings.get_subcommand", lambda *args, **kwargs: Command())

    with pytest.raises(SystemExit) as error:
        settings.run()

    assert error.value.code == 3


def test_settings_run_exits_with_async_subcommand_result(tmp_path, monkeypatch):
    settings = make_settings(make_package_paths(Path(tmp_path)))()

    class Command:
        async def run(self):
            return 4

    monkeypatch.setattr("pydantic_settings.get_subcommand", lambda *args, **kwargs: Command())

    with pytest.raises(SystemExit) as error:
        settings.run()

    assert error.value.code == 4


def test_settings_accept_init_values(tmp_path):
    settings = make_settings(make_package_paths(Path(tmp_path)))

    assert settings(value="from-init").value == "from-init"


def test_find_env_file_defaults_to_repo(tmp_path):
    repo = Path(tmp_path)
    paths = make_package_paths(repo)
    settings = make_settings(paths)

    assert settings.find_env_file() == repo / '.env'


def test_find_env_file_defaults_to_cwd_outside_repo(tmp_path):
    paths = make_package_paths(None)
    settings = make_settings(paths)

    with Path(tmp_path).chdir:
        assert settings.find_env_file() == Path(tmp_path) / '.env'


def test_dotenv_source_uses_default_repo_path(tmp_path):
    repo = Path(tmp_path)
    (repo / '.env').write_text('TEST__VALUE=from-dotenv\nUNRELATED=value\n')
    paths = make_package_paths(repo)
    settings = make_settings(paths)

    assert settings().value == 'from-dotenv'
