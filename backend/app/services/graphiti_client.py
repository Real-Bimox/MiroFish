# backend/app/services/graphiti_client.py
"""
Graphiti client factory with per-group_id singleton cache.

Each MiroFish project maps to one Graphiti group_id. We cache one
Graphiti instance per group so Neo4j connection setup and index
validation only happen once per project lifetime.
"""

import inspect
import threading
from graphiti_core import Graphiti
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
from app.config import Config
from app.utils.async_loop import run_async
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Domain-specific extraction prompt injected into Graphiti's LLM pipeline
# Guides entity/relation extraction toward social simulation concepts
SOCIAL_SIMULATION_PROMPT = """
This knowledge graph models a social simulation environment.
Focus on extracting: agents (people, organisations, personas),
social relationships (follows, influences, opposes, collaborates),
events (posts, reactions, conflicts, endorsements), and
ideological positions (beliefs, stances, affiliations).
Preserve temporal context — note when relationships form or dissolve.
""".strip()

_cache: dict[str, Graphiti] = {}
_lock = threading.Lock()


def _build_graphiti() -> Graphiti:
    """Create a new Graphiti instance connected to the configured Neo4j."""
    llm_config = LLMConfig(
        api_key=Config.LLM_API_KEY,
        model=Config.LLM_MODEL_NAME,
        base_url=Config.LLM_BASE_URL,
    )
    llm_client = OpenAIClient(config=llm_config)
    embedder_config = OpenAIEmbedderConfig(
        api_key=Config.LLM_API_KEY,
        base_url=Config.LLM_BASE_URL,
    )
    embedder = OpenAIEmbedder(config=embedder_config)
    cross_encoder = OpenAIRerankerClient(config=llm_config)
    return Graphiti(
        uri=Config.NEO4J_URI,
        user=Config.NEO4J_USER,
        password=Config.NEO4J_PASSWORD,
        llm_client=llm_client,
        embedder=embedder,
        cross_encoder=cross_encoder,
    )


def get_graphiti(group_id: str) -> Graphiti:
    """
    Return the cached Graphiti instance for this group_id.
    Creates and initialises (indices + constraints) on first call.
    Thread-safe.
    """
    with _lock:
        if group_id not in _cache:
            logger.info(f"Creating Graphiti client for group_id={group_id}")
            g = _build_graphiti()
            coro = g.build_indices_and_constraints()
            if inspect.iscoroutine(coro):
                run_async(coro)
            _cache[group_id] = g
            logger.info(f"Graphiti client ready for group_id={group_id}")
        return _cache[group_id]


def close_graphiti(group_id: str) -> None:
    """Remove a group's Graphiti instance from the cache (e.g., after delete_graph)."""
    with _lock:
        instance = _cache.pop(group_id, None)
        if instance:
            try:
                coro = instance.close()
                if inspect.iscoroutine(coro):
                    run_async(coro)
            except Exception:
                pass
            logger.info(f"Closed Graphiti client for group_id={group_id}")


def close_all() -> None:
    """Shutdown all cached instances — called at application exit."""
    with _lock:
        for group_id, instance in list(_cache.items()):
            try:
                coro = instance.close()
                if inspect.iscoroutine(coro):
                    run_async(coro)
            except Exception:
                pass
        _cache.clear()
        logger.info("All Graphiti clients closed")
