"""Optional Redis-backed caches for PatchCourt.

Import the embedding helpers directly::

    from patchcourt.cache.redis_client import get_cached_embedding, set_cached_embedding
"""
from patchcourt.cache.redis_client import (
    embedding_cache_key,
    get_cached_embedding,
    get_redis_client,
    set_cached_embedding,
)

__all__ = [
    "embedding_cache_key",
    "get_cached_embedding",
    "get_redis_client",
    "set_cached_embedding",
]
