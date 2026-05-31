from __future__ import annotations

from typing import Callable, List, Optional, TYPE_CHECKING, Union

from corio.iterator import enlist
from corio.strings import camel_to_snake, get_docstring

if TYPE_CHECKING:
    from corio.api.api import Base as ApiBase


class Base:
    """

    Base endpoint contract.

    """

    NAME: str | None = None
    IS_MCP: bool = False

    def __init__(self, api: ApiBase):
        """

        Bind this endpoint instance to its owning API.

        """
        self.api = api

    async def run(self, *args, **kwargs):
        """

        Execute the endpoint.

        """
        raise NotImplementedError

    def register(self):
        """

        Register this endpoint with its backing API framework.

        """
        raise NotImplementedError

    @property
    def name(self) -> str:
        """

        Public endpoint name, defaulting to the class name in snake case.

        """
        return self.NAME or camel_to_snake(self.__class__.__name__)

    @property
    def cls(self):
        """

        Endpoint class lookup for this API's registered endpoints.

        """
        return self.api.endpoints.cls


class API(Base):
    """

    Class-based HTTP endpoint object.

    """

    PATH: str | None = None
    TAGS: Optional[Union[str, List[str]]] = None
    OPERATION_ID: str | None = None

    @property
    def path(self) -> str:
        """

        HTTP route path for this endpoint.

        """
        return self.PATH or f"/{self.name}"

    @property
    def tags(self) -> list[str]:
        """

        OpenAPI tags for this endpoint.

        """
        return enlist(self.TAGS)

    @property
    def method(self) -> Callable:
        """

        FastAPI decorator used to register this HTTP endpoint.

        """
        return self.api.app.get

    @property
    def summary(self) -> str | None:
        """

        OpenAPI summary from the endpoint class docstring.

        """
        return get_docstring(self.__class__)

    @property
    def operation_id(self) -> str:
        """

        Stable OpenAPI operation ID for this endpoint.

        """
        return self.OPERATION_ID or self.name

    def register(self):
        """

        Register this endpoint as an HTTP route.

        """
        self.method(
            path=self.path,
            tags=self.tags,
            summary=self.summary,
            operation_id=self.operation_id,
        )(self.run)


class MCP(Base):
    """

    Class-based MCP endpoint object.

    """

    APP: bool = False
    IS_MCP: bool = True
    DESCRIPTION: str | None = None

    @property
    def description(self) -> str | None:
        """

        MCP description from an override or the endpoint class docstring.

        """
        if self.DESCRIPTION is not None:
            return self.DESCRIPTION
        return get_docstring(self.__class__)

    @property
    def method(self) -> Callable:
        """

        MCP decorator used to register this endpoint.

        """
        raise NotImplementedError

    def register(self):
        """

        Register this endpoint with MCP.

        """
        self.method(self.run)


class Tool(MCP):
    """

    MCP tool endpoint.

    """

    @property
    def method(self) -> Callable:
        """

        MCP tool decorator for this endpoint.

        """
        return self.api.mcp.tool(
            name=self.name,
            description=self.description,
            app=self.APP,
        )


class UI(Tool):
    """

    MCP app UI tool endpoint.

    """

    APP: bool = True


class Prompt(MCP):
    """

    MCP prompt endpoint.

    """

    @property
    def method(self) -> Callable:
        """

        MCP prompt decorator for this endpoint.

        """
        return self.api.mcp.prompt(name=self.name)


class Resource(MCP):
    """

    MCP resource endpoint.

    """

    URI: str

    @property
    def method(self) -> Callable:
        """

        MCP resource decorator for this endpoint.

        """
        return self.api.mcp.resource(uri=self.URI)

    def register(self):
        """

        Register this endpoint as an MCP resource.

        """
        self.method(self.run)
