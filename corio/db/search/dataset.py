from __future__ import annotations

from contextlib import contextmanager
from functools import cached_property
from itertools import batched
from typing import Iterable, Any

from qdrant_client.http import models
from qdrant_client.http.models import CollectionInfo

from corio.inherit import Inherit
from corio.iterator import Iterator

from .collection import Collection
from .constants import DENSE
from .document import Document
from .embedder import Embedder
from .client import Client
from ... import logger


class Builder:
    Document = Document
    Embedder = Embedder
    MAX_LENGTH = 256
    MAX_RETRIES = 3

    def __init__(self, client: Client|None=None):
        self.client = client or Client()

    @cached_property
    def name(self):
        return self.Document.__name__

    def get_document(self, data: Any) -> Document:
        raise NotImplementedError()

    @property
    def collection(self)->CollectionInfo:
        if not self.client.collection_exists(collection_name=self.name):
            logger.warning(f'Collection "{self.name}" does not exist.')
            with logger.span(f'Creating collection "{self.name}"...'):
                self.client.create_collection(collection_name=self.name, **self.embedder.config)

            with logger.span(f'Creating payload indexes...'):
                for data in self.embedder.indexes:
                    self.client.create_payload_index(collection_name=self.name, **data)

        collection = self.client.get_collection(collection_name=self.name)
        logger.info(f'Fetched collection: "{collection}"')
        return collection

    @contextmanager
    def disable_hnsw(self):
        collection = self.client.get_collection(collection_name=self.name)
        original = collection.config.params.vectors[DENSE].hnsw_config

        temp = models.HnswConfigDiff(m=0)
        logger.info(f"Enabling low-memory ingest mode: {temp}")
        self.client.update_collection(
            collection_name=self.name,
            vectors_config={
                DENSE: models.VectorParamsDiff(
                    hnsw_config=temp,
                ),
            },
        )
        try:
            yield
        finally:
            logger.info(f"Restoring post-ingest indexing settings: {original}")
            self.client.update_collection(
                collection_name=self.name,
                vectors_config={
                    DENSE: models.VectorParamsDiff(
                        hnsw_config=original,
                    ),
                },
            )

    @cached_property
    def embedder(self):
        return self.Embedder()

    @property
    def docs(self) -> Iterator[Document]:
        raise NotImplementedError()

    def build(self):

        # batch_size=int(self.embedder.BATCH_SIZE_EMBEDDING*0.5)
        batch_size = self.embedder.BATCH_SIZE_EMBEDDING
        self.collection

        # for doc in self.docs:
        #     path=Path(paths.data/'json'/f'{doc.id}.json')
        #     path.write_data(doc.model_dump(warnings=False))

        with self.disable_hnsw():
            self.client.upload_points(
                collection_name=self.name,
                points=self.docs,
                batch_size=batch_size,
                parallel=1,
                method="fork",
                max_retries=self.MAX_RETRIES,
                # wait=True,
            )

        return ...
