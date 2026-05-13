from __future__ import annotations

import logging
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from functools import cached_property
from typing import Callable, List, Optional, Union, Self, TYPE_CHECKING

import httpx
import uvicorn
from fastapi import FastAPI, Request

from corio import env, strings
from corio.iterator import enlist
from corio.logs import logger

if TYPE_CHECKING:
    from corio.api.mcp import FastMCP

for name in ["uvicorn.access", "uvicorn.error", "uvicorn"]:
    logger_uvicorn = logging.getLogger(name)
    logger_uvicorn.handlers.clear()
    logger_uvicorn.propagate = False

@dataclass
class Endpoint:
    """

    Endpoint-as-method config

    """
    method: Callable
    path: str | None = None
    tags: Optional[Union[str, List[str]]] = None
    method_http: Optional[Callable] = None

    def __post_init__(self):
        self.tags = enlist(self.tags)


class Base:
    """

    Simple API base class, generalising endpoint-as-method config.

    """
    TITLE = 'Base API'
    HOST = '0.0.0.0'
    PORT = 8000
    SWAGGER_PARAMS = dict(tryItOutEnabled=True)
    URL = None
    URL_DOCS = '/'
    URL_PREFIX = None
    IS_MCP = False
    MCP_PATH = '/mcp'


    def add_endpoint(self, endpoint: Endpoint):
        """

        Add endpoints from definitions using a single dataclass instance.

        """
        method_http = endpoint.method_http or self.app.post
        doc = (endpoint.method.__doc__ or '').strip() or None
        path = endpoint.path or f'/{endpoint.method.__name__}'

        method_http(
            path=path,
            tags=endpoint.tags,
            summary=doc,
            operation_id=endpoint.method.__name__,
        )(endpoint.method)

    def __init__(self):
        self.app = FastAPI(
            title=self.TITLE,
            swagger_ui_parameters=self.SWAGGER_PARAMS,
            docs_url=self.URL_DOCS,
            lifespan=self.lifespan,
            description=self.description,
        )
        logger.instrument_fastapi(self.app)

        for endpoint in self.get_endpoints():
            self.add_endpoint(endpoint)

        if env.IS_DEV:
            self.app.exception_handler(Exception)(self.handle_exception)

        for child in self.children:
            self.app.mount(child.url_prefix, child.app)

        if self.IS_MCP:
            self.app.mount(self.MCP_PATH, self.mcp_app)
            self.app.router.lifespan_context = self.lifespan_mcp

    @cached_property
    def children(self) -> List[Self]:
        """

        Initialise any sub-APIs

        """
        return []

    @cached_property
    def url_prefix(self) -> str:
        """

        Get a default sub-API prefix.

        """
        if self.URL_PREFIX:
            return self.URL_PREFIX

        return f'/{self.__class__.__name__.lower()}'

    def get_endpoints(self) -> List[Endpoint]:
        """

        Define endpoints using a dataclass instance.

        """
        endpoints = [

        ]

        return endpoints

    async def handle_exception(self, request: Request, exception: Exception):
        """

        Actually raise exceptions (e.g. for debugging) instead of returning a 500.

        """
        exception
        raise

    @property
    def url(self) -> str:
        """

        Default URL unless overridden.

        """
        if self.URL:
            url = self.URL
        else:
            url = f'http://{self.HOST}:{self.PORT}'
        return url

    @property
    def message(self) -> str:
        """

        Launch message.

        """
        message = f"Launching {self.TITLE} at {self.url}"
        if self.IS_MCP:
            message = f"{message} (with MCP at {self.MCP_PATH})"
        return message

    @property
    def description(self) -> str|None:
        """

        Optional OpenAPI description with immediate child API links.

        """
        if not self.children:
            return None

        lines = [f"- [{child.TITLE}]({child.url_prefix})" for child in self.children]
        lines= "\n".join(lines)
        description=strings.trim(f"""
        ### APIs
        
        {lines}
        """)
        return description

    @property
    def config(self) -> uvicorn.Config:
        """

        Uvicorn config.

        """
        return uvicorn.Config(self.app, host=self.HOST, port=self.PORT, access_log=False)

    @property
    def server(self) -> uvicorn.Server:
        """"

        Uvicorn server.

        """
        return uvicorn.Server(self.config)

    @classmethod
    async def launch_async(cls, *args, **kwargs):
        """

        Initialise and launch.

        """

        self = cls(*args, **kwargs)
        logger.info(self.message)
        await self.server.serve()

    @classmethod
    def launch(cls, *args, **kwargs):
        """

        Convenience method to launch async from a regular context.

        """
        import asyncio
        return asyncio.run(cls.launch_async(*args, **kwargs))

    @staticmethod
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """

        Default app lifespan.

        """
        yield
        logger.info(f"Closing {app.title}")


    # MCP integration methods

    @cached_property
    def mcp(self) -> FastMCP:
        """

        Build an MCP server from this API's OpenAPI schema.

        """
        from corio.api.mcp import FastMCP
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url=self.url)
        return FastMCP.from_openapi(openapi_spec=self.app.openapi(), client=client, name=self.TITLE)

    @cached_property
    def mcp_app(self):
        """

        HTTP ASGI app for this API's MCP server.

        """
        return self.mcp.http_app(path='/')


    @cached_property
    def mcp_lifespans_flat(self) -> list[tuple[Callable, FastAPI]]:
        """

        Flattened MCP lifespans for this API and immediate descendants.

        """

        if self.IS_MCP:
            lifespans = [(self.mcp_app.lifespan, self.mcp_app)]
        else:
            lifespans = []

        for child in self.children:
            lifespans.extend(child.mcp_lifespans_flat)
        return lifespans

    @cached_property
    def lifespan_mcp(self):
        """

        Combined lifespan wrapper for FastAPI and mounted MCP apps.

        """
        original_lifespan = self.app.router.lifespan_context

        @asynccontextmanager
        async def lifespan(app):
            async with AsyncExitStack() as stack:
                await stack.enter_async_context(original_lifespan(app))
                for mcp_lifespan, mcp_owner_app in self.mcp_lifespans_flat:
                    await stack.enter_async_context(mcp_lifespan(mcp_owner_app))
                yield

        return lifespan
