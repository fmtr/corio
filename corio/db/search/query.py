from __future__ import annotations

from functools import cached_property
from typing import Generic, TypeVar

from qdrant_client.http import models

from corio.inherit import Inherit

from .constants import SIMPLE, DENSE, MULTI, SPARSE


PayloadT = TypeVar("PayloadT")
EmbedderT = TypeVar("EmbedderT")


class Query(Generic[PayloadT, EmbedderT]):
    DESCRIPTION = "rrf_sparse_dense_bm25_then_multi"

    def __init__(self, text: str, *, limit: int):
        self.text = text
        self.embedding = None
        self.limit = limit

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
    def bm25(self):
        return Bm25(self).data

    @cached_property
    def fusion(self):
        return Fusion(self).data

    @cached_property
    def multi(self):
        return Multi(self).data

    @cached_property
    def query(self):
        return dict(prefetch=models.Prefetch(**self.fusion), **self.multi)

    @cached_property
    def request(self):
        return models.QueryRequest(**self.query)


class QueryBasic(Query[PayloadT, EmbedderT]):
    DESCRIPTION = "bm25_only"

    @cached_property
    def query(self):
        return self.bm25 | dict(with_payload=True)


class QueryIndex(Inherit[Query[PayloadT, EmbedderT]], Generic[PayloadT, EmbedderT]):
    ...


class Sparse(QueryIndex[PayloadT, EmbedderT]):
    @cached_property
    def data(self):
        return dict(
            query=self.embedding.sparse,
            using=SPARSE,
            limit=self.limit * 10,
        )


class Dense(QueryIndex[PayloadT, EmbedderT]):
    @cached_property
    def data(self):
        return dict(
            query=self.embedding.dense,
            using=DENSE,
            limit=self.limit * 10,
        )


class Bm25(QueryIndex[PayloadT, EmbedderT]):
    @cached_property
    def data(self):
        return dict(
            query=self.embedding.simple,
            using=SIMPLE,
            limit=self.limit * 10,
        )


class Fusion(QueryIndex[PayloadT, EmbedderT]):
    @cached_property
    def data(self):
        return dict(
            prefetch=[
                models.Prefetch(**self.sparse),
                models.Prefetch(**self.dense),
                models.Prefetch(**self.bm25),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=self.limit * 5,
        )


class Multi(QueryIndex[PayloadT, EmbedderT]):
    @cached_property
    def data(self):
        return dict(
            query=self.embedding.multi,
            using=MULTI,
            limit=self.limit,
            with_payload=True,
        )
