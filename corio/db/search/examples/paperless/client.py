"""Async client for the Paperless-ngx REST API."""
from __future__ import annotations

from typing import Any

from corio import https


class PaperlessClient:
    """Read document metadata and details from a Paperless-ngx instance."""

    def __init__(self, base_url: str, token: str, *, instance: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.instance = instance

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Token {self.token}"}

    async def _get(self, url: str) -> Any:
        async with https.AsyncClient(headers=self.headers) as client:
            response = await client.get(url)
        response.raise_for_status()
        return response.json()

    async def list_documents(self):
        """Return lightweight Paperless metadata without downloading OCR content."""
        from corio.db.search.examples.paperless.document import PaperlessIndex

        url = f"{self.base_url}/api/documents/?truncate_content=true"
        documents = []
        while url:
            page = await self._get(url)
            documents.extend(
                PaperlessIndex.from_paperless(data)
                for data in page["results"]
            )
            url = page["next"]
        return documents

    async def get_document(self, document_id: int):
        """Return a complete Paperless document for indexing."""
        from corio.db.search.examples.paperless.document import Paperless

        data = await self._get(f"{self.base_url}/api/documents/{document_id}/")
        return Paperless.from_paperless(data, instance=self.instance)
