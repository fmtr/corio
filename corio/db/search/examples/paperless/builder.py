"""Reconciliation builder for Paperless documents."""
from __future__ import annotations

from itertools import batched

import asyncio
from collections.abc import AsyncIterator
from qdrant_client.http import models

from corio import iterator
from corio.db.search.builder import Builder
from corio.db.search.document import Point
from corio.db.search.examples.paperless.document import PaperlessIndex
from corio.hash import get_hash_int
from corio.iterator import ilist


class PaperlessBuilder(Builder):
    """Reconcile Paperless roots and their chunks without partial updates."""

    DETAIL_BATCH_SIZE = 16

    def __init__(self, *, document_type, client, paperless):
        super().__init__(document_type=document_type, client=client)
        self.paperless = paperless

    def get_point(self, data) -> Point:
        point = self.Document.Point(id=get_hash_int(data.id), vector=[])
        point.document = data
        return point

    async def indexed_roots(self) -> ilist[PaperlessIndex]:
        roots = ilist()
        offset = None
        scroll_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="is_doc",
                    match=models.MatchValue(value=True),
                )
            ]
        )
        while True:
            kwargs = dict(
                collection_name=self.name,
                scroll_filter=scroll_filter,
                with_payload=["paperless_id", "modified", "checksum", "archive_checksum"],
                with_vectors=False,
                limit=1000,
            )
            if offset is not None:
                kwargs["offset"] = offset
            page, offset = await self.client.scroll(**kwargs)
            roots.extend(PaperlessIndex.model_validate(point.payload) for point in page)
            if offset is None:
                return roots

    async def delete_documents(self, document_ids: list[str]) -> None:
        if not document_ids:
            return
        await self.client.delete(
            collection_name=self.name,
            points_selector=models.Filter(
                must=[
                    models.FieldCondition(
                        key="id",
                        match=models.MatchAny(any=document_ids),
                    )
                ]
            ),
        )

    async def points(self) -> AsyncIterator[Point]:
        """Yield full points only for Paperless documents needing replacement."""
        data = iterator.Iterator(self.data)
        for documents in batched(data, self.DETAIL_BATCH_SIZE):
            details = await asyncio.gather(
                *(self.paperless.get_document(document.paperless_id) for document in documents)
            )
            for detail in details:
                yield self.get_point(detail)

    async def build(self):
        """Reconcile Paperless metadata, then use the base batch ingest path."""
        source_documents = await self.paperless.list_documents()
        await self.collection()
        indexed_documents = await self.indexed_roots()
        source_by_id = ilist(source_documents).id
        indexed_by_id = ilist(indexed_documents).id
        replacement_ids = ilist()

        for indexed in indexed_documents:
            document_id = indexed.id
            if document_id not in source_by_id:
                replacement_ids.append(document_id)
                continue
            source = source_by_id[document_id]
            if source.sync_fingerprint != indexed.sync_fingerprint:
                replacement_ids.append(document_id)

        await self.delete_documents(replacement_ids)
        self.data = [
            source
            for source in source_documents
            if source.id not in indexed_by_id or source.id in replacement_ids
        ]

        return await super().build()
