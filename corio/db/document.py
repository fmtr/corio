from functools import cached_property
from typing import List

import beanie
import certifi
from beanie.odm import actions
from pymongo import AsyncMongoClient

from corio import dm
from corio.logs import logger

ModifyEvents = [
    actions.Insert,
    actions.Replace,
    actions.Save,
    actions.SaveChanges,
    actions.Update
]

PORT=27017
HOST='document.db.gex.fmtr.dev'

class Document(beanie.Document, dm.Base):
    """

    Document stub.

    """


class Client:

    def __init__(
            self,
            name,
            host=HOST,
            port=PORT,
            documents: List[beanie.Document] | None = None,
            is_tls: bool = True,
    ):
        self.name = name
        self.host = host
        self.port = port
        self.documents = documents
        self.is_tls = is_tls

        self.client = AsyncMongoClient(self.uri, **self.client_options)
        self.db = self.client[self.name]

    @cached_property
    def client_options(self):
        return dict(
            tz_aware=True,
            tls=self.is_tls,
            tlsCAFile=certifi.where(),
        )

    @cached_property
    def uri(self):
        return f'mongodb://{self.host}:{self.port}'

    async def connect(self):
        """

        Connect

        """
        with logger.span(f'Connecting to document database {self.uri=} {self.name=}'):
            return await beanie.init_beanie(database=self.db, document_models=self.documents)
