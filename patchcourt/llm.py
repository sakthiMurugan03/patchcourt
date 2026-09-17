"""Swappable LLM client — works with OpenAI-compatible APIs, Claude, Gemini
(free-tier API key), a local Ollama server, or a deterministic mock."""

from __future__ import annotations

import json
import re
from typing import Any

from patchcourt.config import settings

_PROVIDERS = ("mock", "openai", "claude", "gemini", "ollama")


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
        resp = await self._real.ainvoke([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ])
        return self._extract_json(resp.content)

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