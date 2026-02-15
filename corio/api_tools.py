import logging
import uvicorn
from dataclasses import dataclass
from fastapi import FastAPI, Request
from typing import Callable, List, Optional, Union

from corio import environment_tools
from corio.iterator_tools import enlist
from corio.logging_tools import logger

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
    path: str
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
    PORT = 8080
    SWAGGER_PARAMS = dict(tryItOutEnabled=True)
    URL = None
    URL_DOCS = '/docs'

    def add_endpoint(self, endpoint: Endpoint):
        """

        Add endpoints from definitions using a single dataclass instance.

        """
        method_http = endpoint.method_http or self.app.post
        doc = (endpoint.method.__doc__ or '').strip() or None

        method_http(
            endpoint.path,
            tags=endpoint.tags,
            description=doc,
            summary=doc
        )(endpoint.method)

    def __init__(self):
        self.app = FastAPI(title=self.TITLE, swagger_ui_parameters=self.SWAGGER_PARAMS, docs_url=self.URL_DOCS)
        logger.instrument_fastapi(self.app)

        for endpoint in self.get_endpoints():
            self.add_endpoint(endpoint)

        if environment_tools.IS_DEV:
            self.app.exception_handler(Exception)(self.handle_exception)

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
        return f"Launching {self.TITLE} at {self.url}"

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



if __name__ == '__main__':
    Base.launch()
