from typing import ClassVar, Any

from pydantic_settings import (
    BaseSettings,
    CliSettingsSource,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)

from corio import Constants
from corio.dm import CliRunMixin
from corio.iterator import strip_none
from corio.path import Path
from corio.paths import paths


class YamlScriptConfigSettingsSource(YamlConfigSettingsSource):
    """

    Customer source for reading YAML *Script* (as opposed to plain YAML) configuration files.

    """

    def _read_file(self, file_path: Path) -> dict[str, Any]:
        """

        Use our own Path class to read YAML Script.

        """
        data = Path(file_path).read_yaml() or {}
        return data


class BaseCLI(BaseSettings, CliRunMixin):
    """Base settings class that reads configuration only from the CLI."""

    ENV_NESTED_DELIMITER: ClassVar = Constants.ENV_NESTED_DELIMITER

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """

        Define priority and additional sources. Note: the earlier items have higher priority.

        """

        return tuple(strip_none(
            cls.get_init_source(settings_cls, init_settings),
            cls.get_cli_source(settings_cls),
            cls.get_env_source(settings_cls),
            cls.get_dotenv_source(settings_cls),
            cls.get_file_secret_source(settings_cls, file_secret_settings),
            cls.get_yaml_source(settings_cls),
        ))

    @classmethod
    def get_init_source(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
    ) -> PydanticBaseSettingsSource | None:
        """

        Get the settings source for values passed during initialization.

        """
        return None

    @classmethod
    def get_cli_source(
            cls,
            settings_cls: type[BaseSettings],
    ) -> PydanticBaseSettingsSource | None:
        """

        Get the command-line settings source.

        """
        cli_parse_args = cls.model_config.get('cli_parse_args')
        if cli_parse_args is None:
            cli_parse_args = False
        return CliSettingsSource(settings_cls, cli_parse_args=cli_parse_args)

    @classmethod
    def get_env_source(
            cls,
            settings_cls: type[BaseSettings],
    ) -> PydanticBaseSettingsSource | None:
        """

        Read settings from process environment variables.

        """
        return EnvSettingsSource(
            settings_cls,
            env_prefix=cls.get_env_prefix(),
            env_nested_delimiter=cls.ENV_NESTED_DELIMITER,
        )

    @classmethod
    def get_env_prefix(cls):
        """

        Get environment variable prefix, which depends on whether the package is a namespace/singleton.

        """
        return None

    @classmethod
    def get_dotenv_source(
            cls,
            settings_cls: type[BaseSettings],
    ) -> PydanticBaseSettingsSource | None:
        """

        Get the dotenv settings source.

        """
        return None

    @classmethod
    def get_file_secret_source(
            cls,
            settings_cls: type[BaseSettings],
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> PydanticBaseSettingsSource | None:
        """

        Get the file secret settings source.

        """
        return None

    @classmethod
    def get_yaml_source(
            cls,
            settings_cls: type[BaseSettings],
    ) -> PydanticBaseSettingsSource | None:
        """

        Get the YAML settings source.

        """
        return None


class Base(BaseCLI):
    """Settings base supporting init, CLI, environment, dotenv, and YAML sources."""

    paths: ClassVar = paths
    config: Path | None = None
    env: Path | None = None

    @classmethod
    def get_init_source(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
    ) -> PydanticBaseSettingsSource | None:
        """

        Enable values passed during initialization.

        """
        return init_settings

    @classmethod
    def get_dotenv_source(
            cls,
            settings_cls: type[BaseSettings],
    ) -> PydanticBaseSettingsSource | None:
        """

        Read settings from the configured dotenv file.

        """
        path = cls.find_env_file()
        if not path:
            return None
        return DotEnvSettingsSource(
            settings_cls,
            env_file=path,
            env_prefix=cls.get_env_prefix(),
            env_nested_delimiter=cls.ENV_NESTED_DELIMITER,
        )

    @classmethod
    def get_yaml_source(
            cls,
            settings_cls: type[BaseSettings],
    ) -> PydanticBaseSettingsSource | None:
        """

        Read settings from the configured YAML script file.

        """
        path = cls.find_yaml_file()
        if not path:
            return None
        return YamlScriptConfigSettingsSource(settings_cls, yaml_file=path)

    @classmethod
    def find_yaml_file(cls) -> Path:
        """

        Overridable find YAML config file method

        """

        class ConfigPathOverride(BaseCLI, cli_parse_args=True, cli_ignore_unknown_args=True):
            """

            Check if the YAML file location has been overridden. If so, we'll provide that location as the source.

            """
            config: Path | None = None

        config_override = ConfigPathOverride()
        if config_override.config:
            return config_override.config

        return cls.paths.settings

    @classmethod
    def find_env_file(cls) -> Path:
        """

        Find the overridden dotenv file, or default to the repository root/current working directory.

        """

        class EnvPathOverride(BaseCLI, cli_parse_args=True, cli_ignore_unknown_args=True):
            env: Path | None = None

        env_override = EnvPathOverride()
        if env_override.env:
            return env_override.env

        return cls.paths.env

    @classmethod
    def get_env_prefix(cls):
        """

        Get environment variable prefix, which depends on whether the package is a namespace/singleton.

        """
        if cls.paths.is_namespace:
            stem = f'{cls.paths.org}_{cls.paths.name}'
        else:
            stem = f'{cls.paths.name}'

        prefix = f'{stem}{cls.ENV_NESTED_DELIMITER}'.upper()
        return prefix

    @property
    def version(self):
        """

        Read version from package metadata.

        """
        return self.paths.metadata.version
