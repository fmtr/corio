from functools import cached_property

from fmtr.tools import environment_tools as env
from fmtr.tools.constants import Constants
from fmtr.tools.docker_tools import DockerClient
from fmtr.tools.infrastructure_tools.project import Project
from fmtr.tools.inherit_tools import Inherit
from fmtr.tools.iterator_tools import IndexList
from fmtr.tools.logging_tools import logger
from fmtr.tools.merging_tools import merge
from fmtr.tools.path_tools import Path


class Stack(Inherit[Project]):
    """
    
    Represents the Docker stack for a project. Manages different deployment targets including:

    - Development compose stack with docker-compose configuration
    - Build targets for dev and production environments

    """

    @cached_property
    def cls(self):
        return self.__class__

    @cached_property
    def token(self):
        return env.get(Constants.CONTAINER_INDEX_PUBLIC_TOKEN_KEY)

    @cached_property
    def channel(self):
        return self.__class__.__name__.lower()

    @cached_property
    def path_compose(self):
        return Path.temp() / f'{self.name}.yml'

    @cached_property
    def client(self):
        return DockerClient(context=self.context, compose_files=self.path_compose)

    @classmethod
    def get_all(self):
        return [Development]

    @cached_property
    def composes_all(self):
        return IndexList[Compose](cls(self) for cls in (Compose, ComposeDocumentDatabase,))

    @cached_property
    def compose_data(self):
        """

        Merge Compose data for all project services

        """
        data = []
        for service in [Compose.NAME] + self.services:
            compose = self.composes_all.NAME[service]
            data.append(compose.data)
        data = merge(*data)
        return data

    @cached_property
    def tags_image(self):
        return [
            f'{self.name}:{self.channel}-{self.extras_str}',
            f'{self.name}:{self.channel}-{self.extras_str}-{self.tag}'
        ]

    @cached_property
    def entrypoint(self):
        # f"{self.org}-{self.package}-{self.entrypoint}" todo allow entrypoint from self.paths.entrypoints.
        return self.name_dash

    @logger.instrument('Building image for project {self.name} on channel {self.channel}...')
    def build(self):
        """

        Builds a Docker image using the specified build arguments, tags, and contexts.

        """

        build_args = dict(
            NAME=self.paths.name_ns,
            VERSION=str(self.versions.new),
            ORG=self.org,
            PACKAGE=self.paths.name,
            BASE=self.paths.metadata.base,
            EXTRAS=self.extras_str,
            ENTRYPOINT=self.entrypoint,
            SCRIPTS=self.scripts_str,
        )

        contexts = dict(
            package=str(self.paths.repo)
        )

        for line in self.client.build(
                build_contexts=contexts,
                file="Dockerfile",
                context_path=self.paths.repo,
                build_args=build_args,
                tags=self.tags_image,
                target=self.channel,
                load=True,
                progress="plain",
                stream_logs=True,
        ):
            logger.info(line.rstrip())


class Development(Stack):
    """

    Represents the development environment stack with channel-specific configuration

    """

    def recreate(self):
        """

        Recreates a compose deployment

        """

        self.build()

        data = self.compose_data

        with logger.span(f'Writing compose file to "{self.path_compose}"'):
            self.path_compose.write_yaml(data)

        self.client.compose.up(
            detach=True,
            force_recreate=True,

        )


class ProductionPrivate(Stack):
    @cached_property
    def channel(self):
        return 'production'

    def push(self):
        pass


class ProductionPublic(ProductionPrivate):

    @cached_property
    def tags_public(self):
        return [f'{Constants.ORG_NAME}/{self.name}:latest', f'{Constants.ORG_NAME}/{self.name}:{self.tag}']

    @cached_property
    def tags_image(self):
        tags = super().tags_image
        tags += self.tags_public
        return tags

    def push(self):
        self.client.login(username=Constants.ORG_NAME, password=self.token)
        for tag in self.tags_public:
            with logger.span(f'Pushing image "{tag}"'):
                for tag, line_bytes in self.client.push(tag, stream_logs=True):
                    line = line_bytes.decode().rstrip()
                    logger.info(line.rstrip())

        self

class Compose(Inherit[Stack]):
    """

    Compose file representation

    """
    NAME = 'base'

    @property
    def port(self):
        return self.paths.metadata.port

    @property
    def data(self):
        data = dict(
            name=f"{self.name_dash}",
            services=dict(
                interpreter=dict(
                    image=f"{self.name}:{self.channel}-{self.extras_str}",
                    restart="unless-stopped",
                    container_name=f"{self.name}",
                    hostname=f"{self.name_dash}-{self.channel}",
                    env_file=[
                        "/opt/dev/repo/env",
                    ],
                    environment=dict(
                        # DISPLAY=f"{self.display}",
                    ),
                    volumes=[
                        "dev:/opt/dev/repo",
                        "ssh:/home/user/.ssh",
                        "/opt/dev/data:/opt/dev/data",
                        "/home/user/.Xauthority:/home/user/.Xauthority:ro",
                        "/tmp/.X11-unix:/tmp/.X11-unix",
                    ],
                    ports=[
                        f"{2200 + self.port}:22",
                        f"{8000 + self.port}:8080",
                        f"{8100 + self.port}:8180",
                        f"{8500 + self.port}:8501",  # legacy streamlit
                    ],
                    user="1000:1000",
                ),
            ),
            secrets=dict(
                hf_token=dict(
                    environment="HF_TOKEN",
                ),
            ),
            volumes=dict(
                dev=dict(
                    name=f"{self.name}",
                ),
                ssh=dict(
                    name="ssh",
                    external=True,
                ),
            ),
        )
        return data


class ComposeDocumentDatabase(Compose):
    """

    Compose file representation for document database service

    """
    NAME = 'db.document'

    @property
    def data(self):
        data = dict(
            # todo
        )
        return data
