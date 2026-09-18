"""Swappable LLM client — works with OpenAI-compatible APIs, Claude, Gemini
(free-tier API key), a local Ollama server, or a deterministic mock."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
from typing import Any

from patchcourt.config import settings

logger = logging.getLogger("patchcourt.llm")

_PROVIDERS = ("mock", "openai", "claude", "gemini", "ollama")


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
        provider = "mock" if settings.use_mock_llm else (settings.llm_provider or "mock")
        if provider not in _PROVIDERS:
            raise ValueError(
                f"Unknown LLM_PROVIDER {provider!r} — choose one of {', '.join(_PROVIDERS)}"
            )
        self._provider = provider
        self._model = settings.llm_model
        if provider == "mock":
            self._use_mock = True
            self._real = None
            return
        self._use_mock = False
        self._real = self._build_real(provider)

    def _build_real(self, provider: str):
        if provider == "ollama":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=settings.llm_model or "llama3.1",
                api_key="ollama",
                base_url=settings.llm_base_url or "http://localhost:11434/v1",
                temperature=0,
            )
        key = (settings.llm_api_key or "").strip()
        if not key:
            raise ValueError(f"LLM_PROVIDER={provider} requires LLM_API_KEY (or use LLM_PROVIDER=mock)")
        if provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=settings.llm_model,
                api_key=key,
                base_url=settings.llm_base_url,
                temperature=0,
            )
        if provider == "claude":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(model=settings.llm_model or "claude-3-5-sonnet-latest", api_key=key, temperature=0)
        if provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=settings.llm_model or "gemini-2.5-flash", api_key=key, temperature=0
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
        """Generate with exponential backoff on 429."""
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                resp = await self._real.ainvoke([
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ])
                return self._extract_json(resp.content)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Check for 429 / rate limit
                if "429" in error_str or "resource_exhausted" in error_str or "rate limit" in error_str:
                    # Try to extract retry delay from error
                    retry_delay = self._extract_retry_delay(e)
                    if retry_delay is None:
                        # Exponential backoff with jitter: 2^attempt * base + jitter
                        base_delay = 2 ** attempt
                        retry_delay = base_delay + random.uniform(0, 1)

                    logger.warning(
                        "Gemini rate limited (attempt %d/%d), waiting %.1fs",
                        attempt + 1,
                        max_retries,
                        retry_delay,
                    )
                    await asyncio.sleep(retry_delay)
                    continue

                # Non-retryable error
                raise

        raise RuntimeError(f"LLM generate failed after {max_retries} retries: {last_error}") from last_error

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