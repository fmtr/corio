import shutil
import subprocess
from functools import cached_property

import build
import pygit2 as vcs
import twine.settings
from mkdocs.__main__ import cli
from twine.commands.upload import upload as twine_upload

from corio.iterator import IndexList

gh_deploy = cli.commands["gh-deploy"].callback
serve = cli.commands["serve"].callback

from corio import env as env
from corio import https as https
from corio.constants import Constants
from corio.infra.project import Project
from corio.inherit import Inherit
from corio.logs import logger, sanitize
from corio.path import Path


class Releaser(Inherit[Project]):
    """

    Manages the release process for a project.

    The release process consists of two main phases:

    1. Repository operations:
       - Fetch latest changes from remote
       - Increment version numbers in relevant files

    2. Distribution and publishing:
       - Create GitHub release (for both public and private repositories)
       - Build Python packages (wheel and sdist)
       - Upload to package indexes (private registry always, PyPI if configured)

    """

    @logger.instrument("Releasing {self.paths.name_ns}...")
    def run(self, increment: bool = True, build: bool = False, release: bool = True, cache: bool = True):

        from corio.infra.stack import ProductionPrivate, ProductionPublic

        is_passed = self.tester.run()
        if not is_passed:
            if self.versions.is_pre:
                logger.warning(f"Tests failed, but release is pre-release ({self.version.prerelease}). Continuing.")
            else:
                raise RuntimeError("Tests failed. Aborting release.")

        if increment:
            self.repo.fetch()
            self.increment()
            self.repo.push()
            self.repo.fetch()

        stack_types = []
        if build:
            stack_types.append(ProductionPrivate)
        if self.paths.metadata.is_dockerhub:
            stack_types.append(ProductionPublic)

        for stack_type in stack_types:
            stack = self.stacks.cls[stack_type]
            stack.build(cache=cache)
            stack.push()

        if release:
            self.package()
            self.release()

    @property
    def message(self):
        return f"Release version {self.version}"

    @logger.instrument("Incrementing version numbers {self.repo.origin.url}...")
    def increment(self):
        """

        Increment version numbers in project files, create a new commit, and rebase the release branch.
        
        """
        repo = self.repo

        main_ref = repo.lookup_reference("refs/heads/main")  # todo raise if not main?
        parent = main_ref.peel(vcs.Commit)

        # Make sure we're building on main's HEAD (not whatever HEAD currently is).
        index = repo.index
        index.read_tree(parent.tree)

        # Apply incrementors (they edit files in the working tree), then stage results.
        for incrementor in self.incrementors:
            paths = incrementor.apply()
            if not paths:
                continue
            if not isinstance(paths, list):
                paths = [paths]

            for path in paths:
                rel = str(Path(path).relative_to(self.paths.repo))
                index.add(rel)

        index.write()
        tree = index.write_tree(repo)

        commit_id = repo.create_commit(
            main_ref.name,
            repo.default_signature,
            repo.default_signature,
            self.message,
            tree,
            [parent.id],
        )

        try:
            repo.create_tag(
                self.tag,
                commit_id,
                vcs.GIT_OBJECT_COMMIT,
                repo.default_signature,
                self.message,
            )
        except Exception as exception:
            logger.warning(f"Failed to create tag: {exception}")

        branch_name = "release"
        ref_name = f"refs/heads/{branch_name}"
        try:
            release_ref = repo.lookup_reference(ref_name)
        except KeyError:
            target = repo.head.peel(vcs.Commit)
            release_ref = repo.create_branch(branch_name, target)

        release_commit = release_ref.peel(vcs.Commit)
        if repo.merge_base(commit_id, release_commit.id) != release_commit.id:
            raise RuntimeError("release has diverged from main")
        release_ref.set_target(commit_id)

        return commit_id

    @cached_property
    def path(self):
        return Path.temp() / f"{self.name}-dist"

    @cached_property
    def token(self):
        return env.get(Constants.GITHUB_TOKEN_KEY)

    @cached_property
    def incrementors(self):
        from corio.infra.incrementor_pyproject import IncrementorPyproject

        return IndexList[Incrementor](
            [
                IncrementorPyproject(self),
                IncrementorHomeAssistantAddon(self),
                IncrementorChangelog(self),
            ]
        )

    @cached_property
    def packagers(self):
        return [PackageWheel(self), PackageSourceDistribution(self)]

    @cached_property
    def releases(self):
        releases = [
            ReleaseGithub(self),
            ReleasePackageIndexPrivate(self),
            ReleaseDocumentation(self)

        ]

        if self.paths.metadata.is_pypi:
            release = ReleasePackageIndexPublic(self)
            releases.append(release)

        return releases

    @cached_property
    def tester(self):
        return Tester(self)

    def release(self):
        for release in self.releases:
            release.release()


    def package(self):
        if self.path.exists():
            logger.info(f"Package directory already exists: {self.path}. Will be removed.")
            shutil.rmtree(self.path)

        self.path.mkdir(parents=True)

        for packager in self.packagers:
            packager.package()


