"""Redis-backed caching helpers.

Embedding generation is one of the most expensive steps in retrieval, so
vectors are memoised in Redis keyed by a SHA-256 digest of the source text.
The helpers are intentionally fault-tolerant: when Redis is not configured,
is unreachable, or returns corrupt data they behave as a cache miss / no-op.
A cache must never take down a review.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

from patchcourt.config import settings

logger = logging.getLogger("patchcourt.cache.redis")

KEY_PREFIX = "patchcourt:embedding:"
# Embeddings are deterministic for a given model + text, so a long TTL is safe.
DEFAULT_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days

# Cached default client so we don't reconnect on every lookup.
_default_client: Any | None = None
_default_client_ready = False


def embedding_cache_key(text: str) -> str:
    """Return a deterministic Redis key for ``text`` using a SHA-256 digest."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"{KEY_PREFIX}{digest}"


def _cache_disabled() -> bool:
    return os.getenv("PATCHCOURT_CACHE_DISABLED", "").lower() in ("1", "true", "yes")


def _build_client() -> Any | None:
    """Create a Redis client from ``settings.redis_url``.

    Returns ``None`` when caching is disabled or Redis is not configured.
    """
    if _cache_disabled() or not settings.redis_url:
        return None
    try:
        import redis  # imported lazily so the dependency stays optional

        return redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    except Exception:  # pragma: no cover - depends on environment
        logger.warning("Could not initialise Redis cache client", exc_info=True)
        return None


def get_redis_client() -> Any | None:
    """Return the shared Redis client (or ``None`` when unavailable)."""
    global _default_client, _default_client_ready
    if not _default_client_ready:
        _default_client = _build_client()
        _default_client_ready = True
    return _default_client


def _resolve_client(client: Any | None) -> Any | None:
    return client if client is not None else get_redis_client()


def get_cached_embedding(text: str, client: Any | None = None) -> list[float] | None:
    """Return the cached embedding for ``text`` or ``None`` on a miss.

    ``client`` may be supplied for testing/DI; otherwise the shared client is
    used.
    """
    store = _resolve_client(client)
    if store is None:
        return None

    key = embedding_cache_key(text)
    try:
        raw = store.get(key)
    except Exception:
        logger.warning("Redis GET failed for embedding cache", exc_info=True)
        return None

    if raw is None:
        return None

    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning("Corrupt embedding cache entry (undecodable bytes)")
            return None

    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        logger.warning("Corrupt embedding cache entry (invalid JSON)")
        return None

    if isinstance(value, list) and all(isinstance(v, (int, float)) for v in value):
        return [float(v) for v in value]
    logger.warning("Corrupt embedding cache entry (unexpected shape)")
    return None


def set_cached_embedding(
    text: str,
    embedding: list[float],
    ttl: int | None = DEFAULT_TTL_SECONDS,
    client: Any | None = None,
) -> bool:
    """Store ``embedding`` for ``text``. Returns ``True`` when it was written."""
    store = _resolve_client(client)
    if store is None:
        return False
    if not embedding:
        return False

    key = embedding_cache_key(text)
    try:
        payload = json.dumps([float(v) for v in embedding])
        store.set(key, payload, ex=ttl)
        return True
    except Exception:
        logger.warning("Redis SET failed for embedding cache", exc_info=True)
        return False
