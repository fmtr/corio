from dataclasses import dataclass
from typing import Any

import pygit2 as vcs

from corio import strings
from corio.infra.project import Project
from corio.path import Path


@dataclass
class ReleaseRepoFixture:
    project: Project
    path_repo: Path
    path_remote: Path
    path_editable: Path
    main_head: str
    release_head: str
    tags: set[str]

    @classmethod
    def create(
        cls,
        root: Path,
        *,
        editable_version: str = "2.6.4",
        current_version: str = "8.3.1",
        with_tests: bool = True,
        with_changelog: bool = True,
        with_addon: bool = True,
        test_envs: bool = False,
        pre: bool | None = False,
        pinned: str | None = None,
        tag_current: bool = True,
        tag_next: bool = False,
    ) -> "ReleaseRepoFixture":
        path_repo = root / "release-target"
        path_editable = root / "editable_support"
        path_remote = root / "origin.git"
        path_repo.mkdir()
        path_editable.mkdir()

        signature = vcs.Signature("Fixture Author", "fixture@example.invalid")
        repository = cls._init_repository(path_repo)
        cls._write_target(path_repo, "8.3.0", with_tests, with_changelog, with_addon, test_envs)
        base_release = cls._commit(repository, signature, "Initial package release", None)
        cls._tag(repository, signature, "v8.3.0", base_release)

        (path_repo / "release_target" / "service.py").write_text(
            "value = 'first history update'\n",
            encoding="utf-8",
        )
        first_history = cls._commit(repository, signature, "Add service behavior", base_release)

        cls._write_target(path_repo, current_version, with_tests, with_changelog, with_addon, test_envs)
        latest_release = cls._commit(
            repository,
            signature,
            f"Release version {current_version}",
            first_history,
        )
        if tag_current:
            cls._tag(repository, signature, f"v{current_version}", latest_release)
        repository.create_branch("release", latest_release)

        (path_repo / "release_target" / "service.py").write_text(
            "value = 'second history update'\n",
            encoding="utf-8",
        )
        if with_changelog:
            (path_repo / "docs" / "changelog" / "changelog.md").write_text(
                "- A synthetic unreleased change.\n",
                encoding="utf-8",
            )
        main_head = cls._commit(repository, signature, "Add another feature", latest_release)

        cls._write_editable(path_editable, editable_version, signature)

        tags = {"v8.3.0"}
        if tag_current:
            tags.add(f"v{current_version}")
        if tag_next:
            cls._tag(repository, signature, "v8.3.2", main_head)
            tags.add("v8.3.2")

        bare = vcs.init_repository(str(path_remote), bare=True)
        origin = repository.remotes.create("origin", str(path_remote))
        push_specs = [
            "refs/heads/main:refs/heads/main",
            "refs/heads/release:refs/heads/release",
            *(f"refs/tags/{tag}:refs/tags/{tag}" for tag in sorted(tags)),
        ]
        origin.push(push_specs)
        bare.set_head("refs/heads/main")
        repository.config["branch.main.remote"] = "origin"
        repository.config["branch.main.merge"] = "refs/heads/main"

        return cls(
            project=Project(path=path_repo, pre=pre, pinned=pinned),
            path_repo=path_repo,
            path_remote=path_remote,
            path_editable=path_editable,
            main_head=str(main_head.id),
            release_head=str(latest_release.id),
            tags=tags,
        )

    @staticmethod
    def _init_repository(path: Path) -> Any:
        repository = vcs.init_repository(str(path), bare=False)
        repository.set_head("refs/heads/main")
        repository.config["user.name"] = "Fixture Author"
        repository.config["user.email"] = "fixture@example.invalid"
        return repository

    @staticmethod
    def _commit(repository: Any, signature: Any, message: str, parent: Any | None) -> Any:
        index = repository.index
        index.add_all()
        index.write()
        tree = index.write_tree()
        parents = [] if parent is None else [parent.id]
        commit_id = repository.create_commit(
            "refs/heads/main",
            signature,
            signature,
            message,
            tree,
            parents,
        )
        return repository[commit_id]

    @staticmethod
    def _tag(repository: Any, signature: Any, name: str, commit: Any) -> None:
        repository.create_tag(
            name,
            commit.id,
            vcs.GIT_OBJECT_COMMIT,
            signature,
            f"Release {name}",
        )

    @classmethod
    def _write_target(
        cls,
        root: Path,
        version: str,
        with_tests: bool,
        with_changelog: bool,
        with_addon: bool,
        test_envs: bool,
    ) -> None:
        package = root / "release_target"
        package.mkdir(parents=True, exist_ok=True)
        marker = package / "pyproject.package.toml"
        if not marker.is_symlink():
            marker.symlink_to("../pyproject.toml")
        (package / "__init__.py").write_text("", encoding="utf-8")
        service = package / "service.py"
        if not service.exists():
            service.write_text("value = 'initial'\n", encoding="utf-8")
        (root / "README.md").write_text("# Release fixture\n", encoding="utf-8")
        (root / "LICENSE").write_text("Synthetic license text.\n", encoding="utf-8")
        (root / "pyproject.toml").write_text(
            strings.trim(f"""
                [project]
                name = "release_target"
                version = "{version}"
                description = "Synthetic release fixture"
                readme = "README.md"

                [tool.corio.metadata]
                version = "{version}"
                description = "Synthetic release fixture"
                keywords = ["synthetic"]
                editables = ["editable_support"]
                test_envs = {str(test_envs).lower()}

                [tool.corio.dependencies]
                install = ["editable_support[core]"]
                test = ["pytest"]
                api = ["editable_support[api]", "httpx"]
                service = ["editable_support[service]", "sqlalchemy"]
            """),
            encoding="utf-8",
        )
        if test_envs:
            (package / "api.py").write_text(
                strings.trim("""
                    value = 'synthetic api'
                """),
                encoding="utf-8",
            )
        if with_tests:
            tests = package / "tests"
            tests.mkdir(exist_ok=True)
            test_modules = ["api", "service"] if test_envs else ["probe"]
            for module in test_modules:
                test_source = strings.trim(f"""
                    def test_{module}():
                        assert True
                """)
                (tests / f"test_{module}.py").write_text(
                    test_source,
                    encoding="utf-8",
                )
        if with_changelog:
            cls._write_changelog_release(root, version)
        if with_addon:
            cls._write_addon_config(root, version)

    @staticmethod
    def _write_changelog_release(root: Path, version: str) -> None:
        path_changelog = root / "docs" / "changelog"
        path_changelog.mkdir(parents=True, exist_ok=True)
        (path_changelog / f"{version}.md").write_text(
            f"- Release {version} history.\n",
            encoding="utf-8",
        )
        path_latest = root / "CHANGELOG.md"
        path_latest.unlink(missing_ok=True)
        path_latest.symlink_to(f"docs/changelog/{version}.md")

    @staticmethod
    def _write_addon_config(root: Path, version: str) -> None:
        path_config = root / "ha" / "addon" / "config.yaml"
        path_config.parent.mkdir(parents=True, exist_ok=True)
        path_config.write_text(
            strings.trim(f"""
                name: Release fixture
                version: "{version}"
            """),
            encoding="utf-8",
        )

    @classmethod
    def _write_editable(cls, root: Path, version: str, signature: Any) -> None:
        package = root / "editable_support"
        package.mkdir()
        (package / "pyproject.package.toml").symlink_to("../pyproject.toml")
        (package / "__init__.py").write_text("", encoding="utf-8")
        cls._write_editable_project(root, "2.6.3")
        repository = cls._init_repository(root)
        initial = cls._commit(repository, signature, "Initial editable package release", None)
        cls._tag(repository, signature, "v2.6.3", initial)
        cls._write_editable_project(root, version)
        latest = cls._commit(repository, signature, f"Release version {version}", initial)
        cls._tag(repository, signature, f"v{version}", latest)

    @staticmethod
    def _write_editable_project(root: Path, version: str) -> None:
        (root / "pyproject.toml").write_text(
            strings.trim(f"""
                [project]
                name = "editable_support"
                version = "{version}"
                description = "Synthetic editable dependency"
                readme = "README.md"

                [project.optional-dependencies]
                core = []
                api = ["httpx"]
                service = ["sqlalchemy"]

                [tool.corio.metadata]
                version = "{version}"
                description = "Synthetic editable dependency"
            """),
            encoding="utf-8",
        )
        (root / "README.md").write_text("# Editable fixture\n", encoding="utf-8")
