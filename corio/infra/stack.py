from functools import cached_property

from corio import env
from corio.constants import Constants
from corio.docker import DockerClient
from corio.infra.project import Project
from corio.inherit import Inherit
from corio.logs import logger, sanitize


class Stack(Inherit[Project]):
    """Base for the single production container image of a project."""

    @cached_property
    def cls(self):
        return self.__class__

    @cached_property
    def client(self):
        return DockerClient(client_call=["podman"])


class Production(Stack):
    """Build and optionally publish a production image from a wheel."""

    @cached_property
    def token(self):
        return env.get(Constants.CONTAINER_INDEX_PUBLIC_TOKEN_KEY)

    @cached_property
    def entrypoint(self):
        return self.name_dash

    @cached_property
    def path_containerfile(self):
        from corio.paths import paths
        return paths.assets / "Containerfile"

    @cached_property
    def path_wheel(self):
        wheels = list(self.releaser.path.glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(
                f'Expected exactly one wheel in "{self.releaser.path}", found {len(wheels)}.'
            )
        return wheels[0]

    @cached_property
    def tags_public(self):
        tags = [f"{Constants.ORG_NAME}/{self.name}:{self.tag}"]
        if not self.versions.is_pre:
            tags.append(f"{Constants.ORG_NAME}/{self.name}:latest")
        return tags

    @cached_property
    def tags_image(self):
        tags = [f"{self.name}:{self.tag}"]
        if self.paths.metadata.is_dockerhub:
            tags.extend(self.tags_public)
        return tags

    @logger.instrument("Building production image for project {self.name}...")
    def build(self):
        build_args = {
            "WHEEL": self.path_wheel.name,
            "PACKAGE": self.paths.name_ns,
            "ENTRYPOINT": self.entrypoint,
        }
        for line in self.client.build(
                file=str(self.path_containerfile),
                context_path=self.releaser.path,
                build_args=build_args,
                tags=self.tags_image,
                load=True,
                progress="plain",
                stream_logs=True,
        ):
            logger.info(sanitize(line))

    def push(self):
        self.client.login(username=Constants.ORG_NAME, password=self.token)
        for image_tag in self.tags_public:
            with logger.span(f'Pushing image "{image_tag}"'):
                for _, line_bytes in self.client.push(image_tag, stream_logs=True):
                    logger.info(sanitize(line_bytes.decode()))
