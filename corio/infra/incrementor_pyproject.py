from functools import cached_property
from itertools import chain
from packaging.requirements import Requirement, InvalidRequirement
from packaging.utils import canonicalize_name

from corio.constants import Constants
from corio.infra.releaser import Incrementor
from corio.iterator import dedupe
from corio.logs import logger
from corio.path import Path, PackagePaths
from corio.path.path import Metadata
from corio.toml import ensure_table

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

    @cached_property
    def editables(self) -> dict[str, Metadata]:
        data = self.path.read_toml()
        sources = data.get("tool", {}).get("uv", {}).get("sources", {})

        editables = {}
        for key, source in sources.items():
            if not isinstance(source, dict):
                continue
            if not source.get("editable"):
                continue

            source_path = source.get("path")
            if not source_path:
                logger.warning(f'Editable source "{key}" is missing "path". Skipping.')
                continue
            path_repo = (self.paths.repo / str(source_path)).resolve()
            if not path_repo.exists():
                continue

            try:
                paths = PackagePaths(path_repo)
            except Exception as exception:
                logger.warning(f'Failed to resolve editable source at "{path_repo}". Skipping. {exception!r}')
                continue

            metadata = paths.metadata
            if metadata.version_obj.prerelease and not self.versions.is_pre:
                raise ValueError(
                    f'Editable dependency "{paths.name_ns}" is pre-release '
                    f'({metadata.version_obj.prerelease}) while "{self.paths.name_ns}" is release. Refusing to pin.'
                )

            editables[paths.name_ns] = metadata
            editables[canonicalize_name(paths.name_ns)] = metadata

        return editables

    def _pin_editable(self, dep: str) -> str:
        try:
            requirement = Requirement(dep)
        except InvalidRequirement:
            return dep

        if requirement.url:
            return dep

        metadata = self.editables.get(requirement.name)
        if metadata is None:
            metadata = self.editables.get(canonicalize_name(requirement.name))
        if metadata is None:
            return dep

        if requirement.specifier:
            operators = {specifier.operator for specifier in requirement.specifier}
            if operators != {"~="}:
                return dep

        extras = ""
        if requirement.extras:
            extras = f"[{','.join(sorted(requirement.extras))}]"

        marker = ""
        if requirement.marker:
            marker = f"; {requirement.marker}"

        pinned = f"{requirement.name}{extras}~={metadata.version}{marker}"
        logger.info(f'Pinning editable dependency "{dep}" -> "{pinned}".')
        return pinned

    def _process_deps(self, deps: str | list[str]) -> str | list[str]:

        if isinstance(deps, list):
            deps = [self._process_deps(dep) for dep in deps]
            deps = dedupe(deps)
            return deps

        dep = deps
        dep = self._pin_editable(dep)

        return dep

    def apply(self) -> Path | list[Path] | None:
        if not self.path.exists():
            logger.info(f'pyproject.toml not found: "{self.path}". Skipping.')
            return None

        data = self.path.read_toml()

        data = self._enrich_toml(data)
        if data is None:
            return None

        self.path.write_toml(data)
        return self.path

    @property
    def _author(self) -> str:
        if self.paths.metadata.is_client:
            return f"{Constants.ORG_NAME_FRIENDLY} on behalf of {self.paths.metadata.org_friendly}"
        return Constants.ORG_NAME_FRIENDLY

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

        extras = {key: dedupe(resolve_values(key)) for key in dependencies}
        install = extras.pop("install", [])
        extras["all"] = dedupe(list(chain.from_iterable(extras.values())))
        return install, extras

    def _enrich_toml(self, data):
        version = str(self.version)
        logger.info(f'Applying release version "{version}" to "{self.path}"...')

        metadata = ensure_table(data, ("tool", "corio", "metadata"))
        metadata["version"] = version

        project = ensure_table(data, ("project",))
        project["name"] = self.paths.name_ns
        project["version"] = version
        project["description"] = self.paths.metadata.description
        project["keywords"] = self.paths.metadata.keywords
        project["readme"] = self.paths.readme.name
        project["authors"] = [dict(name=self._author, email=self.AUTHOR_EMAIL)]
        project["license"] = "Apache-2.0"
        if self.paths.license.exists():
            project["license-files"] = [self.paths.license.name]
        elif "license-files" in project:
            del project["license-files"]

        deps_corio = data.get("tool", {}).get("corio", {}).get("dependencies", None)
        if deps_corio is not None:
            install, extras = self._flatten_dependencies(deps_corio)
            project["dependencies"] = install
            project["optional-dependencies"] = extras
        else:
            logger.info(f'No dependencies section found in "{self.path}". Skipping dependency enrichment.')

        deps = project.get("dependencies")
        if deps is not None:
            project["dependencies"] = self._process_deps(deps)

        optionals = project.get("optional-dependencies")
        if optionals is not None:
            optionals = {
                key: self._process_deps(values)
                for key, values in optionals.items()
            }
            project["optional-dependencies"] = optionals

            if "dev" in optionals:
                dependency_groups = ensure_table(data, ("dependency-groups",))
                dependency_groups["dev"] = list(optionals["dev"])

        urls = ensure_table(project, ("urls",))
        urls["Homepage"] = self.repo_url

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

        dependencies = project.get("optional-dependencies", {})
        gen = GeneratorTestEnvs(paths=self.paths, optionals=dependencies)

        tox = ensure_table(data, ("tool", "tox"))
        tox["requires"] = gen.TOX_REQUIRES
        tox["env_list"] = list(gen.envs.keys())
        tox["env"] = gen.envs

        return data

