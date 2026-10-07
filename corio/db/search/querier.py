"""

Query execution helpers for `corio.db.search`.

"""
from __future__ import annotations

from itertools import batched

from collections.abc import AsyncIterator, Iterable
from functools import cached_property
from qdrant_client.http import models
from qdrant_client.http.models import CollectionInfo

from corio import logger
from corio.db.search.client import Client
from corio.db.search.document import Document
from corio.db.search.query import Query


class Querier:
    """Run batched asynchronous search requests against a collection."""

    def __init__(
            self,
            document_type: type[Document],
            client: Client,
    ):
        self.Document = document_type
        self.client = client

    @cached_property
    def name(self):
        return self.Document.__name__

    async def collection(self) -> CollectionInfo:
        """Return the active collection."""
        collection = await self.client.get_collection(collection_name=self.name)
        logger.info(f'Fetched collection: "{self.name}"')
        return collection

    @cached_property
    def embedder(self):
        """Return the embedder configured for the document type."""
        return self.Document.embedder

    async def query(
        self,
        texts: Iterable[str],
        *,
        limit: int = 10,
        query_type: type[Query] | None = None,
        runtime_filter: models.Filter | None = None,
    ) -> AsyncIterator[Query]:
        """Yield queries annotated with their search hits."""
        query_type = query_type or self.Document.Query
        batch_size = self.embedder.batch_size
        queries = [
            query_type(
                text=text,
                limit=limit,
                is_multi=self.Document.IS_MULTI,
                runtime_filter=runtime_filter,
            )
            for text in texts
        ]

        for query_batch in batched(queries, batch_size):
            await self.embedder.add_vectors(query_batch)
            requests = [query.request for query in query_batch]
            results = await self.client.query_batch_points(
                collection_name=self.name,
                requests=requests,
            )
            for query, result in zip(query_batch, results):
                query.hits = [
                    self.Document(score=hit.score, **hit.payload)
                    for hit in result.points
                ]
                yield query
