"""Swappable LLM client — works with OpenAI-compatible APIs, Claude, Gemini
(free-tier API key), a local Ollama server, or a deterministic mock."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import time
from typing import Any

from patchcourt.runtime_llm_config import get_runtime_config

logger = logging.getLogger("patchcourt.llm")

_PROVIDERS = ("mock", "openai", "claude", "gemini", "ollama")


class LLMQuotaExhausted(Exception):
    """Provider rejected the request: quota exceeded / 429 / RESOURCE_EXHAUSTED."""


class LLMInvalidKey(Exception):
    """Provider rejected the API key (401 / unauthorized / permission denied)."""


class LLMServiceBusy(Exception):
    """Provider is temporarily overloaded (503)."""


class LLMUnreachable(Exception):
    """Provider could not be reached (timeout / DNS / network failure)."""


class _GeminiRateLimiter:
    """Simple token-bucket rate limiter for Gemini free tier (~4 req/min)."""

    def __init__(self, max_per_min: int = 4):
        self.max_per_min = max_per_min
        self._tokens = max_per_min
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(self.max_per_min, self._tokens + elapsed * (self.max_per_min / 60.0))
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                # Wait until next token is available
                wait_time = (1 - self._tokens) * (60.0 / self.max_per_min)
                await asyncio.sleep(wait_time)


_GEMINI_LIMITER = _GeminiRateLimiter()


class LLMClient:
    """Thin wrapper that returns structured JSON from an LLM or from a deterministic mock."""

    def __init__(self) -> None:
        cfg = get_runtime_config()
        provider = "mock" if cfg.use_mock_llm else (cfg.provider or "mock")
        if provider not in _PROVIDERS:
            raise ValueError(
                f"Unknown LLM_PROVIDER {provider!r} — choose one of {', '.join(_PROVIDERS)}"
            )
        self._provider = provider
        self._model = cfg.model
        if provider == "mock":
            self._use_mock = True
            self._real = None
            return
        self._use_mock = False
        self._real = self._build_real(provider, cfg)

    def _build_real(self, provider: str, cfg):
        if provider == "ollama":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=cfg.model or "llama3.1",
                api_key="ollama",
                base_url=cfg.base_url or "http://localhost:11434/v1",
                temperature=0,
            )
        key = (cfg.api_key or "").strip()
        if not key and provider not in {"mock", "ollama"}:
            raise ValueError(f"LLM_PROVIDER={provider} requires LLM_API_KEY (or use LLM_PROVIDER=mock)")
        if provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=cfg.model,
                api_key=key,
                base_url=cfg.base_url,
                temperature=0,
            )
        if provider == "claude":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(model=cfg.model or "claude-3-5-sonnet-latest", api_key=key, temperature=0)
        if provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=cfg.model or "gemini-2.5-flash", api_key=key, temperature=0
            )
        raise ValueError(f"Unsupported provider {provider}")

    # ------------------------------------------------------------------
    async def generate(self, system: str, user: str) -> dict[str, Any]:
        if self._use_mock:
            return self._mock_response(user)

        # Apply rate limiting for Gemini
        if self._provider == "gemini":
            await _GEMINI_LIMITER.acquire()

        return await self._generate_with_retry(system, user)

    async def _generate_with_retry(self, system: str, user: str, max_retries: int = 5) -> dict[str, Any]:
        """Generate with exponential backoff on transient 429s.

        Distinct failures (invalid key, overloaded, unreachable) are raised as
        typed, structured exceptions so the API can map them to precise
        user-facing messages. Raw error text is only logged server-side.
        """
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                resp = await self._real.ainvoke([
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ])
                content = self._normalize_content(resp.content)
                return self._extract_json(content)
            except Exception as e:
                cls = self._classify_error(e)
                if cls is LLMQuotaExhausted:
                    # 429 / rate limit may be transient — back off and retry.
                    last_error = e
                    retry_delay = self._extract_retry_delay(e)
                    if retry_delay is None:
                        base_delay = 2 ** attempt
                        retry_delay = base_delay + random.uniform(0, 1)

                    logger.warning(
                        "LLM quota/rate limited (attempt %d/%d), waiting %.1fs",
                        attempt + 1,
                        max_retries,
                        retry_delay,
                    )
                    await asyncio.sleep(retry_delay)
                    continue

                if cls is LLMInvalidKey:
                    logger.error("LLM provider rejected API key: %s", e)
                    raise LLMInvalidKey(str(e)) from e
                if cls is LLMServiceBusy:
                    logger.error("LLM provider overloaded: %s", e)
                    raise LLMServiceBusy(str(e)) from e
                if cls is LLMUnreachable:
                    logger.error("LLM provider unreachable: %s", e)
                    raise LLMUnreachable(str(e)) from e

                # Unknown / non-retryable — propagate the raw exception.
                raise

        raise LLMQuotaExhausted(
            f"LLM generate failed after {max_retries} retries: {last_error}"
        ) from last_error

    @staticmethod
    def _classify_error(err: Exception) -> type[Exception] | None:
        """Categorize a provider exception into a typed, structured error."""
        s = str(err).lower()
        if any(k in s for k in (
            "401", "unauthorized", "invalid api key", "invalid key",
            "apikey not valid", "403", "permission denied",
        )):
            return LLMInvalidKey
        if any(k in s for k in ("503", "service unavailable", "overloaded", "temporarily overloaded", "busy")):
            return LLMServiceBusy
        if any(k in s for k in ("429", "resource_exhausted", "quota exceeded", "quota")):
            return LLMQuotaExhausted
        if any(k in s for k in (
            "timeout", "timed out", "deadline exceeded", "connection",
            "connect", "network", "dns", "resolve", "getaddrinfo", "refused",
        )):
            return LLMUnreachable
        return None

    @staticmethod
    def _normalize_content(content: Any) -> str:
        """Normalize LLM response content to a plain string.

        langchain_google_genai may return content as a list of parts
        (e.g., [{'text': '...'}, ...]) instead of a plain string.
        """
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    parts.append(part["text"])
                else:
                    parts.append(str(part))
            return "".join(parts)
        return str(content)

    @staticmethod
    def _extract_retry_delay(e: Exception) -> float | None:
        """Extract retry delay from Google API error if present."""
        error_str = str(e)

        # Try to parse retry_delay from error message (Google API format)
        import re

        # Look for "retryDelay": "123s" or similar
        m = re.search(r'retryDelay["\s:]+(\d+)s', error_str)
        if m:
            return float(m.group(1))

        # Look for "retry_delay" in structured error
        m = re.search(r'"retry_delay"\s*:\s*(\d+)', error_str)
        if m:
            return float(m.group(1))

        return None

    # ------------------------------------------------------------------
    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group())
        m2 = re.search(r"\[.*\]", text, re.DOTALL)
        if m2:
            return {"claims": json.loads(m2.group())}
        return {"raw": text}

    # ------------------------------------------------------------------
    @staticmethod
    def _mock_response(user: str) -> dict[str, Any]:
        """Deterministic stub that returns plausible structured claims.

        If the prompt includes static-analysis findings, it emits a
        deliberately dismissive claim about the same file/line so the
        conflict detector and debate stage get exercised in offline demos.
        """
        finding = re.search(r"\] (.+?):(\d+) sev(\d) T(\d) — ", user)
        if finding and "STATIC-ANALYSIS FINDINGS" in user:
            return {
                "claims": [
                    {
                        "issue": f"Disputed: tool finding on {finding.group(1)}:{finding.group(2)} is likely a false positive",
                        "file": finding.group(1),
                        "line": int(finding.group(2)),
                        "severity": 1,
                        "evidence": [{"tier": 5, "text": "mock LLM assertion — not tool corroborated"}],
                        "confidence": 0.4,
                        "tier": 5,
                    }
                ]
            }
        return {
            "claims": [
                {
                    "issue": "Mock: please configure a real LLM key for actual review",
                    "file": "example.py",
                    "line": 1,
                    "severity": 2,
                    "evidence": [{"tier": 5, "text": "mock evidence — no real analysis"}],
                    "confidence": 0.3,
                }
            ]
        }


_client: LLMClient | None = None


def get_llm() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def reset_llm() -> None:
    """Drop the cached client so the next get_llm() reflects config changes."""
    global _client
    _client = None