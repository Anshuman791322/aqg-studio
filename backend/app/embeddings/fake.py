"""Deterministic fake embedding provider for unit tests and local mock runs."""

import hashlib
import math

from app.embeddings.base import EmbeddingProvider


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic embedding provider generating normalized vectors from text hash."""

    def __init__(self, dimension: int = 384, provider_name: str = "fake_embeddings") -> None:
        self._dimension = dimension
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def _generate_vector(self, text: str) -> list[float]:
        """Generate deterministic unit vector of given dimension from text."""
        seed_bytes = hashlib.sha256(text.encode("utf-8")).digest()
        raw_values: list[float] = []

        for i in range(self._dimension):
            # Derive deterministic pseudo-random float from seed bytes
            byte_idx = i % len(seed_bytes)
            raw_val = (seed_bytes[byte_idx] + (i * 17)) % 100 - 50
            raw_values.append(float(raw_val))

        # Normalize to unit length
        norm = math.sqrt(sum(x * x for x in raw_values)) or 1.0
        return [round(x / norm, 6) for x in raw_values]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._generate_vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._generate_vector(text)
