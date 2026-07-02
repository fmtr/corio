from __future__ import annotations

from collections.abc import Iterable
from functools import cached_property
from itertools import batched
from typing import Generic

from qdrant_client.http.models import CollectionInfo

from corio import iterator, logger
from corio.iterator import Iterator

from .client import Client
from .document import Document, EmbedderT, PayloadT
from .query import Query


class Querier(Generic[PayloadT, EmbedderT]):
    Document: type[Document[PayloadT, EmbedderT]] = Document

    def __init__(
        self,
        doc_type: type[Document[PayloadT, EmbedderT]] | None = None,
        client: Client | None = None,
    ):
        self.Document = doc_type or self.Document
        self.client = client or Client()

    @cached_property
    def name(self):
        return self.Document.__name__

    @property
    def collection(self) -> CollectionInfo:
        collection = self.client.get_collection(collection_name=self.name)
        logger.info(f'Fetched collection: "{collection}"')
        return collection

    @cached_property
    def embedder(self) -> EmbedderT:
        return self.Document.get_embedder()

    def query(
        self,
        texts: Iterable[str],
        *,
        limit: int = 10,
        query_cls: type[Query[PayloadT, EmbedderT]] | None = None,
    ):
        query_cls = query_cls or self.Document.Query
        batch_size = self.embedder.BATCH_SIZE_EMBEDDING
        self.collection

        queries = (query_cls(text=text, limit=limit) for text in texts)
        queries = Iterator(queries)

        points_by_query = []
        for query_batch in batched(queries, batch_size):
            self.embedder.embed(query_batch)

            requests = [query.request for query in query_batch]
            with Iterator.span():
                results = self.client.query_batch_points(
                    collection_name=self.name,
                    requests=requests,
                )
            points_by_query.extend(result.points for result in results)

        return points_by_query


    def evaluate(self, dataset_cls, query_classes, *, limit: int = 100, metrics=None):
        from ranx import Run, evaluate as run_evaluate

        dataset = dataset_cls(self)
        metrics = metrics or dataset.EVAL_METRICS
        qrel_sets = dataset.qrel_sets
        eval_queries = list(dataset.eval_queries)
        collection_meta = self.client.get_collection(collection_name=self.name)

        scores_by_query_desc: dict[str, dict[str, dict[str, float]]] = {}

        with logger.span("Evaluating query classes..."):
            for query_cls in query_classes:
                query_desc = query_cls.DESCRIPTION
                with logger.span(f"Doing eval... {query_desc}"):
                    hits_by_query = self.query(
                        [item.text for item in eval_queries],
                        limit=limit,
                        query_cls=query_cls,
                    )
                    run_dict = {
                        item.query_id: {
                            hit.payload["id"]: float(hit.score)
                            for hit in hits
                        }
                        for item, hits in zip(eval_queries, hits_by_query)
                    }
                    run = Run(run_dict)

                    scores_by_qrel_desc: dict[str, dict[str, float]] = {}
                    for qrel_desc, qrels in qrel_sets.items():
                        scores = run_evaluate(
                            qrels,
                            run,
                            metrics,
                            make_comparable=True,
                        )

                        eval_data = dict(
                            name=self.name,
                            is_metrics=True,
                            collection=collection_meta.model_dump(),
                            query_desc=query_desc,
                            query_class=query_cls.__name__,
                            qrels_desc=qrel_desc,
                            scores=scores,
                        )
                        otel_data = iterator.flatten_tree(dict(eval=eval_data), sep="_")
                        logger.info(f"Eval scores: {scores}", **otel_data)

                        scores_by_qrel_desc[qrel_desc] = scores

                    scores_by_query_desc[query_desc] = scores_by_qrel_desc

        return scores_by_query_desc
