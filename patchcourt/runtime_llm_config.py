"""Runtime LLM configuration store (in-memory, overrides env defaults)."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from patchcourt.config import settings as _env_settings


@dataclass
class RuntimeLLMConfig:
    """Mutable runtime LLM configuration."""
    provider: str = field(default_factory=lambda: _env_settings.llm_provider)
    model: str = field(default_factory=lambda: _env_settings.llm_model)
    api_key: str = field(default_factory=lambda: _env_settings.llm_api_key)
    base_url: str = field(default_factory=lambda: _env_settings.llm_base_url)
    use_mock_llm: bool = field(default_factory=lambda: _env_settings.use_mock_llm)

    # Providers that don't require an API key
    NO_KEY_PROVIDERS = {"mock", "ollama"}

    def has_key(self) -> bool:
        return bool(self.api_key) or self.provider in self.NO_KEY_PROVIDERS

    def to_dict(self, include_key: bool = False) -> dict[str, Any]:
        d = {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "use_mock_llm": self.use_mock_llm,
            "has_api_key": self.has_key(),
            "available_providers": ["mock", "gemini", "openai", "ollama"],
        }
        if include_key:
            d["api_key"] = self.api_key
        return d


# Thread-safe singleton
_RUNTIME_CONFIG: RuntimeLLMConfig | None = None
_CONFIG_LOCK = threading.Lock()


def get_runtime_config() -> RuntimeLLMConfig:
    """Get or create the runtime LLM config (thread-safe)."""
    global _RUNTIME_CONFIG
    if _RUNTIME_CONFIG is None:
        with _CONFIG_LOCK:
            if _RUNTIME_CONFIG is None:
                _RUNTIME_CONFIG = RuntimeLLMConfig()
    return _RUNTIME_CONFIG


def update_runtime_config(
    *,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    use_mock_llm: bool | None = None,
) -> RuntimeLLMConfig:
    """Update the runtime LLM config and return the new state."""
    cfg = get_runtime_config()
    with _CONFIG_LOCK:
        if provider is not None:
            cfg.provider = provider
        if model is not None:
            cfg.model = model
        if api_key is not None:
            cfg.api_key = api_key
        if base_url is not None:
            cfg.base_url = base_url
        if use_mock_llm is not None:
            cfg.use_mock_llm = use_mock_llm
            if use_mock_llm:
                cfg.provider = "mock"
        # Reset LLM client so next get_llm() picks up new config
        from patchcourt.llm import reset_llm
        reset_llm()
    return cfg


def get_effective_llm_settings() -> dict[str, Any]:
    """Get effective LLM settings (runtime overrides env)."""
    cfg = get_runtime_config()
    return cfg.to_dict()


def reset_runtime_config() -> None:
    """Reset the runtime config to env defaults (for testing)."""
    global _RUNTIME_CONFIG
    with _CONFIG_LOCK:
        _RUNTIME_CONFIG = None