"""

Query shapes for `corio.db.search`.

"""

from __future__ import annotations

from functools import cached_property
from qdrant_client.http import models
from typing import Generic, TypeVar

from corio.inherit import Inherit
from .constants import SIMPLE, DENSE, MULTI, SPARSE

PayloadT = TypeVar("PayloadT")
EmbedderT = TypeVar("EmbedderT")


class Query(Generic[PayloadT, EmbedderT]):
    """

    Base qdrant query shape for the search stack.

    """

    DESCRIPTION = "rrf_sparse_dense_bm25_then_multi"

    def __init__(self, text: str, *, limit: int, is_multi: bool = True):
        self.text = text
        self.embedding = None
        self.limit = limit
        self.is_multi = is_multi
        self.hits=[]

    @property
    def text_vector(self) -> str:
        return self.text

    @property
    def vectors_obj(self):
        return self.embedding

    @vectors_obj.setter
    def vectors_obj(self, value) -> None:
        self.embedding = value

    @cached_property
    def sparse(self):
        return Sparse(self).data

    @cached_property
    def dense(self):
        return Dense(self).data

    @cached_property
    def simple(self):
        return Simple(self).data

    @cached_property
    def fusion(self):
        return Fusion(self).data

    @cached_property
    def multi(self):
        return Multi(self).data

    @cached_property
    def data(self):
        if self.is_multi:
            data=dict(prefetch=models.Prefetch(**self.fusion), **self.multi)
        else:
            data=self.fusion
        return data

    @cached_property
    def query(self):
        return self.data|self.root

    @cached_property
    def root(self):
        return dict(with_payload=True,limit=self.limit)

    @cached_property
    def request(self):
        return models.QueryRequest(**self.query)

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self.text)})"


class QueryBasic(Query[PayloadT, EmbedderT]):
    """

    Query shape that skips multi-vector reranking.

    """

    DESCRIPTION = "simple"

    @cached_property
    def data(self):
        return self.simple


class QueryIndex(Inherit[Query[PayloadT, EmbedderT]], Generic[PayloadT, EmbedderT]):
    """

    Shared base for cached query variants.

    """


class Sparse(QueryIndex[PayloadT, EmbedderT]):
    """

    Sparse vector query payload.

    """

    @cached_property
    def data(self):
        return dict(
            query=self.embedding.sparse,
            using=SPARSE,
            limit=self.limit * 10,
        )


class Dense(QueryIndex[PayloadT, EmbedderT]):
    """

    Dense vector query payload.

    """

    @cached_property
    def data(self):
        return dict(
            query=self.embedding.dense,
            using=DENSE,
            limit=self.limit * 10,
        )


class Simple(QueryIndex[PayloadT, EmbedderT]):
    """

    BM25 query payload.

    """

    @cached_property
    def data(self):
        return dict(
            query=self.embedding.simple,
            using=SIMPLE,
            limit=self.limit * 10,
        )


class Fusion(QueryIndex[PayloadT, EmbedderT]):
    """

    Multi-source fusion query payload.

    """

    @cached_property
    def data(self):

        return dict(
            prefetch=[
                models.Prefetch(**self.sparse),
                models.Prefetch(**self.dense),
                models.Prefetch(**self.simple),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=self.limit * 5,
        )


class Multi(QueryIndex[PayloadT, EmbedderT]):
    """

    ColBERT multi-vector query payload.

    """

    @cached_property
    def data(self):
        return dict(
            query=self.embedding.multi,
            using=MULTI,
        )
