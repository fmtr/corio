from copy import deepcopy
from functools import cached_property
from itertools import chain

from corio.constants import Constants
from corio.infrastructure_tools.releaser import Incrementor
from corio.iterator_tools import dedupe
from corio.logging_tools import logger
from corio.path_tools import Path
from corio.toml_tools import ensure_table


class IncrementorPyproject(Incrementor):
    AUTHOR_EMAIL = "innovative.fowler@mask.pro.fmtr.dev"
    ENTRYPOINT_COMMAND_SEP = "-"
    ENTRYPOINT_FUNCTION_SEP = "_"
    ENTRYPOINT_FUNC_NAME = "main"
    DEPENDENCIES_SECTION_PATH = ("tool", "corio", "dependencies")

    @cached_property
    def path(self) -> Path:
        return self.paths.pyproject_repo

    @cached_property
    def name_command(self) -> str:
        return self.paths.name_ns.replace(".", self.ENTRYPOINT_COMMAND_SEP)

    def apply(self) -> Path | list[Path] | None:
        if not self.path.exists():
            logger.info(f'pyproject.toml not found: "{self.path}". Skipping.')
            return None

        data = self.path.read_toml()
        original_data = deepcopy(data)

        data = self._enrich_toml(data)
        if data is None:
            return None

        if data == original_data:
            return None

        self.path.write_toml(data)
        return self.path

    @property
    def _author(self) -> str:
        if self.paths.metadata.is_client:
            return f"{Constants.ORG_NAME_FRIENDLY} on behalf of {self.paths.metadata.org_friendly}"
        return Constants.ORG_NAME_FRIENDLY

    @property
    def _url(self) -> str:
        return f"https://github.com/{self.paths.metadata.org_github}/{self.paths.name_ns}"

    @property
    def _package_dir(self):
        if self.paths.is_namespace:
            return {"": "."}
        return None

    @property
    def _package_data(self) -> dict[str, list[str]]:
        return {self.paths.name_ns: [Constants.FILENAME_PYPROJECT_PACKAGE]}

    @cached_property
    def _console_scripts(self) -> list[str]:
        if not self.paths.entrypoints.exists():
            paths_mods = []
        else:
            paths_mods = list(self.paths.entrypoints.iterdir())

        names_mods = [path.stem for path in paths_mods if path.is_file() and path.name != Constants.INIT_FILENAME]
        command_suffixes = [
            name_mod.replace(self.ENTRYPOINT_FUNCTION_SEP, self.ENTRYPOINT_COMMAND_SEP) for name_mod in names_mods
        ]
        commands = [f"{self.name_command}-{command_suffix}" for command_suffix in command_suffixes]
        entrypoint_paths = [
            f"{self.paths.name_ns}.{Constants.ENTRYPOINTS_DIR}.{name_mod}:{self.ENTRYPOINT_FUNC_NAME}"
            for name_mod in names_mods
        ]

        if self.paths.entrypoint.exists():
            commands.append(self.name_command)
            path = f"{self.paths.name_ns}.{self.paths.entrypoint.stem}:{self.ENTRYPOINT_FUNC_NAME}"
            entrypoint_paths.append(path)

        return [f"{command} = {entrypoint}" for command, entrypoint in zip(commands, entrypoint_paths)]

    @cached_property
    def _scripts(self) -> list[str]:
        paths = []
        if not self.paths.scripts.exists():
            return paths

        for path in self.paths.scripts.iterdir():
            if path.is_dir():
                continue
            path_rel = path.relative_to(self.paths.repo)
            paths.append(str(path_rel))
        return paths

    def _flatten_dependencies(self, dependencies: dict[str, list[str]]) -> tuple[list[str], dict[str, list[str]]]:
        def resolve_values(key: str) -> list[str]:
            values_resolved = []
            for value in dependencies[key]:
                if value == key or value not in dependencies:
                    values_resolved.append(str(value))
                else:
                    values_resolved += resolve_values(value)
            return values_resolved

        install = dedupe(resolve_values("install")) if "install" in dependencies else []
        extras = {key: dedupe(resolve_values(key)) for key in dependencies}
        extras.pop("install", None)
        extras["all"] = dedupe(list(chain.from_iterable(extras.values())))
        return install, extras

    def _get_dependencies(self, data) -> dict[str, list[str]]:
        table = data
        for key in self.DEPENDENCIES_SECTION_PATH:
            if key not in table:
                return {}
            table = table[key]

        if table is None:
            return {}
        return {str(key): [str(value) for value in values] for key, values in table.items()}

    def _enrich_toml(self, data):
        old = self.versions.old
        new = self._bump(old)
        logger.info(f'Incrementing version "{self.path}" {old} {Constants.ARROW_RIGHT} {new}...')
        self.paths.metadata.version = str(new)

        metadata = ensure_table(data, ("tool", "corio", "metadata"))
        metadata["version"] = self.paths.metadata.version

        project = ensure_table(data, ("project",))
        project["name"] = self.paths.name_ns
        project["version"] = self.paths.metadata.version
        project["description"] = self.paths.metadata.description
        project["keywords"] = self.paths.metadata.keywords
        project["readme"] = self.paths.readme.name
        project["authors"] = [dict(name=self._author, email=self.AUTHOR_EMAIL)]
        project["license"] = "Apache-2.0"
        if self.paths.license.exists():
            project["license-files"] = [self.paths.license.name]
        elif "license-files" in project:
            del project["license-files"]

        dependencies = self._get_dependencies(data)
        if dependencies:
            install, extras = self._flatten_dependencies(dependencies)
            project["dependencies"] = install
            project["optional-dependencies"] = extras

            if "dev" in extras:
                dependency_groups = ensure_table(data, ("dependency-groups",))
                dependency_groups["dev"] = list(extras["dev"])
        else:
            logger.info(f'No dependencies section found in "{self.path}". Skipping dependency enrichment.')

        urls = ensure_table(project, ("urls",))
        urls["Homepage"] = self._url

        scripts = {}
        for entry in self._console_scripts:
            command, target = entry.split("=", maxsplit=1)
            scripts[command.strip()] = target.strip()
        project["scripts"] = scripts

        setuptools = ensure_table(data, ("tool", "setuptools"))
        package_find = ensure_table(data, ("tool", "setuptools", "packages", "find"))
        package_find["where"] = ["."]
        package_find["include"] = [f"{self.paths.name_ns}*"]
        package_find["namespaces"] = bool(self.paths.is_namespace)

        if self._package_dir:
            setuptools["package-dir"] = self._package_dir
        elif "package-dir" in setuptools:
            del setuptools["package-dir"]

        package_data = ensure_table(setuptools, ("package-data",))
        package_data[self.paths.name_ns] = self._package_data[self.paths.name_ns]

        if self._scripts:
            setuptools["script-files"] = self._scripts
        elif "script-files" in setuptools:
            del setuptools["script-files"]

        return data

    def _bump(self, version):
        if self.versions.pinned:
            return self.versions.pinned

        if version.prerelease:
            return version.bump_prerelease()
        return version.bump_patch()
