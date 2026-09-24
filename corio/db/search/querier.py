"""

Query execution helpers for `corio.db.search`.

"""
from __future__ import annotations

from itertools import batched

from collections.abc import Iterable
from functools import cached_property
from qdrant_client.http.models import CollectionInfo

from corio import logger
from corio.db.search.client import Client
from corio.db.search.document import Document
from corio.db.search.query import Query
from corio.iterator import Iterator


class Querier:
    """

    Run batched search requests against a collection.

    """

    def __init__(
            self,
            document_type: type[Document] = Document,
            client: Client | None = None,
    ):
        self.Document = document_type
        self.client = client or Client()

    @cached_property
    def name(self):
        return self.Document.__name__

    @property
    def collection(self) -> CollectionInfo:
        """

        Return the active collection.

        """
        collection = self.client.get_collection(collection_name=self.name)
        logger.info(f'Fetched collection: "{self.name}"')
        return collection

    @cached_property
    def embedder(self):
        """

        Return the embedder configured for the document type.

        """
        return self.Document.embedder

    def query(
        self,
        texts: Iterable[str],
        *,
        limit: int = 10,
            query_type: type[Query] | None = None,
    ):
        """

        Yield queries annotated with their search hits.

        """
        query_type = query_type or self.Document.Query
        batch_size = self.embedder.BATCH_SIZE_EMBEDDING
        queries = Iterator(
            query_type(text=text, limit=limit, is_multi=self.Document.IS_MULTI)
            for text in texts
        )

        for query_batch in batched(queries, batch_size):
            self.embedder.embed(query_batch)
            requests = [query.request for query in query_batch]
            with Iterator.span():
                results = self.client.query_batch_points(
                    collection_name=self.name,
                    requests=requests,
                )
            for query, result in zip(query_batch, results):
                query.hits = [
                    self.Document(score=hit.score, **hit.payload)
                    for hit in result.points
                ]
                yield query
