"""
Collection-building helpers for asynchronous `corio.db.search`.
"""
from __future__ import annotations

from itertools import chain

from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from functools import cached_property
from qdrant_client.http import models
from qdrant_client.http.models import CollectionInfo
from typing import Any

from corio import logger
from corio.db.search.client import Client
from corio.db.search.constants import DENSE, DENSE_SIZE, MULTI, MULTI_SIZE, SIMPLE, SPARSE
from corio.db.search.document import Document, Point


# Async-only implementation.


class Builder:
    """Create and ingest the backing Qdrant collection."""

    Document: type[Document] = Document
    DENSE_SIZE = DENSE_SIZE
    MULTI_SIZE = MULTI_SIZE
    MAX_RETRIES = 3

    def __init__(
        self,
            document_type: type[Document],
            client: Client,
            data: Iterable[Any] | None = None,
    ):
        self.Document = document_type
        self.client = client
        self.data = data or ()

    @cached_property
    def name(self):
        return self.Document.__name__

    @cached_property
    def config(self):
        return dict(
            vectors_config={
                DENSE: models.VectorParams(
                    size=self.DENSE_SIZE,
                    distance=models.Distance.COSINE,
                    on_disk=True,
                    hnsw_config=models.HnswConfigDiff(m=16),
                ),
                MULTI: models.VectorParams(
                    size=self.MULTI_SIZE,
                    distance=models.Distance.COSINE,
                    on_disk=True,
                    multivector_config=models.MultiVectorConfig(
                        comparator=models.MultiVectorComparator.MAX_SIM,
                    ),
                    hnsw_config=models.HnswConfigDiff(m=0)
                ),
            },
            sparse_vectors_config={
                SPARSE: models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=True),
                    modifier=models.Modifier.IDF,
                ),
                SIMPLE: models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=True),
                    modifier=models.Modifier.IDF,
                ),
            },
            quantization_config=models.ScalarQuantization(
                scalar=models.ScalarQuantizationConfig(
                    type=models.ScalarType.INT8,
                ),
            ),
        )

    def get_point(self, data: Any) -> Point:
        """

        Convert a raw dataset row into a point instance.

        """
        raise NotImplementedError()

    async def collection(self) -> CollectionInfo:
        """

        Return the active collection, creating it on demand.

        """
        if not await self.client.collection_exists(collection_name=self.name):
            logger.warning(f'Collection "{self.name}" does not exist.')
            with logger.span(f'Creating collection "{self.name}"...'):
                await self.client.create_collection(
                    collection_name=self.name,
                    **self.config,
                )
            with logger.span('Creating payload indexes...'):
                for data in self.Document.indexes:
                    await self.client.create_payload_index(
                        collection_name=self.name,
                        **data,
                    )

        collection = await self.client.get_collection(collection_name=self.name)
        logger.info(f'Fetched collection: "{collection}"')
        return collection

    @asynccontextmanager
    async def disable_hnsw(self):
        """

        Temporarily lower HNSW indexing cost during ingest.

        """
        collection = await self.client.get_collection(collection_name=self.name)
        original = collection.config.params.vectors[DENSE].hnsw_config
        temp = models.HnswConfigDiff(m=0)
        logger.info(f"Enabling low-memory ingest mode: {temp}")
        await self.client.update_collection(
            collection_name=self.name,
            vectors_config={DENSE: models.VectorParamsDiff(hnsw_config=temp)},
        )
        try:
            yield
        finally:
            logger.info(f"Restoring post-ingest indexing settings: {original}")
            await self.client.update_collection(
                collection_name=self.name,
                vectors_config={DENSE: models.VectorParamsDiff(hnsw_config=original)},
            )

    @cached_property
    def embedder(self):
        """

        Return the embedder configured for the document type.

        """
        return self.Document.embedder

    async def points(self) -> AsyncIterator[Point]:
        """Yield points converted from the runtime input data."""
        for data in self.data:
            yield self.get_point(data)

    async def build(self):
        """

        Create the collection and upload all points.

        """
        batch_size = self.embedder.batch_size
        await self.collection()

        points = [point async for point in self.points()]
        points = chain.from_iterable(point.points for point in points)
        points = await self.embedder.add_vectors(points)

        async with self.disable_hnsw():
            await self.client.upload_points(
                collection_name=self.name,
                points=points,
                batch_size=batch_size,
                parallel=1,
                method="fork",
                max_retries=self.MAX_RETRIES,
            )
