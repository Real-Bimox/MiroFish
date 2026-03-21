# backend/app/services/fastembed_client.py
"""
Local CPU embedder using fastembed (ONNX BAAI/bge-small-en-v1.5).

Model is downloaded on first use (~90 MB) and cached under
~/.cache/fastembed/ (or wherever fastembed stores its cache).
"""

from typing import Iterable

from graphiti_core.embedder.client import EmbedderClient, EmbedderConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)

FASTEMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384  # bge-small produces 384-dim vectors


class FastEmbedConfig(EmbedderConfig):
    embedding_dim: int = EMBEDDING_DIM


class FastEmbedClient(EmbedderClient):
    """
    Wraps fastembed.TextEmbedding for use as a Graphiti EmbedderClient.

    BGE-small-en-v1.5: 384 dims, ~90 MB, CPU-only ONNX.
    """

    def __init__(self) -> None:
        from fastembed import TextEmbedding  # lazy import so missing package gives clear error
        logger.info(f"Loading fastembed model {FASTEMBED_MODEL}")
        self._model = TextEmbedding(model_name=FASTEMBED_MODEL)
        logger.info("fastembed model ready")

    async def create(
        self, input_data: str | list[str] | Iterable[int] | Iterable[Iterable[int]]
    ) -> list[float]:
        if isinstance(input_data, str):
            texts = [input_data]
        else:
            texts = list(input_data)  # type: ignore[arg-type]
        vectors = list(self._model.embed(texts))
        return vectors[0].tolist()

    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        vectors = list(self._model.embed(input_data_list))
        return [v.tolist() for v in vectors]
