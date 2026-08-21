"""Abstract base class for vector embedding providers."""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name identifier of the embedding provider."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimension (e.g. 384)."""
        pass

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate normalized vector embeddings for a list of texts."""
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Generate a single normalized vector embedding for a query string."""
        pass
