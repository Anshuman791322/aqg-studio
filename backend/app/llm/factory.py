"""Factory function for initializing configured LLM provider instances and fallback gateway."""

from app.core.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.fake import FakeLLMProvider
from app.llm.fallback import FallbackLLMGateway
from app.llm.nvidia import NVIDIAProvider
from app.llm.openrouter import OpenRouterProvider

PROVIDER_REGISTRY: dict[str, type[LLMProvider]] = {
    "openrouter": OpenRouterProvider,
    "nvidia": NVIDIAProvider,
    "fake": FakeLLMProvider,
}


def create_llm_gateway(
    app_settings: Settings | None = None,
    override_providers: list[LLMProvider] | None = None,
) -> FallbackLLMGateway:
    """Build a FallbackLLMGateway from application settings and provider order."""
    if override_providers:
        return FallbackLLMGateway(providers=override_providers)

    cfg = app_settings or get_settings()

    # Parse configured provider order string (e.g. "openrouter,nvidia" or "fake")
    provider_order_str = getattr(cfg, "LLM_PROVIDER_ORDER", "openrouter,nvidia")
    provider_names = [p.strip().lower() for p in provider_order_str.split(",") if p.strip()]

    initialized_providers: list[LLMProvider] = []

    for name in provider_names:
        if name == "openrouter":
            initialized_providers.append(
                OpenRouterProvider(
                    api_key=cfg.OPENROUTER_API_KEY,
                    base_url=cfg.OPENROUTER_BASE_URL,
                    default_model=getattr(cfg, "OPENROUTER_MODEL", cfg.OPENROUTER_PRIMARY_MODEL),
                )
            )
        elif name == "nvidia":
            initialized_providers.append(
                NVIDIAProvider(
                    api_key=cfg.NVIDIA_API_KEY,
                    base_url=cfg.NVIDIA_BASE_URL,
                    default_model=getattr(cfg, "NVIDIA_MODEL", cfg.NVIDIA_FALLBACK_MODEL),
                )
            )
        elif name == "fake":
            initialized_providers.append(FakeLLMProvider())

    if not initialized_providers:
        # Fallback to fake provider if no valid providers could be configured
        initialized_providers.append(FakeLLMProvider())

    return FallbackLLMGateway(
        providers=initialized_providers,
        max_retries_per_provider=getattr(cfg, "LLM_MAX_RETRIES", 2),
        base_backoff_seconds=getattr(cfg, "LLM_BACKOFF_BASE_SECONDS", 0.5),
        max_backoff_seconds=getattr(cfg, "LLM_BACKOFF_MAX_SECONDS", 5.0),
        max_request_budget=getattr(cfg, "LLM_MAX_DAILY_REQUEST_BUDGET", 1000),
    )


# Singleton factory helper
def get_llm_gateway() -> FallbackLLMGateway:
    """Dependency injection helper returning active FallbackLLMGateway."""
    return create_llm_gateway()
