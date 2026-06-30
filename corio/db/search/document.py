from __future__ import annotations

from functools import cached_property, lru_cache
from typing import ClassVar, Generic, TYPE_CHECKING, TypeVar

from qdrant_client.http import models
from qdrant_client.http.models import PointStruct

from .constants import SIMPLE, DENSE, MULTI, SPARSE, TOKENS_WORDS_FACTOR
from corio import dm, Client
from .embedder import Embedder, Vectors
from ...hash import get_hash_int
from ...strings import chunk_sliding

if TYPE_CHECKING:
    from .builder import Builder




class Payload(dm.Base):
    id: str
    text: str
    is_doc: bool = True
    chunk_idx: int | None = None

    @cached_property
    def text_vector(self) -> str:
        raise NotImplementedError()


PayloadT = TypeVar("PayloadT", bound=Payload)
EmbedderT = TypeVar("EmbedderT", bound=Embedder)


class Document(PointStruct, Generic[PayloadT, EmbedderT]):
    Payload: ClassVar[type[PayloadT]] = Payload
    Embedder: ClassVar[type[EmbedderT]] = Embedder
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
        
    def chunk(self,text: str)->list[str]:
        max_length=self.get_builder().MAX_LENGTH
        window = int(max_length * TOKENS_WORDS_FACTOR)
        stride = int(window * self.STRIDE_FACTOR)
        return chunk_sliding(text,window,stride)

    @property
    def points(self):
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
        from .builder import Builder
        return Builder

    @classmethod
    @lru_cache()
    def get_embedder(cls) -> EmbedderT:
        return cls.Embedder(is_multi=cls.IS_MULTI)

    @classmethod
    def build(cls, client: Client | None = None):
        Builder=cls.get_builder()
        builder = Builder(client)
        return builder.build()
