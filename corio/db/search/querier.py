from __future__ import annotations

from collections.abc import Iterable
from itertools import batched

from corio import iterator
from corio.logs import logger


class Querier:
    COLLECTION_NAME = "search"
    BATCH_SIZE_EMBEDDING = 50

    MAX_LENGTH = 1024
    DENSE_SIZE = 1024
    MULTI_SIZE = 1024



    def query(self, texts: Iterable[str], *, limit: int = 10, query_cls=None):
        from .query import Query

        query_cls = query_cls or Query

        queries = [query_cls(self, text=text, limit=limit) for text in texts]
        queries = self.embedder.embed(queries)
        requests = [query.request for query in queries]

        points_by_query = []
        for request_batch in batched(requests, self.BATCH_SIZE_EMBEDDING):
            results = self.client.query_batch_points(
                collection_name=self.COLLECTION_NAME,
                requests=list(request_batch),
            )
            points_by_query.extend(result.points for result in results)

        return points_by_query


    def evaluate(self, dataset_cls, query_classes, *, limit: int = 100, metrics=None):
        from ranx import Run, evaluate as run_evaluate

        self.collection
        dataset = dataset_cls(self)
        metrics = metrics or dataset.EVAL_METRICS
        qrel_sets = dataset.qrel_sets
        eval_queries = list(dataset.eval_queries)
        collection_meta = self.client.get_collection(collection_name=self.COLLECTION_NAME)

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
                            name=self.COLLECTION_NAME,
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
