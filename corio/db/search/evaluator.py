"""

Evaluation helpers for `corio.db.search`.

"""

from __future__ import annotations

from functools import cached_property
from ranx import Qrels
from typing import ClassVar, Generic

from corio import iterator, logger
from corio.db.search.client import Client
from corio.db.search.document import Document, EmbedderT, EvaluatorT, PayloadT
from corio.db.search.querier import Querier
from corio.db.search.query import Query


class Evaluator(Generic[PayloadT, EmbedderT]):
    """

    Score query classes against the stored qrels.

    """


    METRICS: ClassVar[list[str]] = ["ndcg@10", "map@100", "recall@100", "precision@10"]

    def __init__(
            self,
            Document: type[Document[PayloadT, EmbedderT, EvaluatorT]] | None = None,
            client: Client | None = None,
    ):
        """

        Bind the evaluator to a document type and client.

        """

        self.client = client or Client()
        self.Document = Document

    @cached_property
    def name(self):
        """

        Return the evaluation name for the bound document type.

        """

        return self.Document.__name__

    @cached_property
    def queries(self) -> dict[str, str]:
        """

        Return the query id to text mapping used for evaluation.

        """

        raise NotImplementedError()

    @cached_property
    def qrels(self) -> Qrels:
        """

        Return the graded relevance set used for scoring.

        """

        raise NotImplementedError()

    def evaluate(
        self,
        query_classes: list[type[Query[PayloadT, EmbedderT]]] | None = None,
        *,
        limit: int = 100,
        metrics=None,
    ):
        """

        Run each query class and return metric scores by query description.

        """

        from ranx import Run, evaluate as run_evaluate

        metrics = metrics or self.METRICS
        query_classes = query_classes or [self.Document.Query]

        querier = Querier(doc_type=self.Document, client=self.client)
        collection_meta = querier.collection

        scores_by_query_desc: dict[str, dict[str, float]] = {}

        with logger.span("Evaluating query classes..."):
            for query_cls in query_classes:
                query_desc = query_cls.DESCRIPTION
                with logger.span(f"Doing eval... {query_desc}"):
                    queries = querier.query(
                        self.queries.values(),
                        limit=limit,
                        Query=query_cls,
                    )
                    run = Run(name=query_desc)
                    for query_id, query in zip(self.queries, queries):
                        for hit in query.hits:
                            run.add_score(query_id, hit.id, hit.score)

                    scores = run_evaluate(
                        self.qrels,
                        run,
                        metrics,
                        make_comparable=True,
                    )
                    scores = {metric: float(score) for metric, score in scores.items()}

                    eval_data = dict(
                        name=self.name,
                        is_metrics=True,
                        collection=collection_meta.model_dump(),
                        query_desc=query_desc,
                        query_class=query_cls.__name__,
                        scores=scores,
                    )
                    otel_data = iterator.flatten_tree(dict(eval=eval_data), sep="_")
                    logger.info(f"Eval scores: {scores}", **otel_data)

                    scores_by_query_desc[query_desc] = scores

        return scores_by_query_desc
