from __future__ import annotations

from functools import cached_property
from itertools import batched

from FlagEmbedding import BGEM3FlagModel
from fastembed import SparseTextEmbedding
from typing import Self, List, ClassVar, Dict, Any, TYPE_CHECKING

from pydantic import StrictFloat
from qdrant_client.http.models import SparseVector

from corio import dm, logger
from corio.inherit import Inherit
from corio.db.search.constants import DENSE, MULTI, SPARSE, SIMPLE, M3
from corio.db.search import models
from corio.iterator import Iterator

from FlagEmbedding.inference.embedder.encoder_only import m3 as flag_m3_module
# Force-disable tqdm bars emitted inside FlagEmbedding's M3 module.


if TYPE_CHECKING:
    from .document import Document

_m3_tqdm = flag_m3_module.tqdm
_m3_trange = flag_m3_module.trange



def _m3_tqdm_disabled(*args, **kwargs):
    kwargs["disable"] = True
    return _m3_tqdm(*args, **kwargs)


def _m3_trange_disabled(*args, **kwargs):
    kwargs["disable"] = True
    return _m3_trange(*args, **kwargs)


flag_m3_module.tqdm = _m3_tqdm_disabled
flag_m3_module.trange = _m3_trange_disabled


class Vectors(dm.Base):
    simple: SparseVector
    sparse: SparseVector
    dense: List[StrictFloat]
    multi: List[List[StrictFloat]]



class Embedder:
    Vectors = Vectors

    BATCH_SIZE_EMBEDDING = 1_500
    MAX_LENGTH = 256

    def __init__(self):
        with logger.span(f'Initialising {self.__class__.__name__}...'):
            for name in SIMPLE, M3:
                with logger.span(f'Initialising {name}...'):
                    getattr(self, name)

    @cached_property
    def config(self):
        return dict(
            # collection_name=self.COLLECTION_NAME,
            vectors_config={
                DENSE: models.VectorParams(
                    size=self.m3.model.model.config.hidden_size,
                    distance=models.Distance.COSINE,
                    on_disk=True,
                    hnsw_config=models.HnswConfigDiff(m=16),
                ),
                MULTI: models.VectorParams(
                    size=self.m3.model.colbert_linear.out_features,
                    distance=models.Distance.COSINE,
                    on_disk=True,
                    multivector_config=models.MultiVectorConfig(
                        comparator=models.MultiVectorComparator.MAX_SIM,
                    ),
                    hnsw_config=models.HnswConfigDiff(m=0)
                ),
            },
            sparse_vectors_config={
                SPARSE: models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=True),
                    modifier=models.Modifier.IDF,
                ),
                SIMPLE: models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=True),
                    modifier=models.Modifier.IDF,
                ),
            },
            quantization_config=models.ScalarQuantization(
                scalar=models.ScalarQuantizationConfig(
                    type=models.ScalarType.INT8,
                ),
            ),
        )

    @cached_property
    def indexes(self):
        return [
            dict(
                field_name="id",
                field_schema=models.PayloadSchemaType.KEYWORD
            ),
            dict(
                field_name="is_doc",
                field_schema=models.PayloadSchemaType.KEYWORD
            ),
            dict(
                field_name="chunk_idx",
                field_schema=models.PayloadSchemaType.INTEGER
            ),
        ]

    @cached_property
    def m3(self) -> BGEM3FlagModel:
        return BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)

    @cached_property
    def simple(self) -> SparseTextEmbedding:
        return SparseTextEmbedding(model_name="Qdrant/bm25")

    def embed(self, batch: Iterator[Document]):
        texts = [item.payload_obj.text_vector for item in batch]

        logger.info('Encoding M3...')
        with Iterator.span():
            m3 = self.m3.encode(
                texts,
                batch_size=self.BATCH_SIZE_EMBEDDING,
                max_length=self.MAX_LENGTH,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=True,
            )
        logger.info('Encoding simples...')
        with Iterator.span():
            simples = self.simple.embed(
                texts,
                batch_size=self.BATCH_SIZE_EMBEDDING,
            )
        m3 = zip(m3["dense_vecs"], m3["lexical_weights"], m3["colbert_vecs"], simples)
        for item, (dense, sparse, multi, simple) in zip(batch, m3):
            multi=[0.]*self.m3.model.colbert_linear.out_features
            multi=[multi] # todo fix.
            sparse_vector = SparseVector(indices=list(sparse.keys()), values=list(sparse.values()))
            simple_vector = SparseVector(indices=list(simple.indices), values=list(simple.values))
            vectors = self.Vectors(
                simple=simple_vector,
                sparse=sparse_vector,
                dense=dense,
                multi=multi
            )
            item.vectors_obj = vectors
        return batch

    def add_vectors(self, documents: Iterator[Document]) -> Iterator[Document]:

        for batch in batched(documents, self.BATCH_SIZE_EMBEDDING):
            yield from self.embed(batch)