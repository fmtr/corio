from __future__ import annotations

import typing

from itertools import batched

from qdrant_client.http import models

from corio.inherit import Inherit
from corio.iterator import Iterator

from .point_builder import PointBuilder

from corio.db.search.collection import Collection

class Dataset(Inherit[Collection]):
    POINT_BUILDER_CLS = PointBuilder
    MAX_RETRIES = 3

    @property
    def BATCH_SIZE_DATASET(self):
        return self.BATCH_SIZE_EMBEDDING

    @property
    def docs(self) -> Iterator:
        raise NotImplementedError

    @property
    def points(self) -> typing.Iterable[models.PointStruct]:
        batches = Iterator(batched(self.docs, self.BATCH_SIZE_DATASET))
        for batch in batches:
            batch = list(batch)
            batch = self.embedder.embed(batch)
            for point in Iterator((doc.point for doc in batch), total=len(batch)):
                yield point
