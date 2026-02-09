import shutil
from functools import cached_property

import build
import pygit2 as vcs
import twine.settings
from mkdocs.__main__ import cli
from twine.commands.upload import upload as twine_upload

from fmtr.tools.iterator_tools import IndexList

gh_deploy = cli.commands["gh-deploy"].callback



from fmtr.tools import environment_tools as env
from fmtr.tools import http_tools as http
from fmtr.tools.constants import Constants
from fmtr.tools.infrastructure_tools.project import Project
from fmtr.tools.inherit_tools import Inherit
from fmtr.tools.logging_tools import logger
from fmtr.tools.path_tools import Path


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
    def run(self):
        self.repo.fetch()
        self.increment()
        self.repo.push()
        self.repo.fetch()

        if self.paths.metadata.is_dockerhub:
            from fmtr.tools.infrastructure_tools.stack import ProductionPublic
            stack = self.stacks.cls[ProductionPublic]
            stack.build()
            stack.push()

        from fmtr.tools.infrastructure_tools.stack import ProductionPrivate
        stack = self.stacks.cls[ProductionPrivate]
        stack.build()

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
        return Path.temp() / self.name

    @cached_property
    def token(self):
        return env.get(Constants.GITHUB_TOKEN_KEY)

    @cached_property
    def incrementors(self):
        return IndexList[Incrementor](
            [
                IncrementorVersion(self),
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


class IncrementorVersion(Incrementor):

    @cached_property
    def path(self):
        return self.paths.metadata.path


    def apply(self) -> Path | list[Path] | None:
        old = self.versions.old
        new = self.bump(old)

        logger.info(f'Incrementing metadata file "{self.path}" {old} {Constants.ARROW_RIGHT} {new}...')

        self.paths.metadata.version = str(new)
        self.paths.metadata.write()
        return self.path

    def bump(self, version):

        if self.versions.pinned:
            return self.versions.pinned

        if version.prerelease:
            return version.bump_prerelease()
        return version.bump_patch()

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

    @property
    def src(self):
        return self.paths.changelog


    @logger.instrument('Incrementing Changelog "{self.path}"...')
    def apply(self) -> Path | list[Path] | None:
        path = self.paths.docs_changelog
        if not path.exists():
            logger.info(f"New changelog not found: {path}. Skipping.")
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
        return f"https://github.com/{Constants.ORG_NAME}/{self.paths.name_ns}/compare/v{self.versions.old}...v{self.versions.new}"

    @property
    def body(self):
        path_changelog = self.incrementors.cls[IncrementorChangelog].dest
        if path_changelog.exists():
            return path_changelog.read_text()
        else:
            return f'**Full Changelog**: [{self.versions.old} {Constants.ARROW_RIGHT} {self.versions.new}]({self.url})'

    def release(self):
        url = f"https://api.github.com/repos/{Constants.ORG_NAME}/{self.paths.name_ns}/releases"  # todo add gh org to meta.json
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
            response = http.client.post(url, json=payload, headers=headers)

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

        from mkdocs.config import load_config
        from material.extensions.emoji import twemoji, to_svg

        return dict(
            config_file=io.StringIO(""),
            site_dir='site',
            docs_dir=str(self.paths.docs),

            site_name=self.paths.name_ns,
            theme={
                "name": "material",
                "features": [
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
            nav=self.nav or [
                {"Home": "index.md"},
                {"Changelog": "changelog/"},
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

    def release(self):
        if not self.paths.docs.exists():
            logger.info(f"No documentation found at {self.paths.docs}. Skipping...")
            return

        with self.paths.repo.chdir:
            self.deploy()
