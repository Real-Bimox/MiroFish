# backend/app/services/graphiti_client.py
"""
Graphiti client factory with per-group_id singleton cache.

Each MiroFish project maps to one Graphiti group_id. We cache one
Graphiti instance per group so Neo4j connection setup and index
validation only happen once per project lifetime.
"""

import inspect
import json
import re
import threading
import typing

from pydantic import BaseModel

from graphiti_core import Graphiti
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.llm_client.config import LLMConfig, ModelSize
from graphiti_core.prompts.models import Message
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
from app.services.fastembed_client import FastEmbedClient
from app.config import Config
from app.utils.async_loop import run_async
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LocalLLMClient(OpenAIGenericClient):
    """
    OpenAI-compatible client for local models (llama.cpp-router).

    Local models don't enforce json_schema response_format, so field names drift
    (e.g. `entity_name` instead of `name`). Fix: inject the schema as a compact
    one-line format example into the prompt, then use plain json_object mode.
    Schema injection happens once in generate_response (not in the retry loop).
    """

    async def generate_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
        max_tokens: int | None = None,
        model_size: ModelSize = ModelSize.medium,
        group_id: str | None = None,
        prompt_name: str | None = None,
    ) -> dict[str, typing.Any]:
        # Inject a human-readable field-names hint so the model uses exact key names.
        # We avoid raw JSON schema ($defs/properties) which models mistake for the
        # actual response.  Instead we describe the structure in plain language.
        if response_model is not None:
            hint = self._build_field_hint(response_model)
            messages[-1].content += f"\n\nIMPORTANT: {hint}"
        # Delegate to parent with response_model=None so _generate_response uses
        # json_object mode (not json_schema, which llama.cpp ignores).
        return await super().generate_response(
            messages,
            response_model=None,
            max_tokens=max_tokens,
            model_size=model_size,
            group_id=group_id,
            prompt_name=prompt_name,
        )

    async def _generate_response(
        self,
        messages,
        response_model=None,
        max_tokens=None,
        model_size=None,
    ) -> dict:
        """
        Override to strip markdown code fences that thinking models wrap around JSON.
        E.g. GLM/Qwen sometimes return ```json\\n{...}\\n``` instead of raw JSON.
        """
        import openai as _openai
        from graphiti_core.llm_client.config import DEFAULT_MAX_TOKENS, ModelSize as MS
        from graphiti_core.llm_client.errors import RateLimitError as _RLE
        from graphiti_core.prompts.models import Message as _Msg

        openai_messages = []
        for m in messages:
            m.content = self._clean_input(m.content)
            if m.role in ("user", "system"):
                openai_messages.append({"role": m.role, "content": m.content})

        _max = max_tokens or self.max_tokens or DEFAULT_MAX_TOKENS

        try:
            response = await self.client.chat.completions.create(
                model=self.model or "local",
                messages=openai_messages,  # type: ignore[arg-type]
                temperature=self.temperature,
                max_tokens=_max,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or ""
            # Strip markdown fences (```json ... ```) some models add
            raw = raw.strip()
            if raw.startswith("```"):
                raw = re.sub(r'^```(?:json)?\s*', '', raw)
                raw = re.sub(r'\s*```$', '', raw).strip()
            return json.loads(raw or "{}")
        except _openai.RateLimitError as e:
            raise _RLE from e
        except Exception as e:
            logger.error(f"LocalLLMClient._generate_response error: {e}")
            raise

    @staticmethod
    def _build_field_hint(model: type[BaseModel]) -> str:
        """
        Build a plain-English field-name hint for a Pydantic model.

        Recursively walks the model's fields.  For each field that is itself a
        Pydantic model (or a list of one), it lists that model's field names too.
        Output example:
          'Your response MUST be a JSON object whose top-level key(s) are exactly:
          "extracted_entities". Each "extracted_entities" item must have key(s):
          "name", "entity_type_id".'
        """
        import typing as _t
        lines = []
        top_keys = ", ".join(f'"{k}"' for k in model.model_fields)
        lines.append(
            f"Your response MUST be a JSON object whose top-level key(s) are "
            f"exactly: {top_keys}."
        )
        for field_name, field_info in model.model_fields.items():
            # Unwrap Optional / list to find nested BaseModel types
            ann = field_info.annotation
            origin = getattr(ann, "__origin__", None)
            args = getattr(ann, "__args__", ())
            # list[SomeModel] → SomeModel
            if origin is list and args:
                inner = args[0]
                if isinstance(inner, type) and issubclass(inner, BaseModel):
                    nested_keys = ", ".join(f'"{k}"' for k in inner.model_fields)
                    lines.append(
                        f'Each "{field_name}" item must have key(s): {nested_keys}.'
                    )
        return " ".join(lines)

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
    llm_client = LocalLLMClient(config=llm_config)
    embedder = FastEmbedClient()
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
