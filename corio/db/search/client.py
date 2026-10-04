"""

Qdrant client wrapper used by `corio.db.search`.

"""

import qdrant_client as qc
from qdrant_client.http import models
from typing import ClassVar

from corio.constants import Constants
from corio.logs import logger


class Client(qc.QdrantClient):
    """

    Qdrant client with Corio defaults and startup logging.

    """

    MEMORY: ClassVar[str]=":memory:"

    models=models

    def __init__(
        self,
        url: str | None = Constants.FMTR_DB_SEARCH_URL_DEFAULT,
        port: int = 443,
        timeout: int = 180,
        location: str | None = None,
        **kwargs,
    ):
        """

        Connect to the configured search backend and log the collections.

        """

        if location:
            url = None
        self.port = port
        self.url = url
        self.timeout = timeout
        self.location = location
        super().__init__(
            port=self.port,
            url=self.url,
            timeout=self.timeout,
            location=self.location,
            **kwargs,
        )

        with logger.span(f'Connecting to search database {self.location=} {self.url=} {self.port=}'):
            logger.info(f'Found collections: {self.get_collections().collections}')
