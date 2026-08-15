from corio.path import PackagePaths, Path
from corio.sets import Base


def make_package_paths(repo):
    paths = object.__new__(PackagePaths)
    paths.repo = repo
    paths.name = 'test'
    paths.org = None
    return paths


def make_settings(package_paths):
    class Settings(Base):
        paths = package_paths
        value: str | None = None

        @classmethod
        def get_yaml_source(cls, settings_cls):
            return None

    return Settings


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
    (repo / '.env').write_text('TEST__VALUE=from-dotenv\n')
    paths = make_package_paths(repo)
    settings = make_settings(paths)

    assert settings().value == 'from-dotenv'