class Incrementor(Inherit[Releaser]):

    @property
    def cls(self):
        return self.__class__

    def apply(self) -> Path | list[Path] | None:
        raise NotImplementedError





class IncrementorHomeAssistantAddon(Incrementor):
    DESC = 'Home Assistant Add-On config file'

    @cached_property
    def path(self):
        return self.paths.ha_addon_config

    @logger.instrument('Incrementing {self.DESC} version "{self.path}"...')
    def apply(self) -> Path | list[Path]:

        if not self.path.exists():
            logger.info(f"{self.DESC} not found: {self.path}. Skipping.")
            return None

        if self.versions.is_pre:
            logger.warning(f"Release is pre-release ({self.version.prerelease}). Skipping {self.DESC}.")
            return None

        data = self.path.read_yaml()
        data['version'] = str(self.version)
        self.path.write_yaml(data)
        return self.path


class IncrementorChangelogSymlink(Incrementor):

    @property
    def src(self):
        raise NotImplementedError

    @property
    def dest(self):
        return self.paths.docs_changelog.with_stem(f'{self.version}')

    def apply(self) -> Path | list[Path] | None:
        if not self.dest.exists():
            logger.info(f"Symlink dest not found: {self.dest}. Skipping.")
            return None

        dest = self.dest.relative_to(self.paths.repo)

        self.src.unlink(missing_ok=True)
        self.src.symlink_to(dest)

        return self.src


class IncrementorChangelog(IncrementorChangelogSymlink):
    DESC = 'Changelog'

    @property
    def src(self):
        return self.paths.changelog


    @logger.instrument('Incrementing {self.DESC} "{self.path}"...')
    def apply(self) -> Path | list[Path] | None:
        path = self.paths.docs_changelog
        if not path.exists():
            logger.info(f"New changelog not found: {path}. Skipping.")
            return None

        if self.versions.is_pre:
            logger.warning(f"Release is pre-release ({self.version.prerelease}). Skipping {self.DESC}.")
            return None

        logger.info(f"Version tagging Changelog: {path} {Constants.ARROW_RIGHT} {self.dest}")
        path.rename(self.dest)

        paths = [self.dest, super().apply()]
        return paths


class Packager(Inherit[Releaser]):
    """
    
    Base class for packaging operations.
    
    """
    TYPE = None

    def package(self):
        builder = build.ProjectBuilder(str(self.paths.repo))
        with logger.span(f'Building {self.TYPE} distribution...'):
            path = builder.build(self.TYPE, str(self.path))
            logger.info(f'Build complete: {path}')

        self.cleanup()

    def cleanup(self):

        patterns = '*.egg-info', 'dist', 'build'

        with logger.span(f'Cleaning up after {self.TYPE} build...'):
            for pattern in patterns:
                for path in self.paths.repo.glob(pattern):
                    with logger.span(f'Removing {path}...'):
                        shutil.rmtree(path)


class PackageWheel(Packager):
    """
    
    Package as Python wheel.
    
    """
    TYPE = 'wheel'


class PackageSourceDistribution(Packager):
    """
    
    Package as source distribution.
    
    """
    TYPE = 'sdist'


class Release(Inherit[Releaser]):
    """
    
    Base class for release operations.
    
    """
    def release(self):
        raise NotImplementedError


