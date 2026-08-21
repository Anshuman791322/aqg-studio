"""Application configuration module using Pydantic Settings."""

import json
from functools import lru_cache
from typing import Annotated, Any

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_cors_origins(v: Any) -> list[str]:
    """Parse CORS origins from JSON string, comma-separated string, or list."""
    if isinstance(v, list):
        return [str(item).strip() for item in v if str(item).strip()]
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return []
        if v.startswith("[") and v.endswith("]"):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass
        return [item.strip() for item in v.split(",") if item.strip()]
    return ["http://localhost:3000"]


CorsOriginsType = Annotated[list[str], BeforeValidator(_parse_cors_origins)]


class Settings(BaseSettings):
    """Application Settings class."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core Application Settings
    APP_NAME: str = "AQG Studio Backend"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    DEBUG: bool = Field(default=False)

    # CORS Settings
    BACKEND_CORS_ORIGINS: CorsOriginsType = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    # Database Settings (Optional in Phase 1 foundation)
    DATABASE_URL: str | None = Field(default=None)
    DIRECT_URL: str | None = Field(default=None)
    DB_ECHO_LOG: bool = Field(default=False)

    # Supabase Settings (Optional in Phase 1)
    NEXT_PUBLIC_SUPABASE_URL: str | None = Field(default=None)
    NEXT_PUBLIC_SUPABASE_ANON_KEY: str | None = Field(default=None)
    SUPABASE_SERVICE_ROLE_KEY: str | None = Field(default=None)
    SUPABASE_JWT_SECRET: str | None = Field(default=None)
    JWT_ALGORITHM: str = Field(default="HS256")

    # LLM Settings (Optional in Phase 1)
    OPENROUTER_API_KEY: str | None = Field(default=None)
    OPENROUTER_BASE_URL: str = Field(default="https://openrouter.ai/api/v1")
    OPENROUTER_PRIMARY_MODEL: str = Field(default="anthropic/claude-3.5-sonnet")

    NVIDIA_API_KEY: str | None = Field(default=None)
    NVIDIA_BASE_URL: str = Field(default="https://integrate.api.nvidia.com/v1")
    NVIDIA_FALLBACK_MODEL: str = Field(default="meta/llama-3.3-70b-instruct")

    # Embeddings & System Limits
    EMBEDDING_PROVIDER: str = Field(default="fastembed")
    EMBEDDING_MODEL_NAME: str = Field(default="BAAI/bge-small-en-v1.5")
    EMBEDDING_DIMENSION: int = Field(default=384)
    MAX_DOCUMENT_SIZE_MB: int = Field(default=50)
    MAX_QUESTIONS_PER_BATCH: int = Field(default=50)


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of Settings."""
    return Settings()
