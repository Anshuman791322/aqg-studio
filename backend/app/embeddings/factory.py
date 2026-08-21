"""Factory for initializing configured embedding provider."""

from app.core.config import Settings, get_settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.fake import FakeEmbeddingProvider
from app.embeddings.fastembed import FastEmbedProvider
from app.embeddings.nvidia import NVIDIAEmbeddingProvider


def get_embedding_provider(
    provider_name: str | None = None,
    app_settings: Settings | None = None,
) -> EmbeddingProvider:
    """Instantiate and return the requested or default EmbeddingProvider."""
    cfg = app_settings or get_settings()
    target_provider = (provider_name or cfg.EMBEDDING_PROVIDER).lower().strip()

    if target_provider == "fake":
        return FakeEmbeddingProvider(dimension=cfg.EMBEDDING_DIMENSION)
    elif target_provider == "nvidia" and cfg.NVIDIA_API_KEY:
        return NVIDIAEmbeddingProvider(
            api_key=cfg.NVIDIA_API_KEY,
            base_url=cfg.NVIDIA_BASE_URL,
            dimension=cfg.EMBEDDING_DIMENSION,
        )
    elif target_provider == "fastembed":
        return FastEmbedProvider(
            model_name=cfg.EMBEDDING_MODEL_NAME,
            dimension=cfg.EMBEDDING_DIMENSION,
        )

    # Fallback to FakeEmbeddingProvider if unknown or test environment
    return FakeEmbeddingProvider(dimension=cfg.EMBEDDING_DIMENSION)
