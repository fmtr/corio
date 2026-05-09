import pygit2 as vcs
from functools import cached_property
from typing import Any

from corio import version
from corio.inherit import Inherit
from corio.logs import logger
from corio.path import Path


class Repository(vcs.Repository):
    """

    Repository subclass to add some project-specific functionality.

    """
    SSH_DIR = Path().home() / ".ssh"

    def __init__(self, path: Path, project: Any):
        super().__init__(str(path))
        self.project = project


    @cached_property
    def tags(self):
        return Tags(self)

    @property
    def origin(self):
        return self.remotes["origin"]

    @property
    def keypair(self):
        return vcs.Keypair("git", self.SSH_DIR / "id_rsa.pub", self.SSH_DIR / "id_rsa", passphrase=None)

    @property
    def callbacks(self):
        return vcs.RemoteCallbacks(credentials=self.keypair)

    @logger.instrument('Fetching from repo {self.origin.url}...')
    def fetch(self):
        specs = [
            "+refs/heads/*:refs/remotes/origin/*",
            "+refs/tags/*:refs/tags/*",
        ]

        return self.origin.fetch(specs, callbacks=self.callbacks)

    @logger.instrument('Pushing to repo {self.origin.url}...')
    def push(self):
        allowed_heads = {"refs/heads/main", "refs/heads/release"}
        tag_ref = f"refs/tags/{self.project.tag}"

        if tag_ref not in self.references:
            raise RuntimeError(f"Local tag not found: {tag_ref}")

        specs = [
            f"{ref}:{ref}"
            for ref in self.references
                    if ref in allowed_heads
                ] + [f"{tag_ref}:{tag_ref}"]

        return self.origin.push(specs, callbacks=self.callbacks)

    def get_most_recent_release_tag(self, include_pre: bool = True, before=None):
        before_version = None
        if before is not None:
            if isinstance(before, str):
                before = before.removeprefix("v")
                before_version = version.parse(before)
            else:
                before_version = before

        candidates = []
        for tag in self.tags.all:
            if not tag.startswith("v"):
                continue
            text = tag.removeprefix("v")
            parsed = version.parse(text)

            if before_version is not None and parsed >= before_version:
                continue

            if not include_pre and parsed.prerelease:
                continue

            candidates.append(parsed)

        if not candidates:
            return None

        candidates.sort(reverse=True)
        return candidates[0]





class Tags(Inherit[Repository]):

    @property
    def new(self):
        return f"v{self.project.repo.data.new}"

    @property
    def current(self):
        return f"v{self.project.version}"

    def get_tags(self):
        for ref in self.references:
            path = Path(ref)
            if path.parent.name == 'tags':
                yield path.name

    @property
    def all(self):
        return set(self.get_tags())
