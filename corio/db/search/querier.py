"""

Query execution helpers for `corio.db.search`.

"""

from __future__ import annotations

from collections.abc import Iterable
from functools import cached_property
from itertools import batched
from qdrant_client.http.models import CollectionInfo
from typing import Any, Generic

from corio import logger
from corio.iterator import Iterator
from .client import Client
from .document import Document, EmbedderT, PayloadT
from .query import Query


class Querier(Generic[PayloadT, EmbedderT]):
    """

    Run batched search requests against a collection.

    """

    Document: type[Document[PayloadT, EmbedderT, Any]] = Document

    def __init__(
        self,
        doc_type: type[Document[PayloadT, EmbedderT, Any]] | None = None,
        client: Client | None = None,
    ):
        """

        Bind the querier to a document type and client.

        """

        self.Document = doc_type or self.Document
        self.client = client or Client()

    @cached_property
    def name(self):
        """

        Return the collection name for the configured document type.

        """

        return self.Document.__name__

    @property
    def collection(self) -> CollectionInfo:
        """

        Return the collection for the configured document type.

        """

        collection = self.client.get_collection(collection_name=self.name)
        logger.info(f'Fetched collection: "{collection}"')
        return collection

    @cached_property
    def embedder(self) -> EmbedderT:
        """

        Return the embedder used to encode incoming queries.

        """

        return self.Document.get_embedder()

    def query(
        self,
        texts: Iterable[str],
        *,
        limit: int = 10,
        Query: type[Query[PayloadT, EmbedderT]] | None = None,
    ):
        """

        Yield queries annotated with their search hits.

        """

        Query = Query or self.Document.Query
        batch_size = self.embedder.BATCH_SIZE_EMBEDDING

        queries = (Query(text=text, limit=limit, is_multi=self.Document.IS_MULTI) for text in texts)
        queries = Iterator(queries)

        for query_batch in batched(queries, batch_size):
            self.embedder.embed(query_batch)

            requests = [query.request for query in query_batch]
            with Iterator.span():
                results = self.client.query_batch_points(
                    collection_name=self.name,
                    requests=requests,
                )

            for query,result in zip(query_batch,results):
                hits=[self.Document.Payload(score=hit.score, **hit.payload) for hit in result.points]
                query.hits=hits
                yield query
