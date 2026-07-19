"""

Example db.search implementation

"""

from __future__ import annotations






from corio.db.search.document import Payload, Document

from functools import lru_cache
from itertools import chain, islice
from typing import ClassVar

import ir_datasets
from ranx import Qrels
from ir_datasets.datasets.msmarco_document import MsMarcoDocument

from corio.db.search.builder import Builder
from corio.db.search.evaluator import Evaluator
from corio.db.search.query import Query, QueryBasic

from corio.hash import get_hash_int
from corio.iterator import Iterator
from corio.logs import logger
from corio.db.search.client import models
from corio.db.search.embedder import Embedder

from functools import cached_property


class PayloadMsMarco(Payload):
    title: str
    url: str

    @cached_property
    def text_vector(self) -> str:

        if self.is_doc:
            text = f'{self.title} {self.text}'
        else:
            text = self.text
        return text


class DocumentMsMarco(Document[PayloadMsMarco, Embedder, Evaluator]):
    Payload: ClassVar[type[PayloadMsMarco]] = PayloadMsMarco
    IS_MULTI = False

    @classmethod
    @lru_cache
    def get_builder(self) -> type[BuilderMsMarco]:
        return BuilderMsMarco


class DatasetMsMarco:
    DATASET_NAME = "msmarco-document/trec-dl-2019"

    @cached_property
    def ir_dataset(self):
        return ir_datasets.load(self.DATASET_NAME)

class BuilderMsMarco(Builder[PayloadMsMarco, Embedder], DatasetMsMarco):
    Document = DocumentMsMarco


    TOTAL_DOCS = 50_000

    def get_document(self, data: MsMarcoDocument) -> DocumentMsMarco:

        doc = self.Document(
            id=get_hash_int(data.doc_id),
            vector=[]
        )

        payload = self.Document.Payload(
            id=data.doc_id,
            title=data.title,
            url=data.url,
            text=data.body
        )
        doc.payload_obj = payload
        return doc



    @property
    def inserted_ids(self) -> set[str]:
        collection = self.collection
        ids: set[str] = set()
        offset = None
        while True:
            points, offset = self.client.scroll(
                collection_name=self.name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="is_doc",
                            match=models.MatchValue(value=True),
                        )
                    ]
                ),
                with_payload=["id"],
                with_vectors=False,
                limit=10_000,
                offset=offset,
            )
            for point in points:
                ids.add(point.payload["id"])
            if offset is None:
                break
        logger.info(f"Found {len(ids)} already inserted docs")
        return ids

    @property
    def docs(self) -> Iterator[DocumentMsMarco]:
        dataset = self.ir_dataset
        inserted_ids = self.inserted_ids
        remaining_total = self.TOTAL_DOCS - len(inserted_ids)

        gold_doc_ids = {qrel.doc_id for qrel in dataset.qrels_iter()} - inserted_ids
        gold_doc_ids_count = len(gold_doc_ids)
        gold_doc_ids_session = set(islice(gold_doc_ids, remaining_total))
        remaining_non_gold = remaining_total - len(gold_doc_ids_session)
        logger.info(
            f"Doc targets - {self.TOTAL_DOCS=}, {remaining_total=}, {gold_doc_ids_count=}, {remaining_non_gold=}"
        )

        ids_gold = (dataset.docs.lookup(id) for id in gold_doc_ids_session)
        ids_other = (
            doc
            for doc in islice(
            (
                doc
                for doc in dataset.docs_iter()
                if doc.doc_id not in inserted_ids and doc.doc_id not in gold_doc_ids_session
            ),
            remaining_non_gold,
        )
        )
        data = chain(ids_other, ids_gold)
        docs = (self.get_document(datum) for datum in data)
        docs = Iterator(docs, total=remaining_total)
        docs = chain.from_iterable(doc.points for doc in docs)
        docs = self.embedder.add_vectors(docs)

        return docs




class EvaluatorMsMarco(DatasetMsMarco, Evaluator):

    @cached_property
    def queries(self) -> dict[str, str]:
        return {
            query.query_id: query.text
            for query in self.ir_dataset.queries_iter()
        }

    @cached_property
    def qrels(self)->Qrels:
        qrels = Qrels(name=self.name)
        for qrel in self.ir_dataset.qrels_iter():
            qrels.add_score(qrel.query_id, qrel.doc_id, qrel.relevance)
        return qrels







if __name__ == "__main__":
    #DocumentMsMarco.build()
    texts=['sql queries in access', 'rivers in south america']
    results=list(DocumentMsMarco.query(texts=texts))
    scores = DocumentMsMarco.evaluate(query_classes=[Query, QueryBasic])
    results
