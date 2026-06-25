from __future__ import annotations

from collections.abc import Iterable
from functools import cached_property

from qdrant_client.http import models

from .client import Client
from .constants import BM25, DENSE, MULTI, SPARSE


class Collection:
    COLLECTION_NAME = "search"
    BATCH_SIZE_EMBEDDING = 50

    MAX_LENGTH = 1024
    DENSE_SIZE = 1024
    MULTI_SIZE = 1024

    @cached_property
    def COLLECTION_CONFIG(self):
        return {
            "collection_name": self.COLLECTION_NAME,
            "vectors_config": {
                DENSE: models.VectorParams(
                    size=self.DENSE_SIZE,
                    distance=models.Distance.COSINE,
                ),
                MULTI: models.VectorParams(
                    size=self.MULTI_SIZE,
                    distance=models.Distance.COSINE,
                    multivector_config=models.MultiVectorConfig(
                        comparator=models.MultiVectorComparator.MAX_SIM,
                    ),
                ),
            },
            "sparse_vectors_config": {
                SPARSE: models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=True),
                    modifier=models.Modifier.IDF,
                ),
                BM25: models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=True),
                    modifier=models.Modifier.IDF,
                ),
            },
            "quantization_config": models.ScalarQuantization(
                scalar=models.ScalarQuantizationConfig(
                    type=models.ScalarType.INT8,
                ),
            ),
        }

    @cached_property
    def client(self) -> Client:
        return Client()

    @cached_property
    def models(self):
        return models

    @cached_property
    def embedder(self):
        from corio.db.search.embedder import Embedder
        return Embedder(self)

    @property
    def collection(self) -> None:
        if not self.client.collection_exists(collection_name=self.COLLECTION_NAME):
            self.client.create_collection(**self.COLLECTION_CONFIG)
        return ...

    def query(self, texts: Iterable[str], *, limit: int = 10, query_cls=None):
        from .query import Query
        query_cls=query_cls or Query

        queries = [query_cls(self, text=text, limit=limit) for text in texts]
        queries = self.embedder.embed(queries)
        requests = [query.request for query in queries]

        results = self.client.query_batch_points(
            collection_name=self.COLLECTION_NAME,
            requests=requests,
        )
        return [result.points for result in results]

    def insert(self, dataset_cls) -> None:
        self.collection
        dataset = dataset_cls(self)

        self.client.local_inference_batch_size = dataset.BATCH_SIZE_DATASET
        self.client.update_collection(
            collection_name=self.COLLECTION_NAME,
            optimizer_config=models.OptimizersConfigDiff(indexing_threshold=0),
        )
        self.client.upload_points(
            collection_name=self.COLLECTION_NAME,
            points=dataset.points,
            batch_size=dataset.BATCH_SIZE_DATASET,
            parallel=1,
            method="fork",
            max_retries=dataset.MAX_RETRIES,
            wait=True,
        )
