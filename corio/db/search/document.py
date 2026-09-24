"""

Document and payload models for `corio.db.search`.

"""
from __future__ import annotations

from functools import cached_property, lru_cache
from pydantic import Field
from pydantic.json_schema import SkipJsonSchema
from qdrant_client.http.models import PointStruct
from typing import TYPE_CHECKING, ClassVar

from corio import dm
from corio.db.search.client import Client
from corio.db.search.constants import TOKENS_WORDS_FACTOR
from corio.db.search.embedder import Embedder, Vectors
from corio.db.search.query import Query
from corio.function import ccp
from corio.hash import get_hash_int
from corio.strings import chunk_sliding

if TYPE_CHECKING:
    from corio.db.search.builder import Builder
    from corio.db.search.evaluator import Evaluator


class Payload(dm.Base):
    """

    Base payload stored with each search point and root of a collection definition.

    """

    id: str
    text: str
    is_doc: bool = True
    chunk_idx: int | None = None
    score: SkipJsonSchema[float | None] = Field(default=None, exclude=True)

    MAX_LENGTH: ClassVar[int] = 256

    @ccp
    def Document(cls) -> type[Document]:
        """

        Return the internal document type bound to this payload.

        """
        document = type(
            f"{cls.__name__}Document",
            (Document,),
            {"__module__": cls.__module__, "Payload": cls},
        )
        return document

    @ccp
    def Builder(cls) -> type[Builder]:
        """

        Return the builder configured for this payload.

        """
        from corio.db.search.builder import Builder
        return Builder

    @ccp
    def Evaluator(cls) -> type[Evaluator]:
        """

        Return the evaluator configured for this payload.

        """
        from corio.db.search.evaluator import Evaluator
        return Evaluator

    @ccp
    def Query(cls) -> type[Query]:
        return Query

    @ccp
    def IS_MULTI(cls) -> bool:
        return True

    @cached_property
    def text_vector(self) -> str:
        return self.text

    @classmethod
    def get_embedder(cls) -> Embedder:
        return Embedder(is_multi=cls.IS_MULTI)

    @classmethod
    def build(cls, client: Client | None = None):
        builder = cls.Builder(payload_type=cls, client=client)
        return builder.build()

    @classmethod
    def query(cls, texts: list[str], client: Client | None = None):
        from corio.db.search.querier import Querier

        querier = Querier(payload_type=cls, client=client)
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
        evaluator = cls.Evaluator(payload_type=cls, client=client)
        return evaluator.evaluate(
            query_classes=query_classes,
            limit=limit,
            metrics=metrics,
        )


class Document(PointStruct):
    """

    Internal Qdrant point model bound to a payload type.

    """

    Payload: ClassVar[type[Payload]] = Payload
    Embedder: ClassVar[type[Embedder]] = Embedder
    Query: ClassVar[type[Query]] = Query

    STRIDE_FACTOR: ClassVar[float] = 0.25

    @property
    def payload_obj(self) -> Payload:
        return self.Payload.model_validate(self.payload)

    @payload_obj.setter
    def payload_obj(self, value: Payload) -> None:
        self.payload = value.model_dump()

    @property
    def vectors_obj(self) -> Vectors:
        return Vectors.model_validate(self.vector)

    @vectors_obj.setter
    def vectors_obj(self, value: Vectors) -> None:
        self.vector = value.model_dump()

    @property
    def text_vector(self) -> str:
        return self.payload_obj.text_vector

    def chunk(self, text: str) -> list[str]:
        window = int(self.Payload.MAX_LENGTH * TOKENS_WORDS_FACTOR)
        stride = int(window * self.STRIDE_FACTOR)
        return chunk_sliding(text, window, stride)

    @property
    def points(self):
        yield self

        payload = self.payload_obj
        for i, subtext in enumerate(self.chunk(payload.text)):
            payload = self.payload_obj
            payload.text = subtext
            payload.chunk_idx = i
            payload.is_doc = False
            document_id = get_hash_int(f"{payload.id}/{i}")
            chunk = self.__class__(id=document_id, vector=[])
            chunk.payload_obj = payload
            yield chunk

    @classmethod
    @lru_cache()
    def get_embedder(cls) -> Embedder:
        return cls.Payload.get_embedder()
