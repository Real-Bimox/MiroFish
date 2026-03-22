# backend/app/services/fastembed_client.py
"""
Ollama-backed embedder using the nomic-embed-text model.

Calls Ollama's OpenAI-compatible /v1/embeddings endpoint.
Returns 768-dimensional L2-normalised float vectors that are semantically
meaningful — enabling proper graph search via Graphiti.

Configuration (env vars, read via Config):
    OLLAMA_BASE_URL   — Ollama base URL, default http://host.containers.internal:11434/v1
    OLLAMA_EMBED_MODEL — model name, default nomic-embed-text

Fallback: if Ollama is unreachable, falls back to the SHA-256 hash stub so the
server doesn't crash, but logs a critical warning.
"""

import hashlib
import os

import numpy as np
import openai

from graphiti_core.embedder.client import EmbedderClient, EmbedderConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)

EMBEDDING_DIM = 768
_FALLBACK_DIM = 384


class FastEmbedConfig(EmbedderConfig):
    embedding_dim: int = EMBEDDING_DIM


class FastEmbedClient(EmbedderClient):
    """
    Ollama-backed semantic embedder (nomic-embed-text, 768-dim).
    Falls back to a deterministic hash stub if Ollama is unreachable.
    """

    def __init__(self) -> None:
        from app.config import Config
        base_url = Config.OLLAMA_BASE_URL
        model = Config.OLLAMA_EMBED_MODEL
        self._model = model
        self._client = openai.AsyncOpenAI(
            base_url=base_url,
            api_key="ollama",   # Ollama ignores the key; field is required by the client
        )
        logger.info(
            f"OllamaEmbedClient initialised: base_url={base_url}, model={model}"
        )

    async def create(self, input_data) -> list[float]:
        text = input_data if isinstance(input_data, str) else " ".join(str(t) for t in input_data)
        try:
            response = await self._client.embeddings.create(
                model=self._model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as exc:
            logger.error(f"Ollama embedding failed, using hash fallback: {exc}")
            return self._hash_fallback(text)

    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        try:
            response = await self._client.embeddings.create(
                model=self._model,
                input=input_data_list,
            )
            # Sort by index to preserve order
            items = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in items]
        except Exception as exc:
            logger.error(f"Ollama batch embedding failed, using hash fallback: {exc}")
            return [self._hash_fallback(t) for t in input_data_list]

    @staticmethod
    def _hash_fallback(text: str) -> list[float]:
        """Deterministic hash-based stub used only when Ollama is unreachable."""
        digest = hashlib.sha256(text.encode("utf-8", errors="replace")).digest()
        seed = int.from_bytes(digest[:8], "little")
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(_FALLBACK_DIM).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec.tolist()