class ReleaseGithub(Release):
    """
    
    Release to GitHub.
    
    """

    @property
    def url(self):
        return f"{self.repo_url}/compare/v{self.versions.old}...v{self.versions.new}"

    @property
    def body(self):
        path_changelog = self.incrementors.cls[IncrementorChangelog].dest
        if path_changelog.exists():
            return path_changelog.read_text()
        else:
            return f'**Full Changelog**: [{self.versions.old} {Constants.ARROW_RIGHT} {self.versions.new}]({self.url})'

    def release(self):
        url = f"{self.repo_api_url}/releases"
        name = f'Release {self.tag}'

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json"
        }



        payload = {
            "tag_name": self.tag,
            "name": name,
            "body": self.body,
            "draft": False,
            "prerelease": self.versions.is_pre
        }

        with logger.span(f'Creating release "{name}"...'):
            response = https.client.post(url, json=payload, headers=headers)

        response.raise_for_status()

        data = response.json()
        url = data['html_url']
        logger.info(f"Release created: {url} Changes: {self.url}")


class ReleasePackageIndex(Release):
    """
    
    Base class for package index releases.
    
    """
    
    TOKEN_KEY = None
    URL = None
    USERNAME = None
    NAME = None

    @cached_property
    def token(self):
        return env.get(self.TOKEN_KEY)

    @cached_property
    def settings(self):
        return twine.settings.Settings(
            repository_name=self.NAME,
            repository_url=self.URL,
            username=self.USERNAME,
            password=self.token,
            non_interactive=True,
            verbose=True
        )

    def warn(self):
        pass

    def release(self):
        with logger.span(f'Uploading package to PyPI index ({self.URL}) as {self.USERNAME}...'):
            self.warn()
            twine_upload(self.settings, [f'{self.path}/*'])


class ReleasePackageIndexPrivate(ReleasePackageIndex):
    """
    
    Release to private package index.
    
    """
    TOKEN_KEY = Constants.PACKAGE_INDEX_PRIVATE_TOKEN_KEY
    URL = Constants.PACKAGE_INDEX_PRIVATE_URL
    USERNAME = Constants.ORG_NAME


class ReleasePackageIndexPublic(ReleasePackageIndex):
    """
    
    Release to public package index, namely PyPI.
    
    """
    TOKEN_KEY = Constants.PACKAGE_INDEX_PUBLIC_TOKEN_KEY
    URL = None
    USERNAME = '__token__'
    NAME = "pypi"

    def warn(self):
        logger.error(f'Project "{self.paths.name_ns}" is being pushed to a PUBLIC Package Index!')


class ReleaseDocumentation(Release):

    @property
    def data(self):
        import io

        from material.extensions.emoji import twemoji, to_svg

        return dict(
            config_file=io.StringIO(""),
            site_dir='site',
            docs_dir=str(self.paths.docs),

            site_name=self.paths.name_ns,
            site_description=self.paths.metadata.description,
            repo_url=self.repo_url,
            repo_name=self.repo_name,
            theme={
                "name": "material",
                "features": [
                    "navigation.indexes",
                    "content.code.annotate",
                    "content.code.copy",
                ],
            },
            plugins=[
                "search",
                {"include_dir_to_nav": {"reverse_sort_file": True}},
                {
                    "mkdocstrings": {
                        "handlers": {
                            "python": {
                                "options": {
                                    "show_source": True,
                                }
                            }
                        }
                    }
                },
            ],
            markdown_extensions=[
                "admonition",
                "attr_list",
                "md_in_html",
                "pymdownx.superfences",
                {"pymdownx.highlight": {"pygments_lang_class": True}},
                {"pymdownx.snippets": {"check_paths": True}},

                {"pymdownx.tabbed": {"alternate_style": True}},
                {"pymdownx.emoji": {"emoji_index": twemoji, "emoji_generator": to_svg}},
            ],
            extra={
                "version": {"provider": "mike"},
            },
        ) | self.paths.metadata.docs

    @property
    def message(self):
        return f"Release documentation version {self.version}"

    def deploy(self):
        result = gh_deploy(
            clean=True,
            message=self.message,
            remote_branch="docs",
            remote_name="origin",
            force=True,
            no_history=False,
            ignore_version=True,
            shell=False,
            **self.data
        )
        return result

    def serve(self, host: str = '0.0.0.0', port: int = 8180, livereload: bool = True):
        dev_addr = f"{host}:{port}"
        data = dict(self.data)
        data.pop("site_dir", None)
        return serve(
            dev_addr=dev_addr,
            livereload=livereload,
            **data,
        )

    def release(self):
        if not self.paths.docs.exists():
            logger.info(f"No documentation found at {self.paths.docs}. Skipping...")
            return

        with self.paths.repo.chdir:
            self.deploy()


