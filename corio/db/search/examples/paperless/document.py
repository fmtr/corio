"""Paperless documents represented in the Corio search index."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pydantic import Field, computed_field
from typing import Annotated, Any, ClassVar

from corio import dm, env
from corio.db.search.document import Document, Index
from corio.function import ccp
from corio.hash import get_hash_readable


class PaperlessIndexedRoot(dm.Base):
    """The payload fields needed to reconcile an indexed Paperless root."""

    id: str
    paperless_id: int
    sync_fingerprint: str


class Paperless(Document):
    """A Paperless document, either from a list page or a detail response."""

    paperless_id: Annotated[int, Index()]
    instance: str
    title: str
    modified: Annotated[datetime, Index()]
    added: Annotated[datetime, Index()]
    checksum: Annotated[str | None, Index()] = None
    archive_checksum: Annotated[str | None, Index()] = None
    tags: Annotated[list[str], Index()] = Field(default_factory=list)
    correspondent: Any = None
    document_type: Any = None
    custom_fields: Any = None
    mime_type: str | None = None
    page_count: int | None = None
    original_filename: str | None = None
    filename: str | None = None
    archive_filename: str | None = None
    source_url: str | None = None

    IS_MULTI: ClassVar[bool] = False

    @classmethod
    def from_paperless(cls, data: dict[str, Any], *, instance: str) -> "Paperless":
        """Convert either a truncated or complete Paperless response."""
        values = dict(data)
        paperless_id = values.pop("id")
        values["id"] = str(paperless_id)
        values["paperless_id"] = paperless_id
        values["instance"] = instance
        values["tags"] = [str(tag) for tag in values.get("tags", [])]
        values["original_filename"] = values.pop("original_file_name", values.get("original_filename"))
        values["archive_filename"] = values.pop("archived_file_name", values.get("archive_filename"))
        values["text"] = values.pop("content", "")
        return cls.model_validate(values)

    @computed_field
    @property
    def sync_fingerprint(self) -> str:
        canonical = json.dumps(
            [self.modified.isoformat(), self.checksum, self.archive_checksum],
            separators=(",", ":"),
        )
        return get_hash_readable(canonical)

    @property
    def text_vector(self) -> str:
        if not self.is_doc:
            return self.text
        return f"{self.title}\n{self.text}"

    @classmethod
    async def build(cls, *, client, paperless):
        """Reconcile the complete Paperless instance with the search collection."""
        builder = cls.Builder(document_type=cls, client=client, paperless=paperless)
        return await builder.build()

    @ccp
    def Builder(cls):
        from corio.db.search.examples.paperless.builder import PaperlessBuilder
        return PaperlessBuilder


async def main():
    """Reconcile the configured Paperless instance with the search collection."""
    from corio.db.search.client import Client
    from corio.db.search.examples.paperless.client import PaperlessClient

    paperless = PaperlessClient(
        "https://documents.sv.fmtr.dev",
        env.get("DOCUMENTS_TOKEN"),
        instance="documents",
    )
    async with Client() as client:
        await Paperless.build(client=client, paperless=paperless)


if __name__ == "__main__":
    asyncio.run(main())
