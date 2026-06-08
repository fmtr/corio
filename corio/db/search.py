import corio
from functools import cached_property

import qdrant_client as qc

from corio import Path
from corio.constants import Constants
from corio.logs import logger

models=qc.models

class Client:

    def __init__(self, name, path: Path|None=None, host: str | None = None,url: str | None = None, port: int = 6333):
        self.name = name
        self.path = path
        self.host = host
        self.port = port
        self.url=url
        self.client = self._get_client()

    @cached_property
    def is_local(self):
        return self.host is None

    def _get_client(self):
        return qc.QdrantClient(path=self.path, host=self.host, port=self.port, url=self.url)

    def connect(self):
        """

        Connect

        """
        with logger.span(f'Connecting to search database {self.name=} {self.path=} {self.host=} {self.port=}'):
            if not self.is_local:
                self.client.get_collections()
            return self.client
