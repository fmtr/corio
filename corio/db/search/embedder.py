"""

Embedding helpers for `corio.db.search`.

"""
from __future__ import annotations

from itertools import batched

from collections.abc import Iterable
from pydantic import StrictFloat
from qdrant_client.http.models import SparseVector
from typing import TYPE_CHECKING, List

from corio import dm
from corio.constants import Constants
from corio.db.search.constants import MULTI_SIZE
from corio.function import ccp

if TYPE_CHECKING:
    from corio.db.search.document import Point


class Vectors(dm.Base):
    """

    Vector payload returned by the embedder.

    """

    simple: SparseVector
    sparse: SparseVector
    dense: List[StrictFloat]
    multi: List[List[StrictFloat]]


class Embedder:
    """

    Build dense, sparse, and multi-vector representations.

    """

    Vectors = Vectors
    MAX_LENGTH = 256

    def __init__(self, *, is_multi: bool = True, max_length: int = MAX_LENGTH):
        """

        Configure the embedder without loading its models.

        """
        self.is_multi = is_multi
        self.max_length = max_length

    @ccp
    def m3(cls):
        """

        Load the BGE-M3 embedding model once for the process.

        """
        from FlagEmbedding import BGEM3FlagModel

        return BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)

    @ccp
    def simple(cls):
        """

        Load the sparse BM25 embedding model once for the process.

        """
        from fastembed import SparseTextEmbedding

        return SparseTextEmbedding(model_name="Qdrant/bm25")

    def get_multi(self, m3):
        """

        Return ColBERT vectors or a zero-filled fallback.

        """
        if self.is_multi:
            return m3["colbert_vecs"]

        import numpy as np

        batch_size = len(m3["dense_vecs"])
        return np.zeros((batch_size, 1, MULTI_SIZE), dtype=np.float32).tolist()

    def get_vectors(self, dense, sparse, multi, simple):
        sparse_vector = SparseVector(indices=list(sparse.keys()), values=list(sparse.values()))
        simple_vector = SparseVector(indices=list(simple.indices), values=list(simple.values))
        return self.Vectors(
            simple=simple_vector,
            sparse=sparse_vector,
            dense=dense,
            multi=multi,
        )

    def embed(self, texts: list[str]) -> list[Vectors]:
        """Embed the supplied texts as one request."""
        m3 = self.m3.encode(
            texts,
            batch_size=len(texts),
            max_length=self.max_length,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=self.is_multi,
        )
        multi = self.get_multi(m3)
        simples = self.simple.embed(texts)
        vectors = zip(m3["dense_vecs"], m3["lexical_weights"], multi, simples)
        result = []
        for dense, sparse, multi_vectors, simple in vectors:
            result.append(self.get_vectors(dense, sparse, multi_vectors, simple))
        return result


class EmbedderClient:
    """Consume the remote embedding service."""

    Vectors = Vectors
    BATCH_SIZE_BASE = 1_500
    BATCH_SIZE_MULTI_FACTOR = 32 / BATCH_SIZE_BASE

    def __init__(
            self,
            *,
            is_multi: bool = True,
            max_length: int = Embedder.MAX_LENGTH,
            url: str = Constants.FMTR_DB_EMBED_URL_DEFAULT,
    ):
        self.is_multi = is_multi
        self.max_length = max_length
        self.url = url

    @property
    def batch_size(self) -> int:
        if not self.is_multi:
            return self.BATCH_SIZE_BASE
        return int(self.BATCH_SIZE_BASE * self.BATCH_SIZE_MULTI_FACTOR)

    def embed(self, texts: list[str]) -> list[Vectors]:
        from corio import https

        response = https.client.post(
            f"{self.url}/embed",
            json=dict(
                is_multi=self.is_multi,
                max_length=self.max_length,
                texts=texts,
            ),
        )
        return [self.Vectors.model_validate(vector) for vector in response.json()]

    def add_vectors(self, points: Iterable[Point]) -> Iterable[Point]:
        """Embed points in batches and yield them back."""
        for batch in batched(points, self.batch_size):
            vectors = self.embed([point.text_vector for point in batch])
            for point, vector in zip(batch, vectors):
                point.vectors = vector
                yield point
