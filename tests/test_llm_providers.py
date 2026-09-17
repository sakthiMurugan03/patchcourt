"""LLM provider dispatch — validate provider selection without network calls."""
import pytest

from patchcourt.config import settings
from patchcourt.llm import LLMClient, get_llm, reset_llm


def _restore(**kw):
    for k, v in kw.items():
        setattr(settings, k, v)
    reset_llm()


def test_default_is_mock():
    try:
        settings.use_mock_llm = False
        settings.llm_provider = "mock"
        settings.llm_api_key = ""
        reset_llm()
        client = get_llm()
        assert client._use_mock is True
    finally:
        _restore(use_mock_llm=False, llm_provider="mock", llm_api_key="")


def test_unknown_provider_rejected():
    try:
        settings.use_mock_llm = False
        settings.llm_provider = "grok"
        settings.llm_api_key = "x"
        with pytest.raises(ValueError, match="LLM_PROVIDER"):
            get_llm()
    finally:
        _restore(use_mock_llm=False, llm_provider="mock", llm_api_key="")


def test_real_provider_requires_key():
    try:
        settings.use_mock_llm = False
        settings.llm_provider = "openai"
        settings.llm_api_key = ""
        with pytest.raises(ValueError, match="requires LLM_API_KEY"):
            get_llm()
    finally:
        _restore(use_mock_llm=False, llm_provider="mock", llm_api_key="")


def test_openai_backend_selected():
    try:
        settings.use_mock_llm = False
        settings.llm_provider = "openai"
        settings.llm_api_key = "test-key-openai"
        reset_llm()
        client = get_llm()
        assert not client._use_mock
        assert client._provider == "openai"
    finally:
        _restore(use_mock_llm=False, llm_provider="mock", llm_api_key="")


def test_claude_backend_selected():
    try:
        settings.use_mock_llm = False
        settings.llm_provider = "claude"
        settings.llm_api_key = "test-key-claude"
        reset_llm()
        client = get_llm()
        assert client._provider == "claude"
        assert type(client._real).__name__ == "ChatAnthropic"
    finally:
        _restore(use_mock_llm=False, llm_provider="mock", llm_api_key="")


def test_gemini_backend_selected():
    try:
        settings.use_mock_llm = False
        settings.llm_provider = "gemini"
        settings.llm_api_key = "test-key-gemini"
        reset_llm()
        client = get_llm()
        assert client._provider == "gemini"
        assert type(client._real).__name__ == "ChatGoogleGenerativeAI"
    finally:
        _restore(use_mock_llm=False, llm_provider="mock", llm_api_key="")


def test_ollama_backend_selected():
    try:
        settings.use_mock_llm = False
        settings.llm_provider = "ollama"
        settings.llm_api_key = ""
        settings.llm_base_url = "http://localhost:11434/v1"
        reset_llm()
        client = get_llm()
        assert client._provider == "ollama"
        assert type(client._real).__name__ == "ChatOpenAI"
        assert "11434" in client._real.openai_api_base
    finally:
        _restore(use_mock_llm=False, llm_provider="mock", llm_api_key="", llm_base_url="https://api.openai.com/v1")


async def test_mock_still_deterministic():
    client = LLMClient()
    out = await client.generate("sys", "no findings here")
    assert out["claims"][0]["file"] == "example.py"