class Tester(Inherit[Releaser]):
    TEST_FILENAME_PREFIX = "test_"
    TEST_FILENAME_SUFFIX = ".py"
    TOX_REQUIRES = ["tox>=4.22", "tox-uv>=1"]

    @cached_property
    def path_config_dir(self) -> Path:
        return Path.temp() / f"{self.name}-tox"

    @cached_property
    def path_config(self) -> Path:
        return self.path_config_dir / "tox.toml"

    @cached_property
    def dependencies(self) -> dict[str, list[str]]:
        data = self.paths.pyproject_repo.read_toml()
        table = data.get("tool", {}).get("corio", {}).get("dependencies", {})
        dependencies = {
            str(key): [str(value) for value in values]
            for key, values in table.items()
            if isinstance(values, list)
        }
        return dependencies

    @cached_property
    def modules(self) -> list[str]:
        if not self.paths.tests.exists():
            return []

        modules = []
        for path in sorted(self.paths.tests.glob(f"{self.TEST_FILENAME_PREFIX}*{self.TEST_FILENAME_SUFFIX}")):
            module = path.stem.removeprefix(self.TEST_FILENAME_PREFIX)
            if module:
                modules.append(module)
        return modules


    def get_env(self, name: str, path_tests: Path, extras: list[str]) -> dict:
        if path_tests.is_relative_to(self.paths.repo):
            path_tests = path_tests.relative_to(self.paths.repo)
        env = {
            "description": f"Run {name} tests.",
            "extras": extras,
            "commands": [["python", "-m", "pytest", "-q", str(path_tests)]],
        }
        return env

    @cached_property
    def env(self) -> dict:
        return self.get_env(name=self.paths.name_ns, path_tests=self.paths.tests, extras=["test"])

    @cached_property
    def envs(self) -> dict[str, dict]:
        if not self.paths.metadata.test_envs:
            if not self.modules:
                return {}
            return {self.paths.name_ns: self.env}

        envs = {}
        extras_available = set(self.dependencies.keys())

        for module in self.modules:
            extras = ["test"]
            if module in extras_available:
                extras.insert(0, module)

            path_test = self.paths.tests / f"{self.TEST_FILENAME_PREFIX}{module}{self.TEST_FILENAME_SUFFIX}"
            name = f"{self.paths.name_ns}/{module}"
            envs[name] = self.get_env(name=name, path_tests=path_test, extras=extras)

        return envs

    @cached_property
    def data(self) -> dict:
        data = {
            "requires": self.TOX_REQUIRES,
            "env_list": list(self.envs.keys()),
            "env": self.envs,
        }
        return data

    def write_config(self):
        self.path_config_dir.mkdir(parents=True, exist_ok=True)
        self.path_config.write_toml(self.data)

    def run_subprocess(self) -> int:
        command = [
            "uvx",
            "--with",
            "tox-uv",
            "tox",
            "-c",
            str(self.path_config),
            "--root",
            str(self.paths.repo),
            "--workdir",
            str(self.paths.repo / ".tox"),
            "run",
        ]

        process = subprocess.Popen(
            command,
            cwd=self.paths.repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        assert process.stdout is not None
        for line in process.stdout:
            logger.info(sanitize(line))

        code = process.wait()
        return code

    @logger.instrument('Running test suite for "{self.paths.name_ns}"...')
    def run(self) -> bool:
        if not self.envs:
            logger.warning(f'No tests found under "{self.paths.tests}". Skipping.')
            return True

        logger.info(f'Generating temporary tox config: "{self.path_config}"')
        self.write_config()
        try:
            code = self.run_subprocess()
        finally:
            self.path_config.unlink(missing_ok=True)
            shutil.rmtree(self.path_config_dir, ignore_errors=True)

        if code == 0:
            logger.info("All test environments passed.")
            return True

        logger.error(f"Test suite failed with exit code {code}.")
        return False
