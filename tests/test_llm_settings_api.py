"""Test LLM settings API endpoints."""
import pytest
from fastapi.testclient import TestClient

from patchcourt.api.app import app
from patchcourt.runtime_llm_config import reset_runtime_config
from patchcourt.llm import reset_llm


client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime_config()
    reset_llm()
    yield
    reset_runtime_config()
    reset_llm()


def test_get_llm_settings_returns_defaults():
    """GET /api/settings/llm returns current effective settings."""
    resp = client.get("/api/settings/llm")
    assert resp.status_code == 200
    data = resp.json()
    assert "provider" in data
    assert "model" in data
    assert "has_api_key" in data
    assert "available_providers" in data
    assert set(data["available_providers"]) == {"mock", "gemini", "openai", "ollama"}
    # mock provider has has_api_key=True because it doesn't need a key (in NO_KEY_PROVIDERS)
    assert data["has_api_key"] is True


def test_post_llm_settings_updates_provider():
    """POST /api/settings/llm updates provider and re-initializes client."""
    # Update to gemini
    resp = client.post("/api/settings/llm", json={"provider": "gemini", "model": "gemini-flash", "api_key": "test-key"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "gemini"
    assert data["model"] == "gemini-flash"
    assert data["has_api_key"] is True
    assert "api_key" not in data  # never echoed back


def test_post_llm_settings_mock_requires_no_key():
    """POST /api/settings/llm with provider=mock needs no key."""
    resp = client.post("/api/settings/llm", json={"provider": "mock"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "mock"
    assert data["has_api_key"] is True  # mock = True by definition


def test_post_llm_settings_partial_update():
    """POST /api/settings/llm accepts partial updates."""
    # First set a provider
    client.post("/api/settings/llm", json={"provider": "openai", "model": "gpt-4o", "api_key": "key1"})
    # Then only update model
    resp = client.post("/api/settings/llm", json={"model": "gpt-3.5-turbo"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "openai"  # unchanged
    assert data["model"] == "gpt-3.5-turbo"  # updated


def test_test_llm_connection_mock_ok():
    """POST /api/settings/llm/test returns OK for mock provider."""
    # Ensure mock provider
    client.post("/api/settings/llm", json={"provider": "mock"})
    resp = client.post("/api/settings/llm/test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "Mock provider" in data["detail"]


def test_test_llm_connection_missing_key_fails():
    """POST /api/settings/llm/test fails when provider needs key but none set."""
    client.post("/api/settings/llm", json={"provider": "gemini", "api_key": ""})
    resp = client.post("/api/settings/llm/test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "No API key" in data["detail"]