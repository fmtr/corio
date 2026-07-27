"""

Document and payload models for `corio.db.search`.

"""

from __future__ import annotations

from functools import cached_property, lru_cache
from pydantic import Field
from pydantic.json_schema import SkipJsonSchema
from qdrant_client.http import models
from qdrant_client.http.models import PointStruct
from typing import ClassVar, Generic, TYPE_CHECKING, TypeVar

from corio import dm
from .client import Client
from .constants import TOKENS_WORDS_FACTOR
from .embedder import Embedder, Vectors
from .query import Query
from ...hash import get_hash_int
from ...strings import chunk_sliding

if TYPE_CHECKING:
    from .builder import Builder
    from .evaluator import Evaluator




class Payload(dm.Base):
    """

    Base payload stored with each search point.

    """

    id: str
    text: str
    is_doc: bool = True
    chunk_idx: int | None = None
    score: SkipJsonSchema[float | None] = Field(default=None, exclude=True)

    @cached_property
    def text_vector(self) -> str:
        return self.text


PayloadT = TypeVar("PayloadT", bound=Payload)
EmbedderT = TypeVar("EmbedderT", bound=Embedder)
EvaluatorT = TypeVar("EvaluatorT", bound="Evaluator")

class Document(PointStruct, Generic[PayloadT, EmbedderT, EvaluatorT]):
    """

    Search point model with helpers for payload, vectors, and chunking.

    """

    Payload: ClassVar = Payload
    Embedder: ClassVar = Embedder
    Query: ClassVar = Query

    IS_MULTI: ClassVar[bool] = True
    STRIDE_FACTOR: ClassVar[float] = 0.25

    @property
    def payload_obj(self) -> PayloadT:
        return self.Payload.model_validate(self.payload)

    @payload_obj.setter
    def payload_obj(self, value: PayloadT) -> None:
        self.payload = value.model_dump()

    @property
    def vectors_obj(self) -> Vectors:
        return Vectors.model_validate(self.vector)

    @vectors_obj.setter
    def vectors_obj(self, value: Vectors) -> None:
        self.vector = value.model_dump()

    @property
    def text_vector(self) -> str:
        """

        Return the text used for embedding and retrieval.

        """

        return self.payload_obj.text_vector
        
    def chunk(self,text: str)->list[str]:
        """

        Split text into overlapping windows sized for the builder.

        """

        max_length=self.get_builder().MAX_LENGTH
        window = int(max_length * TOKENS_WORDS_FACTOR)
        stride = int(window * self.STRIDE_FACTOR)
        return chunk_sliding(text,window,stride)

    @property
    def points(self):
        """

        Yield the document and its derived chunk points.

        """

        yield self

        payload = self.payload_obj

        for i, subtext in enumerate(self.chunk(payload.text)):
            payload = self.payload_obj
            payload.text = subtext
            payload.chunk_idx = i
            payload.is_doc = False
            id = get_hash_int(f'{payload.id}/{i}')
            chunk = self.__class__(id=id, vector=[])
            chunk.payload_obj = payload
            yield chunk

    @classmethod
    @lru_cache()
    def get_builder(self) -> type[Builder]:
        """

        Return the builder class bound to this document type.

        """

        from .builder import Builder
        return Builder



    @classmethod
    @lru_cache()
    def get_embedder(cls) -> EmbedderT:
        """

        Return the embedder configured for this document type.

        """

        return cls.Embedder(is_multi=cls.IS_MULTI)

    @classmethod
    def build(cls, client: Client | None = None):
        """

        Build the collection for this document type.

        """

        Builder=cls.get_builder()
        builder = Builder(client)
        return builder.build()

    @classmethod
    def query(cls, texts: list[str], client: Client | None = None):
        """

        Run search queries for the given texts.

        """

        from .querier import Querier
        querier = Querier(doc_type=cls, client=client)
        return querier.query(texts)

    @classmethod
    def evaluate(
        cls,
        query_classes: list[type[Query]] | None = None,
        *,
        limit: int = 100,
        metrics=None,
        client: Client | None = None,
    ):
        """

        Evaluate configured query classes against stored qrels.

        """

        Evaluator = cls.Evaluator
        evaluator = Evaluator(Document=cls, client=client)
        return evaluator.evaluate(
            query_classes=query_classes,
            limit=limit,
            metrics=metrics,
        )
