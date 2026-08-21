"""FastEmbed local ONNX embedding provider with lazy-loading and low-memory fallback."""

import asyncio
from typing import Any

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.embeddings.base import EmbeddingProvider

logger = get_logger("aqg.embeddings.fastembed")
settings = get_settings()


class FastEmbedProvider(EmbeddingProvider):
    """Local ONNX embeddings using fastembed (e.g. BAAI/bge-small-en-v1.5)."""

    def __init__(
        self,
        model_name: str | None = None,
        dimension: int = 384,
        app_settings: Settings = settings,
    ) -> None:
        self.model_name = model_name or app_settings.EMBEDDING_MODEL_NAME
        self._dimension = dimension
        self._model: Any = None
        self._is_available: bool = True

    @property
    def provider_name(self) -> str:
        return "fastembed"

    @property
    def dimension(self) -> int:
        return self._dimension

    def _get_model(self) -> Any:
        """Lazy load FastEmbed model on first invocation."""
        if self._model is None and self._is_available:
            try:
                from fastembed import TextEmbedding

                self._model = TextEmbedding(model_name=self.model_name)
                logger.info(f"Initialized FastEmbed model: {self.model_name}")
            except Exception as e:
                self._is_available = False
                logger.warning(
                    f"Failed to load FastEmbed model ({str(e)}). Lexical search will be used as fallback."
                )
                raise RuntimeError(f"FastEmbed initialization failed: {str(e)}") from e
        return self._model

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        def _sync_embed() -> list[list[float]]:
            model = self._get_model()
            embeddings_generator = model.embed(texts)
            return [e.tolist() for e in embeddings_generator]

        return await asyncio.to_thread(_sync_embed)

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed_texts([text])
        return results[0] if results else [0.0] * self._dimension
