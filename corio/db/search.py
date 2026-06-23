import qdrant_client as qc
from corio.constants import Constants
from corio.logs import logger

from qdrant_client.http import models

class Client(qc.QdrantClient):
    """

    Stub Qdrant Client

    """

    models=models

    def __init__(
        self,
        url: str | None = Constants.FMTR_DB_SEARCH_URL_DEFAULT,
        port: int = 443,
        timeout: int = 180,
        **kwargs,
    ):

        self.port = port
        self.url = url
        self.timeout = timeout
        super().__init__(
            port=self.port,
            url=self.url,
            timeout=self.timeout,
            **kwargs,
        )

        with logger.span(f'Connecting to search database {self.url=} {self.port=}'):
            logger.info(f'Found collections: {self.get_collections().collections}')


