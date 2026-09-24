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
from corio.db.search.document import Payload
from corio.db.search.query import Query
from corio.iterator import Iterator


class Querier:
    """

    Run batched search requests against a collection.

    """

    def __init__(
        self,
            payload_type: type[Payload] = Payload,
        client: Client | None = None,
    ):
        self.Payload = payload_type
        self.Document = payload_type.Document
        self.client = client or Client()

    @cached_property
    def name(self):
        return self.Payload.__name__

    @property
    def collection(self) -> CollectionInfo:
        collection = self.client.get_collection(collection_name=self.name)
        logger.info(f'Fetched collection: "{collection}"')
        return collection

    @cached_property
    def embedder(self):
        return self.Payload.get_embedder()

    def query(
        self,
        texts: Iterable[str],
        *,
        limit: int = 10,
            Query: type[Query] | None = None,
    ):
        """

        Yield queries annotated with their search hits.

        """
        query_type = Query or self.Payload.Query
        batch_size = self.embedder.BATCH_SIZE_EMBEDDING

        queries = (
            query_type(
                text=text,
                limit=limit,
                is_multi=self.Payload.IS_MULTI,
            )
            for text in texts
        )
        queries = Iterator(queries)

        for query_batch in batched(queries, batch_size):
            self.embedder.embed(query_batch)

            requests = [query.request for query in query_batch]
            with Iterator.span():
                results = self.client.query_batch_points(
                    collection_name=self.name,
                    requests=requests,
                )

            for query, result in zip(query_batch, results):
                hits = [
                    self.Payload(score=hit.score, **hit.payload)
                    for hit in result.points
                ]
                query.hits = hits
                yield query
