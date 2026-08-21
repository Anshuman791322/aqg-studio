"""Vector embedding providers module."""

from app.embeddings.base import EmbeddingProvider
from app.embeddings.factory import get_embedding_provider
from app.embeddings.fake import FakeEmbeddingProvider
from app.embeddings.fastembed import FastEmbedProvider
from app.embeddings.nvidia import NVIDIAEmbeddingProvider

__all__ = [
    "EmbeddingProvider",
    "FakeEmbeddingProvider",
    "FastEmbedProvider",
    "NVIDIAEmbeddingProvider",
    "get_embedding_provider",
]
