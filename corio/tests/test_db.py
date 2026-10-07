import pytest
from datetime import datetime
from qdrant_client.http import models
from types import SimpleNamespace
from typing import Annotated
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

from corio.db.search.document import Document, Index
from corio.db.search.embedder import Embedder, EmbedderClient


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


@pytest.mark.asyncio
async def test_embedder_client_calls_api_with_vectors_from_embedder():
    m3 = Mock()
    m3.encode.side_effect = lambda texts, **kwargs: dict(
        dense_vecs=[[0.1] if texts[0] == "one" else [0.2]],
        lexical_weights=[{1: 0.3} if texts[0] == "one" else {2: 0.4}],
    )
    simple = Mock()
    simple.embed.side_effect = lambda texts: [
        SimpleNamespace(
            indices=[3] if texts[0] == "one" else [4],
            values=[0.5] if texts[0] == "one" else [0.6],
        )
    ]
    embedder = Embedder(is_multi=False, max_length=128)
    points = []
    for index, text in enumerate(("one", "two")):
        point = Document.Point(id=index + 1, vector=[])
        point.document = Document(id=text, text=text)
        points.append(point)

    async def embed_api_call(url, *, json, timeout):
        assert url == "https://embed.example/embed"
        assert timeout == 120
        assert json["is_multi"] is False
        assert json["max_length"] == 128
        vectors = embedder.embed(json["texts"])
        response = Mock()
        response.json.return_value = [vector.model_dump() for vector in vectors]
        return response

    client = EmbedderClient(is_multi=False, max_length=128, url="https://embed.example")
    client.BATCH_SIZE_BASE = 1
    client.BATCH_SIZE_MULTI_FACTOR = 1

    with patch.object(Embedder, "m3", m3), patch.object(Embedder, "simple", simple):
        http_client = AsyncMock()
        http_client.__aenter__.return_value = http_client
        http_client.post.side_effect = embed_api_call
        with patch("corio.https.AsyncClient", return_value=http_client):
            embedded = await client.add_vectors(points)

        post = http_client.post

    assert embedded == points
    assert [point.vectors.dense for point in points] == [[0.1], [0.2]]
    assert [point.vectors.simple.indices for point in points] == [[3], [4]]
    assert post.call_count == 2
    assert [call.kwargs["json"]["texts"] for call in post.call_args_list] == [["one"], ["two"]]
    assert m3.encode.call_args_list[0].kwargs["max_length"] == 128
