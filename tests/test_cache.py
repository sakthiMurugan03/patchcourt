"""Tests for the Redis embedding cache helpers."""
from __future__ import annotations

from patchcourt.cache import redis_client
from patchcourt.cache.redis_client import (
    embedding_cache_key,
    get_cached_embedding,
    set_cached_embedding,
)


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, object] = {}
        self.last_ttl: int | None = None

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value, ex=None):
        self.store[key] = value
        self.last_ttl = ex
        return True


class BrokenRedis:
    def get(self, key):
        raise RuntimeError("boom")

    def set(self, key, value, ex=None):
        raise RuntimeError("boom")


def test_embedding_cache_key_is_sha256_deterministic():
    a = embedding_cache_key("def foo(): pass")
    b = embedding_cache_key("def foo(): pass")
    c = embedding_cache_key("def bar(): pass")
    assert a == b
    assert a != c
    assert a.startswith(redis_client.KEY_PREFIX)
    # sha256 hex digest is 64 chars
    assert len(a) == len(redis_client.KEY_PREFIX) + 64


def test_set_and_get_round_trip():
    client = FakeRedis()
    assert set_cached_embedding("hello world", [0.1, 0.2, 0.3], client=client) is True
    assert client.last_ttl == redis_client.DEFAULT_TTL_SECONDS
    assert get_cached_embedding("hello world", client=client) == [0.1, 0.2, 0.3]


def test_get_miss_returns_none():
    assert get_cached_embedding("never stored", client=FakeRedis()) is None


def test_get_handles_corrupt_json():
    client = FakeRedis()
    client.store[embedding_cache_key("x")] = "{not-json"
    assert get_cached_embedding("x", client=client) is None


def test_get_handles_unexpected_shape():
    client = FakeRedis()
    client.store[embedding_cache_key("y")] = '{"a": 1}'
    assert get_cached_embedding("y", client=client) is None


def test_get_decodes_bytes():
    client = FakeRedis()
    client.store[embedding_cache_key("z")] = b"[1.0, 2.0]"
    assert get_cached_embedding("z", client=client) == [1.0, 2.0]


def test_get_failure_is_swallowed():
    assert get_cached_embedding("x", client=BrokenRedis()) is None


def test_set_failure_is_swallowed():
    assert set_cached_embedding("x", [1.0], client=BrokenRedis()) is False


def test_set_empty_embedding_is_noop():
    client = FakeRedis()
    assert set_cached_embedding("x", [], client=client) is False
    assert client.store == {}


def test_no_client_configured_returns_none(monkeypatch):
    monkeypatch.setattr(redis_client, "_default_client_ready", True)
    monkeypatch.setattr(redis_client, "_default_client", None)
    assert get_cached_embedding("anything") is None
    assert set_cached_embedding("anything", [1.0]) is False


def test_cache_disabled_flag(monkeypatch):
    monkeypatch.setenv("PATCHCOURT_CACHE_DISABLED", "true")
    monkeypatch.setattr(redis_client.settings, "redis_url", "redis://localhost:6379/0")
    assert redis_client._build_client() is None
