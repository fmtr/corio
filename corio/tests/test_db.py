import pytest
import warnings
from datetime import datetime
from qdrant_client.http import models
from types import SimpleNamespace
from typing import Annotated
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

from corio.db.search.document import Document, Index
from corio.db.search.embedder import Embedder, EmbedderClient
from corio.db.search.examples.paperless import PaperlessClient, Paperless
from corio.db.search.examples.paperless.builder import PaperlessBuilder


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
    with warnings.catch_warnings(record=True) as caught:
        [point.model_dump() for point in points]
    assert caught == []
    assert post.call_count == 2
    assert [call.kwargs["json"]["texts"] for call in post.call_args_list] == [["one"], ["two"]]
    assert m3.encode.call_args_list[0].kwargs["max_length"] == 128


class Response:
    def __init__(self, value):
        self.value = value

    def raise_for_status(self):
        return None

    def json(self):
        return self.value


@pytest.mark.asyncio
async def test_paperless_list_paginates_without_content_download():
    responses = [
        Response({"results": [{"id": 1, "title": "One", "content": "", "modified": "2024-01-01T00:00:00Z",
                               "added": "2024-01-01T00:00:00Z", "checksum": "a"}],
                  "next": "http://paperless/api/documents/?page=2"}),
        Response({"results": [{"id": 2, "title": "Two", "content": "", "modified": "2024-01-02T00:00:00Z",
                               "added": "2024-01-02T00:00:00Z", "checksum": "b"}], "next": None}),
    ]
    http = AsyncMock()
    http.get.side_effect = responses
    http.__aenter__.return_value = http
    client = PaperlessClient("https://paperless/", "secret", instance="home")

    with patch("corio.https.AsyncClient", return_value=http):
        documents = await client.list_documents()

    assert [document.id for document in documents] == ["1", "2"]
    assert http.get.call_args_list[0].args == ("https://paperless/api/documents/?truncate_content=true",)
    assert http.get.call_args_list[1].args == ("https://paperless/api/documents/?page=2",)


@pytest.mark.asyncio
async def test_paperless_detail_is_converted_to_same_document_type():
    http = AsyncMock()
    http.get.return_value = Response({
        "id": 7,
        "title": "Receipt",
        "content": "OCR text",
        "modified": "2024-01-01T00:00:00Z",
        "added": "2024-01-01T00:00:00Z",
        "checksum": "checksum",
        "tags": [3],
    })
    http.__aenter__.return_value = http
    client = PaperlessClient("https://paperless", "secret", instance="home")

    with patch("corio.https.AsyncClient", return_value=http):
        document = await client.get_document(7)

    assert isinstance(document, Paperless)
    assert document.text_vector == "Receipt\nOCR text"
    assert document.tags == ["3"]
    assert http.get.call_args.args == ("https://paperless/api/documents/7/",)


def test_paperless_fingerprint_is_deterministic_and_sensitive():
    values = {
        "id": 1,
        "title": "Title",
        "content": "Text",
        "modified": "2024-01-01T00:00:00Z",
        "added": "2024-01-01T00:00:00Z",
        "checksum": "checksum",
        "archive_checksum": "archive",
    }
    first = Paperless.from_paperless(values, instance="home")
    second = Paperless.from_paperless(values, instance="home")
    assert first.sync_fingerprint == second.sync_fingerprint

    for field, value in (("modified", "2024-01-02T00:00:00Z"), ("checksum", "new"), ("archive_checksum", "new")):
        changed = dict(values, **{field: value})
        assert Paperless.from_paperless(changed, instance="home").sync_fingerprint != first.sync_fingerprint


def test_paperless_root_and_chunk_text_vectors():
    document = Paperless.from_paperless({
        "id": 1,
        "title": "Title",
        "content": "OCR",
        "modified": "2024-01-01T00:00:00Z",
        "added": "2024-01-01T00:00:00Z",
        "checksum": "checksum",
    }, instance="home")
    assert document.text_vector == "Title\nOCR"
    document.is_doc = False
    assert document.text_vector == "OCR"


@pytest.mark.asyncio
async def test_paperless_reconciliation_reads_only_indexed_root_fields():
    client = AsyncMock()
    client.scroll.return_value = (
        [Mock(payload={"id": "1", "paperless_id": 1, "sync_fingerprint": "fingerprint"})],
        None,
    )
    builder = PaperlessBuilder(document_type=Paperless, client=client, paperless=Mock())

    roots = await builder.indexed_roots()

    assert roots[0].id == "1"
    assert client.scroll.call_args.kwargs["with_payload"] == ["id", "paperless_id", "sync_fingerprint"]
