"""
Collection-building helpers for `corio.db.search`.
"""
from __future__ import annotations

from contextlib import contextmanager
from functools import cached_property
from qdrant_client.http import models
from qdrant_client.http.models import CollectionInfo
from typing import Any

from corio import logger
from corio.db.search.client import Client
from corio.db.search.constants import DENSE
from corio.db.search.document import Document, Point
from corio.iterator import Iterator


class Builder:
    """Create and ingest the backing Qdrant collection."""

    Document: type[Document] = Document
    MAX_RETRIES = 3

    def __init__(self, document_type: type[Document] = Document, client: Client | None = None):
        self.Document = document_type
        self.client = client or Client()

    @cached_property
    def name(self):
        return self.Document.__name__

    def get_document(self, data: Any) -> Point:
        """

        Convert a raw dataset row into a point instance.

        """
        raise NotImplementedError()

    @property
    def collection(self) -> CollectionInfo:
        """

        Return the active collection, creating it on demand.

        """
        if not self.client.collection_exists(collection_name=self.name):
            logger.warning(f'Collection "{self.name}" does not exist.')
            with logger.span(f'Creating collection "{self.name}"...'):
                self.client.create_collection(
                    collection_name=self.name,
                    **self.embedder.config,
                )
            with logger.span('Creating payload indexes...'):
                for data in self.Document.indexes:
                    self.client.create_payload_index(collection_name=self.name, **data)

        collection = self.client.get_collection(collection_name=self.name)
        logger.info(f'Fetched collection: "{collection}"')
        return collection

    @contextmanager
    def disable_hnsw(self):
        """

        Temporarily lower HNSW indexing cost during ingest.

        """
        collection = self.client.get_collection(collection_name=self.name)
        original = collection.config.params.vectors[DENSE].hnsw_config
        temp = models.HnswConfigDiff(m=0)
        logger.info(f"Enabling low-memory ingest mode: {temp}")
        self.client.update_collection(
            collection_name=self.name,
            vectors_config={DENSE: models.VectorParamsDiff(hnsw_config=temp)},
        )
        try:
            yield
        finally:
            logger.info(f"Restoring post-ingest indexing settings: {original}")
            self.client.update_collection(
                collection_name=self.name,
                vectors_config={DENSE: models.VectorParamsDiff(hnsw_config=original)},
            )

    @cached_property
    def embedder(self):
        """

        Return the embedder configured for the document type.

        """
        return self.Document.embedder

    @property
    def docs(self) -> Iterator[Point]:
        """

        Yield points ready for upload.

        """
        raise NotImplementedError()

    def build(self):
        """

        Create the collection and upload all points.

        """
        batch_size = self.embedder.BATCH_SIZE_EMBEDDING
        self.collection
        with self.disable_hnsw():
            self.client.upload_points(
                collection_name=self.name,
                points=self.docs,
                batch_size=batch_size,
                parallel=1,
                method="fork",
                max_retries=self.MAX_RETRIES,
            )
