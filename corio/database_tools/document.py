import beanie
from beanie.odm import actions
from functools import cached_property
from pymongo import AsyncMongoClient
from typing import List

from corio import data_modelling_tools
from corio.constants import Constants
from corio.logging_tools import logger

ModifyEvents = [
    actions.Insert,
    actions.Replace,
    actions.Save,
    actions.SaveChanges,
    actions.Update
]


class Document(beanie.Document, data_modelling_tools.Base):
    """

    Document stub.

    """


class Client:

    def __init__(self, name, host=Constants.FMTR_DEV_HOST, port=27017, documents: List[beanie.Document] | None = None):
        self.name = name
        self.host = host
        self.port = port
        self.documents = documents

        self.client = AsyncMongoClient(self.uri, tz_aware=True)
        self.db = self.client[self.name]

    @cached_property
    def uri(self):
        return f'mongodb://{self.host}:{self.port}'

    async def connect(self):
        """

        Connect

        """
        with logger.span(f'Connecting to document database {self.uri=} {self.name=}'):
            return await beanie.init_beanie(database=self.db, document_models=self.documents)
