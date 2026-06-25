from __future__ import annotations

from functools import cached_property

from FlagEmbedding import BGEM3FlagModel
from fastembed import SparseTextEmbedding

from corio.inherit import Inherit

from .constants import BM25_MODEL
from .point_builder import Embedding
from corio.db.search.collection import Collection

class Embedder(Inherit[Collection]):
    @cached_property
    def m3(self) -> BGEM3FlagModel:
        return BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)

    @cached_property
    def bm25(self) -> SparseTextEmbedding:
        return SparseTextEmbedding(model_name=BM25_MODEL)

    def embed(self, batch):
        texts = [item.text for item in batch]
        m3 = self.m3.encode(
            texts,
            batch_size=self.BATCH_SIZE_EMBEDDING,
            max_length=self.MAX_LENGTH,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=True,
        )
        bm25 = self.bm25.embed(
            texts,
            batch_size=self.BATCH_SIZE_EMBEDDING,
        )
        m3 = zip(m3["dense_vecs"], m3["lexical_weights"], m3["colbert_vecs"], bm25)
        for item, (dense, sparse, multi, bm25_vec) in zip(batch, m3):
            item.embedding = Embedding(dense, sparse, multi, bm25_vec)
        return batch
