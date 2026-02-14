import sys
from datetime import datetime
from functools import cached_property
from itertools import chain
from typing import List, Dict, Any, Callable, Optional

from fmtr.tools.constants import Constants
from fmtr.tools.path_tools import PackagePaths
from fmtr.tools.path_tools.path_tools import FromCallerMixin


class Setup(FromCallerMixin):
    """

    Abstract canonical pacakge setup for setuptools.

    """
    AUTHOR = Constants.ORG_NAME_FRIENDLY
    AUTHOR_EMAIL = 'innovative.fowler@mask.pro.fmtr.dev'

    REQUIREMENTS_ARG = 'requirements'

    ENTRYPOINT_COMMAND_SEP = '-'
    ENTRYPOINT_FUNCTION_SEP = '_'
    ENTRYPOINT_FUNC_NAME = 'main'

    def __init__(self, dependencies, paths=None, do_setup=True, **kwargs):
        """

        First check if commandline arguments for requirements output exist. If so, print them and return early.
        Otherwise, continue generating data to pass to setuptools.

        """
        self.kwargs = kwargs

        if type(dependencies) is not Dependencies:
            dependencies = Dependencies(**dependencies)
        self.dependencies = dependencies

        requirements_extras = self.get_requirements_extras()

        if requirements_extras:
            self.print_requirements()
            return

        if not paths:
            paths = PackagePaths(path=self.from_caller())
        self.paths = paths

        if do_setup:
            self.setup()
        self


    def get_requirements_extras(self) -> Optional[List[str]]:
        """

        Get list of extras from command line arguments.

        """
        if self.REQUIREMENTS_ARG not in sys.argv:
            return None

        extras_str = sys.argv[-1]
        extras = extras_str.split(',')
        return extras

    def print_requirements(self):
        """

        Output flat list of requirements for specified extras

        """
        reqs = []
        reqs += self.dependencies.install

        for extra in sys.argv[-1].split(','):
            reqs += self.dependencies.extras[extra]
        reqs = '\n'.join(reqs)
        print(reqs)

    @property
    def console_scripts(self) -> List[str]:
        """

        Generate console scripts for the `entrypoint` module - and/or any modules in `entrypoints` sub-package.

        """

        if not self.paths.entrypoints.exists():
            paths_mods = []
        else:
            paths_mods = list(self.paths.entrypoints.iterdir())

        names_mods = [path.stem for path in paths_mods if path.is_file() and path.name != Constants.INIT_FILENAME]
        command_suffixes = [name_mod.replace(self.ENTRYPOINT_FUNCTION_SEP, self.ENTRYPOINT_COMMAND_SEP) for name_mod in names_mods]
        commands = [f'{self.name_command}-{command_suffix}' for command_suffix in command_suffixes]
        paths = [f'{self.paths.name_ns}.{Constants.ENTRYPOINTS_DIR}.{name_mod}:{self.ENTRYPOINT_FUNC_NAME}' for name_mod in names_mods]

        if self.paths.entrypoint.exists():
            commands.append(self.name_command)
            path = f'{self.paths.name_ns}.{self.paths.entrypoint.stem}:{self.ENTRYPOINT_FUNC_NAME}'
            paths.append(path)

        console_scripts = [f'{command} = {path}' for command, path in zip(commands, paths)]

        return console_scripts

    @property
    def scripts(self) -> List[str]:
        """

        Generate list of shell scripts.

        """

        paths = []

        if not self.paths.scripts.exists():
            return paths

        for path in self.paths.scripts.iterdir():
            if path.is_dir():
                continue

            path_rel = path.relative_to(self.paths.repo)
            paths.append(str(path_rel))

        return paths

    @cached_property
    def name_command(self) -> str:
        """

        Name as a command, e.g. `fmtr-tools`

        """
        return self.paths.name_ns.replace('.', self.ENTRYPOINT_COMMAND_SEP)

    @property
    def author(self) -> str:
        """

        Create appropriate author string

        """
        if self.paths.metadata.is_client:
            return f'{Constants.ORG_NAME_FRIENDLY} on behalf of {self.paths.metadata.org_friendly}'
        return Constants.ORG_NAME_FRIENDLY

    @property
    def long_description(self) -> str:
        """

        Read in README.md

        """
        return self.paths.readme.read_text()

    @property
    def find(self) -> Callable:
        """

        Use the appropriate package finding function from setuptools

        """
        from fmtr.tools import setup

        if self.paths.is_namespace:
            return setup.find_namespace_packages
        else:
            return setup.find_packages

    @property
    def packages(self) -> List[str]:
        """

        Fetch list of packages excluding canonical paths

        """
        excludes = list(Constants.PACKAGE_EXCLUDE_DIRS) + [f'{name}.*' for name in Constants.PACKAGE_EXCLUDE_DIRS if '*' not in name]
        packages = self.find(where=str(self.paths.repo), exclude=excludes)
        return packages

    @property
    def package_dir(self):
        """

        Needs to be relative apparently as absolute paths break during packaging

        """
        if self.paths.is_namespace:
            return {'': '.'}
        else:
            return None

    @property
    def package_data(self):
        """

        Default package data is the version and meta files

        """
        return {self.paths.name_ns: [Constants.FILENAME_VERSION, Constants.FILENAME_META]}

    @property
    def url(self) -> str:
        """

        Default to GitHub URL

        """
        return f'https://github.com/{self.paths.metadata.org_github}/{self.paths.name_ns}'

    @property
    def data(self) -> Dict[str, Any]:
        """

        Generate data for use by setuptools

        """
        data = dict(
            name=self.paths.name_ns,
            version=self.paths.metadata.version,
            author=self.author,
            author_email=self.AUTHOR_EMAIL,
            url=self.url,
            license=f'Copyright © {datetime.now().year} {self.paths.metadata.org_friendly}. All rights reserved.',
            description=self.paths.metadata.description,
            long_description=self.long_description,
            long_description_content_type='text/markdown',
            packages=self.packages,
            package_dir=self.package_dir,
            package_data=self.package_data,
            entry_points=dict(
                console_scripts=self.console_scripts,
            ),
            install_requires=self.dependencies.install,
            extras_require=self.dependencies.extras,
            scripts=self.scripts,
        )
        data |= self.paths.metadata.setup
        data |= self.kwargs
        return data

    def setup(self):
        """

        Call setuptools.setup using generated data

        """

        from fmtr.tools import setup

        return setup.setup_setuptools(**self.data)

    def __repr__(self) -> str:
        """

        Show library name

        """
        return f'{self.__class__.__name__}("{self.paths.name_ns}")'

