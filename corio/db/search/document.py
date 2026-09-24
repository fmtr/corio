"""

Document and point models for `corio.db.search`.

"""
from __future__ import annotations

from functools import cached_property
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


class Document(dm.Base):
    """

    Base document stored with each search point and root of a collection definition.

    """

    id: str
    text: str
    is_doc: bool = True
    chunk_idx: int | None = None
    score: SkipJsonSchema[float | None] = Field(default=None, exclude=True)

    MAX_LENGTH: ClassVar[int] = 256
    IS_MULTI: ClassVar[bool] = True

    @ccp
    def Point(cls) -> type[Point]:
        """

        Return the internal point type bound to this document.

        """
        point = type(
            f"{cls.__name__}Point",
            (Point,),
            {"__module__": cls.__module__, "Document": cls},
        )
        return point

    @ccp
    def Builder(cls) -> type[Builder]:
        """

        Return the builder configured for this document.

        """
        from corio.db.search.builder import Builder
        return Builder

    @ccp
    def Evaluator(cls) -> type[Evaluator]:
        """

        Return the evaluator configured for this document.

        """
        from corio.db.search.evaluator import Evaluator
        return Evaluator

    @ccp
    def Query(cls) -> type[Query]:
        return Query

    @cached_property
    def text_vector(self) -> str:
        return self.text

    @ccp
    def embedder(cls) -> Embedder:
        return Embedder(is_multi=cls.IS_MULTI)

    @classmethod
    def build(cls, client: Client | None = None):
        builder = cls.Builder(document_type=cls, client=client)
        return builder.build()

    @classmethod
    def query(cls, texts: list[str], client: Client | None = None):
        from corio.db.search.querier import Querier

        querier = Querier(document_type=cls, client=client)
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
        evaluator = cls.Evaluator(document_type=cls, client=client)
        return evaluator.evaluate(
            query_classes=query_classes,
            limit=limit,
            metrics=metrics,
        )


class Point(PointStruct):
    """

    Internal Qdrant point model bound to a document type.

    """

    Document: ClassVar[type[Document]] = Document
    STRIDE_FACTOR: ClassVar[float] = 0.25

    @property
    def document_obj(self) -> Document:
        return self.Document.model_validate(self.payload)

    @document_obj.setter
    def document_obj(self, value: Document) -> None:
        self.payload = value.model_dump()

    @property
    def vectors_obj(self) -> Vectors:
        return Vectors.model_validate(self.vector)

    @vectors_obj.setter
    def vectors_obj(self, value: Vectors) -> None:
        self.vector = value.model_dump()

    @property
    def text_vector(self) -> str:
        return self.document_obj.text_vector

    def chunk(self, text: str) -> list[str]:
        window = int(self.Document.MAX_LENGTH * TOKENS_WORDS_FACTOR)
        stride = int(window * self.STRIDE_FACTOR)
        return chunk_sliding(text, window, stride)

    @property
    def points(self):
        yield self

        document = self.document_obj
        for i, subtext in enumerate(self.chunk(document.text)):
            document = self.document_obj
            document.text = subtext
            document.chunk_idx = i
            document.is_doc = False
            point_id = get_hash_int(f"{document.id}/{i}")
            chunk = self.__class__(id=point_id, vector=[])
            chunk.document_obj = document
            yield chunk
