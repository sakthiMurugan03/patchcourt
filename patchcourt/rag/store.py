"""RAG store — chunk, embed, and retrieve code context via Qdrant.

Embeddings are computed explicitly (sentence-transformers when available,
a deterministic hashing fallback otherwise). In-memory mode (``QdrantClient(":memory:")``)
is used when ``QDRANT_URL`` is empty, so everything runs without a server.
"""
from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from patchcourt.config import settings

_client: QdrantClient | None = None
_EMBEDDER: Any = None
COLLECTION = settings.qdrant_collection


class HashingEmbedder:
    """Deterministic fallback embedder — no downloads, runs offline."""

    dim = 64

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for doc in texts:
            vec = [0.0] * self.dim
            for token in re.findall(r"[a-zA-Z_]\w*", doc.lower())[:500]:
                h = int(hashlib.md5(token.encode()).hexdigest(), 16)
                vec[h % self.dim] += 1.0
            normsq = sum(v * v for v in vec) or 1.0
            vectors.append([v / normsq**0.5 for v in vec])
        return vectors


_sentence_transformers = None
try:  # sentence-transformers is the preferred embedder
    from sentence_transformers import SentenceTransformer

    class STEmbedder:
        model_name = "all-MiniLM-L6-v2"

        def __init__(self) -> None:
            self._model = SentenceTransformer(self.model_name)

        def encode(self, texts: list[str]) -> list[list[float]]:
            return self._model.encode(list(texts)).tolist()

    _sentence_transformers = STEmbedder
except Exception:  # pragma: no cover - depends on optional heavy install
    _sentence_transformers = None


def _get_embedder() -> Any:
    global _EMBEDDER
    if _EMBEDDER is None:
        try:
            _EMBEDDER = _sentence_transformers() if _sentence_transformers else HashingEmbedder()
        except Exception:
            _EMBEDDER = HashingEmbedder()
    return _EMBEDDER


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url, timeout=15) if settings.qdrant_url else QdrantClient(":memory:")
    return _client


def _collection() -> QdrantClient:
    """Ensure the collection exists (with the embedder's dimension) and return the client."""
    client = _get_client()
    if not client.collection_exists(COLLECTION):
        dim = len(_get_embedder().encode(["seed"])[0])
        client.create_collection(COLLECTION, vectors_config=VectorParams(size=dim, distance=Distance.COSINE))
    return client


def _chunk(text: str, size: int = 1500, overlap: int = 200) -> list[str]:
    chunks: list[str] = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + size])
        i += size - overlap
    return chunks


def index_pr(file_contents: dict[str, str]) -> None:
    """Index PR file patches into Qdrant."""
    client = _collection()
    texts: list[str] = []
    ids: list[str] = []
    metas: list[dict] = []
    for fname, content in file_contents.items():
        for idx, chunk in enumerate(_chunk(content)):
            stable = f"{fname}:{idx}"
            ids.append(str(uuid.uuid5(uuid.NAMESPACE_URL, stable)))
            texts.append(chunk)
            metas.append({"file": fname, "chunk_idx": idx})

    if not texts:
        return
    vectors = _get_embedder().encode(texts)
    points = [
        PointStruct(id=pid, vector=vec, payload={"document": doc, **meta})
        for pid, vec, doc, meta in zip(ids, vectors, texts, metas)
    ]
    client.delete(collection_name=COLLECTION, points_selector=ids, wait=False)
    client.upsert(collection_name=COLLECTION, points=points, wait=True)


def query(query_text: str, n_results: int = 8) -> list[dict[str, Any]]:
    """Retrieve relevant chunks for a query."""
    client = _collection()
    vec = _get_embedder().encode([query_text])[0]
    response = client.query_points(
        collection_name=COLLECTION,
        query=vec,
        limit=n_results,
        with_payload=True,
    )
    out: list[dict[str, Any]] = []
    for r in response.points:
        payload = r.payload or {}
        out.append(
            {
                "document": payload.get("document", ""),
                "metadata": {"file": payload.get("file", "?")},
                "distance": r.score,
            }
        )
    return out


def clear() -> None:
    global _client
    _client = None