import corio
from functools import cached_property

import qdrant_client as qc


from corio.constants import Constants
from corio.logs import logger

models=qc.models

class Client:

    def __init__(self, name, path: corio.Path, host: str | None = None, port: int = 6333):
        self.name = name
        self.path = corio.Path(path)
        self.host = host
        self.port = port
        self.client = self._get_client()

    @cached_property
    def is_local(self):
        return self.host is None

    def _get_client(self):
        if self.is_local:
            return qc.QdrantClient(path=str(self.path))
        return qc.QdrantClient(host=self.host or Constants.FMTR_DEV_HOST, port=self.port)

    def connect(self):
        """

        Connect

        """
        with logger.span(f'Connecting to search database {self.name=} {self.path=} {self.host=} {self.port=}'):
            if not self.is_local:
                self.client.get_collections()
            return self.client
