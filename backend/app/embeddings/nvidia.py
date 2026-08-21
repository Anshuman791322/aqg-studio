"""NVIDIA NIM vector embedding provider implementation."""

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.embeddings.base import EmbeddingProvider

logger = get_logger("aqg.embeddings.nvidia")
settings = get_settings()


class NVIDIAEmbeddingProvider(EmbeddingProvider):
    """Client for NVIDIA NIM embedding models (e.g. nvidia/nv-embedqa-e5-v5)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str = "nvidia/nv-embedqa-e5-v5",
        dimension: int = 384,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key or settings.NVIDIA_API_KEY
        self.base_url = (base_url or settings.NVIDIA_BASE_URL).rstrip("/")
        self.model_name = model_name
        self._dimension = dimension
        self.client = client

    @property
    def provider_name(self) -> str:
        return "nvidia_embeddings"

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        if not self.api_key:
            raise RuntimeError("NVIDIA API key not configured for embeddings.")

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": texts,
            "model": self.model_name,
            "input_type": "passage",
        }

        if self.client is not None:
            resp = await self.client.post(url, json=payload, headers=headers, timeout=30.0)
        else:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=30.0)

        if resp.status_code != 200:
            raise RuntimeError(f"NVIDIA embeddings failed with status {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        embeddings_data = data.get("data", [])
        return [item["embedding"] for item in sorted(embeddings_data, key=lambda x: x.get("index", 0))]

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed_texts([text])
        return results[0] if results else [0.0] * self._dimension
