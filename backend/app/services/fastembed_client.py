# backend/app/services/fastembed_client.py
"""
Deterministic hash-based embedder using only NumPy.

Produces a 384-dimensional L2-normalised float vector for any text string
by seeding NumPy's PCG64 generator from the SHA-256 of the text.  The
result is:
  - Deterministic: same text always produces the same vector
  - Consistent: vectors are stored and retrieved correctly from Neo4j
  - Not semantically meaningful: cosine similarity between vectors of
    related texts will be ~0; full-text / keyword search still works

IMPORTANT: This is a smoke-test / development embedder.
For production semantic search, replace with a real embedder, e.g.:
  - A local llama.cpp server started with --embeddings (+ a small BERT model)
  - fastembed (add via Dockerfile pip install, not uv — avoids torch bloat)
  - OpenAI text-embedding-3-small (if cloud API is acceptable)
"""

import hashlib

import numpy as np

from graphiti_core.embedder.client import EmbedderClient, EmbedderConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)

EMBEDDING_DIM = 384


class FastEmbedConfig(EmbedderConfig):
    embedding_dim: int = EMBEDDING_DIM


class FastEmbedClient(EmbedderClient):
    """
    Hash-based stub embedder.  Requires only NumPy (already installed).
    Swap this class for a real embedder before using semantic search.
    """

    def __init__(self) -> None:
        logger.warning(
            "Using hash-based stub embedder — semantic search will not work. "
            "Replace FastEmbedClient with a real embedding service for production."
        )

    def _embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8", errors="replace")).digest()
        seed = int.from_bytes(digest[:8], "little")
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec.tolist()

    async def create(self, input_data) -> list[float]:
        if isinstance(input_data, str):
            return self._embed(input_data)
        texts = list(input_data)
        return self._embed(" ".join(str(t) for t in texts))

    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in input_data_list]