class GeneratorTestEnvs:
    TEST_FILENAME_PREFIX = "test_"
    TEST_FILENAME_SUFFIX = ".py"
    TOX_REQUIRES = ["tox>=4.22", "tox-uv>=1"]

    def __init__(self, *, paths, optionals: dict[str, list[str]]):
        self.paths = paths
        self.optionals = optionals

    @cached_property
    def _tests_modules(self) -> list[str]:
        modules = []
        for path in self.paths.path.iterdir():
            if path.is_dir():
                if path.name in {"tests", "__pycache__"}:
                    continue
                module = path.name
            else:
                if path.suffix != self.TEST_FILENAME_SUFFIX:
                    continue
                if path.stem.startswith("_"):
                    continue
                module = path.stem

            path_test = self.get_path_test(module)
            if not path_test.exists():
                continue
            modules.append(module)

        return dedupe(sorted(modules))

    @property
    def deps_test(self):
        return sorted(self.optionals['test'])

    def get_deps(self, name):

        deps = []
        keys = [key for key in self.optionals.keys() if key == name or key.startswith(f"{name}.")]
        for key in keys:
            deps += self.optionals[key]

        deps += self.deps_test

        deps = sorted(dedupe(deps))

        return deps

    def get_path_test(self, module: str) -> Path:
        return self.paths.tests / f"{self.TEST_FILENAME_PREFIX}{module}{self.TEST_FILENAME_SUFFIX}"

    def get_env(self, name, deps, path):
        path=path.relative_to(self.paths.repo)
        return {
            name: dict(
                description=f"Run {name} tests.",
                deps=deps,
                commands=[["python", "-m", "pytest", "-q", str(path)]],
            )
        }

    @cached_property
    def env(self):
        name = self.paths.name_ns
        path_tests = self.paths.tests
        return self.get_env(name, self.deps_test, path_tests)

    @cached_property
    def envs(self) -> dict[str, dict]:

        if not self._tests_modules:
            return {}

        if not self.paths.metadata.test_envs:
            return self.env

        envs = {}
        for module in self._tests_modules:
            path_test = self.get_path_test(module)
            envs |= self.get_env(module, self.get_deps(module), path_test)
        return envs