class Tools:
    """

    Helper for downstream libraries to specify lists of `fmtr.tools` extras

    """
    MASK = f'{Constants.LIBRARY_NAME}[{{extras}}]'

    def __init__(self, *extras):
        self.extras = extras

    def __str__(self):
        extras_str = ','.join(self.extras)
        return self.MASK.format(extras=extras_str)

class Dependencies:
    ALL = 'all'
    INSTALL = 'install'

    def __init__(self, **kwargs):
        self.dependencies = kwargs

    def resolve_values(self, key) -> List[str]:
        """

        Flatten a list of dependencies.

        """
        values_resolved = []
        values = self.dependencies[key]

        for value in values:
            if value == key or value not in self.dependencies:
                # Add the value directly if it references itself or is not a dependency key.
                values_resolved.append(str(value))
            else:
                # Recurse into nested dependencies.
                values_resolved += self.resolve_values(value)

        return values_resolved

    @cached_property
    def extras(self) -> Dict[str, List[str]]:
        """

        Flatten dependencies.

        """
        resolved = {key: self.resolve_values(key) for key in self.dependencies.keys()}
        resolved.pop(self.INSTALL, None)
        resolved[self.ALL] = list(set(chain.from_iterable(resolved.values())))
        return resolved

    @cached_property
    def install(self) -> List[str]:
        """

        Get install_requires

        """
        if self.INSTALL in self.dependencies:
            return self.resolve_values(self.INSTALL)
        else:
            return []


if __name__ == '__main__':
    ...
