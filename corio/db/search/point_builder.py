from __future__ import annotations

from functools import cached_property

from qdrant_client.http import models

from .constants import BM25, DENSE, MULTI, SPARSE


class Embedding:
    def __init__(self, dense, sparse, multi, bm25):
        self.dense = dense
        self.sparse = dict(indices=list(sparse.keys()), values=list(sparse.values()))
        self.multi = multi
        self.bm25 = dict(indices=bm25.indices, values=bm25.values)


class PointBuilder:
    def __init__(self):
        self.embedding = None

    @cached_property
    def text(self) -> str:
        raise NotImplementedError

    @cached_property
    def id(self) -> int:
        raise NotImplementedError

    @cached_property
    def payload(self) -> dict:
        raise NotImplementedError

    @cached_property
    def point(self) -> models.PointStruct:
        return models.PointStruct(
            id=self.id,
            vector={
                SPARSE: self.embedding.sparse,
                DENSE: self.embedding.dense,
                MULTI: self.embedding.multi,
                BM25: self.embedding.bm25,
            },
            payload=self.payload,
        )
