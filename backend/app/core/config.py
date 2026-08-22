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

    # Database Settings
    DATABASE_URL: str | None = Field(default=None)
    DIRECT_URL: str | None = Field(default=None)
    DB_ECHO_LOG: bool = Field(default=False)

    # Supabase Settings
    NEXT_PUBLIC_SUPABASE_URL: str | None = Field(default=None)
    NEXT_PUBLIC_SUPABASE_ANON_KEY: str | None = Field(default=None)
    SUPABASE_SERVICE_ROLE_KEY: str | None = Field(default=None)
    SUPABASE_JWT_SECRET: str | None = Field(default=None)
    JWT_ALGORITHM: str = Field(default="HS256")
    SUPABASE_STORAGE_BUCKET_DOCUMENTS: str = Field(default="user-documents")
    SUPABASE_STORAGE_BUCKET_EXPORTS: str = Field(default="generated-exports")

    # LLM Settings & Provider Order
    LLM_PROVIDER_ORDER: str = Field(default="openrouter,nvidia")
    LLM_REQUEST_TIMEOUT_SECONDS: float = Field(default=60.0)
    LLM_MAX_RETRIES: int = Field(default=2)
    LLM_BACKOFF_BASE_SECONDS: float = Field(default=0.5)
    LLM_BACKOFF_MAX_SECONDS: float = Field(default=5.0)
    LLM_MAX_DAILY_REQUEST_BUDGET: int = Field(default=1000)

    OPENROUTER_API_KEY: str | None = Field(default=None)
    OPENROUTER_BASE_URL: str = Field(default="https://openrouter.ai/api/v1")
    OPENROUTER_PRIMARY_MODEL: str = Field(default="anthropic/claude-3.5-sonnet")
    OPENROUTER_MODEL: str = Field(default="openrouter/free")
    OPENROUTER_APP_TITLE: str = Field(default="AQG Studio")
    OPENROUTER_HTTP_REFERER: str = Field(default="https://aqg.studio")

    NVIDIA_API_KEY: str | None = Field(default=None)
    NVIDIA_BASE_URL: str = Field(default="https://integrate.api.nvidia.com/v1")
    NVIDIA_FALLBACK_MODEL: str = Field(default="meta/llama-3.3-70b-instruct")
    NVIDIA_MODEL: str = Field(default="meta/llama-3.3-70b-instruct")

    # Embeddings & System Limits
    EMBEDDING_PROVIDER: str = Field(default="fastembed")
    EMBEDDING_MODEL_NAME: str = Field(default="BAAI/bge-small-en-v1.5")
    EMBEDDING_DIMENSION: int = Field(default=384)
    MAX_DOCUMENT_SIZE_MB: int = Field(default=50)
    MAX_QUESTIONS_PER_BATCH: int = Field(default=50)

    # Question Generation Agent Settings
    GENERATION_BATCH_SIZE: int = Field(default=3)
    GENERATION_TEMPERATURE: float = Field(default=0.3)
    GENERATION_MAX_RETRIES: int = Field(default=2)
    GENERATION_RAG_TOP_K: int = Field(default=5)
    GENERATION_MAX_CHUNK_CHARS: int = Field(default=3000)

    # Evaluation & Refinement Agent Settings
    EVALUATION_ACCEPT_OVERALL_MIN: float = Field(default=0.85)
    EVALUATION_ACCEPT_CORRECTNESS_MIN: float = Field(default=0.90)
    EVALUATION_ACCEPT_GROUNDEDNESS_MIN: float = Field(default=0.90)
    EVALUATION_REFINE_OVERALL_MIN: float = Field(default=0.60)
    EVALUATION_REFINE_GROUNDEDNESS_MIN: float = Field(default=0.70)
    EVALUATION_MAX_REFINEMENT_ATTEMPTS: int = Field(default=2)
    EVALUATION_MAX_REGENERATION_ATTEMPTS: int = Field(default=2)
    EVALUATION_DUPLICATE_SIMILARITY_THRESHOLD: float = Field(default=0.90)
    EVALUATION_MAX_REPLACEMENT_BLUEPRINTS: int = Field(default=3)
    EVALUATION_BATCH_SIZE: int = Field(default=3)

    # Logging & Observability Settings
    LOG_FORMAT: str = Field(default="auto")  # 'auto', 'json', or 'text'

    # Production Rate Limiting & Quota Limits (Zero Redis Dependency)
    BURST_RATE_LIMIT_PER_MINUTE: int = Field(default=120)
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60)
    MAX_ASSESSMENTS_PER_DAY: int = Field(default=10)
    MAX_QUESTIONS_PER_ASSESSMENT: int = Field(default=50)
    MAX_LLM_CALLS_PER_ASSESSMENT: int = Field(default=30)
    MAX_DAILY_LLM_REQUESTS: int = Field(default=1000)




@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of Settings."""
    return Settings()
