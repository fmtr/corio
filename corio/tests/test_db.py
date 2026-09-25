from datetime import datetime
from qdrant_client.http import models
from typing import Annotated
from uuid import UUID

from corio.db.search.document import Document, Index


class IndexedDocument(Document):
    created_at: Annotated[datetime, Index()]
    external_id: Annotated[UUID, Index()]


def test_indexes_are_derived_from_document_fields():
    assert Document.indexes == [
        {
            "field_name": "id",
            "field_schema": models.PayloadSchemaType.KEYWORD,
        },
        {
            "field_name": "is_doc",
            "field_schema": models.PayloadSchemaType.BOOL,
        },
        {
            "field_name": "chunk_idx",
            "field_schema": models.PayloadSchemaType.INTEGER,
        },
    ]


def test_indexed_subclass_fields_are_mapped_from_python_types():
    assert IndexedDocument.indexes[-2:] == [
        {
            "field_name": "created_at",
            "field_schema": models.PayloadSchemaType.DATETIME,
        },
        {
            "field_name": "external_id",
            "field_schema": models.PayloadSchemaType.UUID,
        },
    ]
