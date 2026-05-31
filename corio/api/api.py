from __future__ import annotations

import logging
from contextlib import AsyncExitStack, asynccontextmanager
from functools import cached_property
from typing import Callable, List, Self, TYPE_CHECKING

import httpx
import uvicorn
from fastapi import FastAPI, Request

from corio import env, strings
from corio import api
from corio.iterator import IndexList
from corio.logs import logger

if TYPE_CHECKING:
    from fastmcp import FastMCP
    from fastmcp.server.transforms import Transform

for name in ["uvicorn.access", "uvicorn.error", "uvicorn"]:
    logger_uvicorn = logging.getLogger(name)
    logger_uvicorn.handlers.clear()
    logger_uvicorn.propagate = False


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
    MCP_PATH = '/mcp'

    @cached_property
    def ENDPOINTS(self) -> list[type[api.endpoint.Base]]:
        """

        Endpoint classes registered on this API.

        """
        return []

    @cached_property
    def TRANSFORMS(self) -> list[type[Transform]]:
        """

        MCP transform classes applied when MCP endpoints are present.

        """
        return []

    def __init__(self):
        """

        Build the FastAPI app and register child APIs, endpoints, and MCP mounts.

        """
        self.app = FastAPI(
            title=self.TITLE,
            swagger_ui_parameters=self.SWAGGER_PARAMS,
            docs_url=self.URL_DOCS,
            lifespan=self.lifespan,
            description=self.description,
        )
        logger.instrument_fastapi(self.app)

        self.endpoints = IndexList[api.endpoint.Base]()
        for cls in self.ENDPOINTS:
            endpoint = cls(self)
            endpoint.register()
            self.endpoints.append(endpoint)

        if env.IS_DEV:
            self.app.exception_handler(Exception)(self.handle_exception)

        for child in self.children:
            self.app.mount(child.url_prefix, child.app)

        if self.is_mcp:
            for cls in self.TRANSFORMS:
                transform = cls(self.mcp)
                self.mcp.add_transform(transform)
            self.app.mount(self.MCP_PATH, self.mcp_http)
            self.app.router.lifespan_context = self.lifespan_mcp

    @cached_property
    def is_mcp(self):
        """

        Whether this API exposes any MCP endpoints.

        """
        return any(endpoint.IS_MCP for endpoint in self.endpoints)

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
        if self.is_mcp:
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
        """

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
        from fastmcp import FastMCP
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url=self.url)
        return FastMCP.from_openapi(openapi_spec=self.app.openapi(), client=client, name=self.TITLE)

    @cached_property
    def mcp_http(self):
        """

        ASGI app exposing the MCP server over HTTP.

        """
        return self.mcp.http_app(path='/')

    @cached_property
    def mcp_lifespans_flat(self) -> list[tuple[Callable, FastAPI]]:
        """

        Flattened MCP lifespans for this API and immediate descendants.

        """

        if self.is_mcp:
            lifespans = [(self.mcp_http.lifespan, self.mcp_http)]
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
            """

            Enter the FastAPI lifespan and all mounted MCP lifespans.

            """
            async with AsyncExitStack() as stack:
                await stack.enter_async_context(original_lifespan(app))
                for mcp_lifespan, mcp_owner_app in self.mcp_lifespans_flat:
                    await stack.enter_async_context(mcp_lifespan(mcp_owner_app))
                yield

        return lifespan
