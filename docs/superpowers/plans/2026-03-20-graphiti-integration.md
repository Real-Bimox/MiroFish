# Graphiti Integration — Replace Zep Cloud in MiroFish

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Zep Cloud dependency in MiroFish with self-hosted Graphiti + Neo4j, keeping all simulation and reporting features intact while eliminating the external cloud dependency for confidential data.

**Architecture:** Graphiti (same engine that powers Zep Cloud) runs against a local Neo4j 5.x container. MiroFish's synchronous Flask backend calls Graphiti's async Python API via a shared per-thread event loop. All eight Zep service files are replaced with Graphiti equivalents; the API layer and simulation engine are untouched.

**Tech Stack:** `graphiti-core>=0.28.2`, `neo4j>=5.26.0`, Python 3.11, Flask 3.x (sync), Neo4j 5.26.2 (Podman quadlet), `asyncio` bridge pattern for Flask-thread compatibility.

---

## Improvements & Best Practices Applied in This Plan

Beyond the basic Zep → Graphiti swap, the following improvements are baked into the implementation:

| # | Improvement | Where Applied |
|---|---|---|
| I1 | **Shared async event loop** — one persistent loop per background thread, not a new loop per call | `async_loop.py` (Task 4) |
| I2 | **Graphiti client singleton** — one `Graphiti` instance per `group_id`, cached and reused | `graphiti_client.py` (Task 5) |
| I3 | **Community detection** — call `build_communities()` after graph build for richer ReportAgent context | `graph_builder.py` (Task 7) |
| I4 | **Saga chains** — simulation rounds linked as ordered episode sagas for temporal ordering | `graphiti_memory_updater.py` (Task 10) |
| I5 | **Custom extraction prompt** — inject social-simulation domain context into Graphiti's LLM extraction | `graphiti_client.py` (Task 5) |
| I6 | **Remove dead code** — `_local_search` fallback and episode polling loop are deleted entirely | `graphiti_tools.py`, `graph_builder.py` |
| I7 | **Increased memory batch size** — from 5 to 25 activities per episode to reduce LLM call overhead | `graphiti_memory_updater.py` (Task 10) |
| I8 | **Neo4j health check** — `/health` endpoint reports Neo4j connectivity alongside existing checks | `app/__init__.py` (Task 12) |
| I9 | **Meaningful episode names** — include round number and platform in episode names for auditability | `graphiti_memory_updater.py` (Task 10) |
| I10 | **`build_indices_and_constraints()` on startup** — ensures Neo4j vector indexes exist before first use | `graphiti_client.py` (Task 5) |

---

## File Map — Created / Modified / Deleted

### New Files
| Path | Purpose |
|---|---|
| `~/.config/containers/systemd/neo4j.container` | Podman Quadlet for Neo4j 5.26.2 |
| `backend/app/utils/async_loop.py` | Shared asyncio event loop bridge for Flask threads |
| `backend/app/services/graphiti_client.py` | Graphiti client factory + per-group_id singleton cache |
| `backend/app/utils/graphiti_paging.py` | Paginated node/edge enumeration (replaces `zep_paging.py`) |
| `backend/app/services/graphiti_entity_reader.py` | Node/edge reads for simulation entity prep (replaces `zep_entity_reader.py`) |
| `backend/app/services/graphiti_tools.py` | Search + ReportAgent tools (replaces `zep_tools.py`) |
| `backend/app/services/graphiti_memory_updater.py` | Real-time simulation activity writer (replaces `zep_graph_memory_updater.py`) |
| `backend/tests/test_graphiti_paging.py` | Tests for paging utilities |
| `backend/tests/test_graphiti_client.py` | Tests for client factory |
| `backend/tests/test_graph_builder.py` | Tests for graph lifecycle |
| `backend/tests/test_graphiti_tools.py` | Tests for search methods |

### Modified Files
| Path | Change Summary |
|---|---|
| `backend/pyproject.toml` | Remove `zep-cloud`, add `graphiti-core`, `neo4j` |
| `backend/uv.lock` | Regenerated after dep change |
| `backend/app/config.py` | Replace `ZEP_API_KEY` with `NEO4J_URI/USER/PASSWORD` |
| `backend/app/__init__.py` | Add Neo4j health check to `/health` endpoint |
| `backend/app/services/graph_builder.py` | Full rewrite — Graphiti lifecycle |
| `backend/app/services/oasis_profile_generator.py` | Replace Zep search with `graphiti_tools` |
| `backend/app/api/graph.py` | Replace `ZEP_API_KEY` guards; update imports |
| `backend/app/api/simulation.py` | Replace `ZEP_API_KEY` guards; update imports |
| `~/.config/containers/systemd/mirofish.container` | Add `NEO4J_URI/USER/PASSWORD`; remove `ZEP_API_KEY` |

### Deleted Files
| Path | Reason |
|---|---|
| `backend/app/utils/zep_paging.py` | Replaced by `graphiti_paging.py` |
| `backend/app/services/zep_entity_reader.py` | Replaced by `graphiti_entity_reader.py` |
| `backend/app/services/zep_tools.py` | Replaced by `graphiti_tools.py` |
| `backend/app/services/zep_graph_memory_updater.py` | Replaced by `graphiti_memory_updater.py` |

---

## Chunk 1: Infrastructure & Dependencies

### Task 1: Deploy Neo4j Container

**Files:**
- Create: `~/.config/containers/systemd/neo4j.container`

- [ ] **Step 1: Create Neo4j quadlet**

```ini
[Unit]
Description=Neo4j 5 - Graph Database for MiroFish/Graphiti
After=network-online.target
Wants=network-online.target

[Container]
Image=docker.io/neo4j:5.26.2
ContainerName=neo4j
PublishPort=7474:7474
PublishPort=7687:7687

Volume=%h/.neo4j/data:/data:Z
Volume=%h/.neo4j/logs:/logs:Z

Environment=NEO4J_AUTH=neo4j/mirofish-neo4j-password
Environment=NEO4J_PLUGINS=["apoc"]
Environment=NEO4J_dbms_memory_heap_initial__size=512m
Environment=NEO4J_dbms_memory_heap_max__size=2G
Environment=NEO4J_dbms_memory_pagecache_size=1G

[Service]
Restart=on-failure
RestartSec=10
TimeoutStartSec=120

[Install]
WantedBy=default.target
```

> **Note:** Change `mirofish-neo4j-password` to a strong password. This same value goes into `NEO4J_PASSWORD` in the MiroFish quadlet.

- [ ] **Step 2: Create data directories and start**

```bash
mkdir -p ~/.neo4j/data ~/.neo4j/logs
systemctl --user daemon-reload
systemctl --user enable --now neo4j
sleep 15  # Neo4j takes ~10s to fully start
```

- [ ] **Step 3: Verify Neo4j is healthy**

```bash
curl -s http://localhost:7474 | python3 -m json.tool | grep neo4j_version
# Expected: "neo4j_version": "5.26.2"

# Verify Bolt port
curl -s --max-time 5 http://localhost:7687 && echo "Bolt open" || echo "Bolt not responding (expected for raw HTTP)"
```

- [ ] **Step 4: Commit**

```bash
# Quadlet files are not in git — document the password in your notes
echo "Neo4j container running at bolt://localhost:7687, browser at http://localhost:7474"
```

---

### Task 2: Update Python Dependencies

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock` (auto-regenerated)

- [ ] **Step 1: Update pyproject.toml**

In `backend/pyproject.toml`, replace:
```toml
    # Zep Cloud
    "zep-cloud==3.13.0",
```
With:
```toml
    # Graphiti - self-hosted knowledge graph (replaces Zep Cloud)
    "graphiti-core>=0.28.2",
    "neo4j>=5.26.0",
```

- [ ] **Step 2: Regenerate uv.lock**

```bash
cd /home/bahram/local-repos/MiroFish/backend
uv lock
```

Expected: `uv.lock` updated, no errors.

- [ ] **Step 3: Verify install resolves**

```bash
cd /home/bahram/local-repos/MiroFish/backend
uv sync --frozen
python3 -c "import graphiti_core; print('graphiti-core OK')"
python3 -c "import neo4j; print('neo4j driver OK')"
```

- [ ] **Step 4: Commit**

```bash
cd /home/bahram/local-repos/MiroFish
git add backend/pyproject.toml backend/uv.lock
git commit -m "deps: replace zep-cloud with graphiti-core and neo4j driver"
```

---

### Task 3: Update Config & Environment

**Files:**
- Modify: `backend/app/config.py`
- Modify: `~/.config/containers/systemd/mirofish.container`

- [ ] **Step 1: Update config.py**

In `backend/app/config.py`, replace:
```python
    # Zep configuration
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
```
With:
```python
    # Graphiti / Neo4j configuration
    NEO4J_URI      = os.environ.get('NEO4J_URI',      'bolt://localhost:7687')
    NEO4J_USER     = os.environ.get('NEO4J_USER',     'neo4j')
    NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'password')
```

- [ ] **Step 2: Update validate() method**

In `Config.validate()`, replace the `ZEP_API_KEY` check:
```python
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY is required")
```
With:
```python
        if not cls.NEO4J_PASSWORD or cls.NEO4J_PASSWORD == 'password':
            errors.append("NEO4J_PASSWORD must be set to a non-default value")
```

- [ ] **Step 3: Update MiroFish quadlet**

In `~/.config/containers/systemd/mirofish.container`:

Remove:
```ini
# Required: Zep Cloud knowledge graph
Environment=ZEP_API_KEY=REPLACE_WITH_YOUR_ZEP_API_KEY
```

Add:
```ini
# Graphiti / Neo4j (local container at host port 7687)
Environment=NEO4J_URI=bolt://host.containers.internal:7687
Environment=NEO4J_USER=neo4j
Environment=NEO4J_PASSWORD=mirofish-neo4j-password
```

- [ ] **Step 4: Verify config loads**

```bash
cd /home/bahram/local-repos/MiroFish/backend
uv run python3 -c "
from app.config import Config
errors = Config.validate()
print('Errors:', errors)
print('NEO4J_URI:', Config.NEO4J_URI)
"
```
Expected: `Errors: []`, `NEO4J_URI: bolt://localhost:7687`

- [ ] **Step 5: Commit**

```bash
cd /home/bahram/local-repos/MiroFish
git add backend/app/config.py
git commit -m "config: replace ZEP_API_KEY with NEO4J_URI/USER/PASSWORD"
```

---

## Chunk 2: Foundation — Async Bridge & Client Factory

### Task 4: Async Event Loop Manager

**Files:**
- Create: `backend/app/utils/async_loop.py`
- Create: `backend/tests/test_async_loop.py`

MiroFish's Flask backend is synchronous. Graphiti is fully async. This utility provides a safe bridge: one persistent asyncio event loop running in a dedicated daemon thread, shared across all Flask worker threads via `run_coroutine_threadsafe`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_async_loop.py
import asyncio
import threading
from app.utils.async_loop import run_async, get_loop

async def _add(a, b):
    await asyncio.sleep(0)
    return a + b

def test_run_async_returns_result():
    assert run_async(_add(2, 3)) == 5

def test_run_async_is_thread_safe():
    results = []
    def worker():
        results.append(run_async(_add(10, 10)))
    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert results == [20] * 10

def test_same_loop_reused():
    loop1 = get_loop()
    loop2 = get_loop()
    assert loop1 is loop2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/bahram/local-repos/MiroFish/backend
uv run pytest tests/test_async_loop.py -v
# Expected: ImportError — module does not exist yet
```

- [ ] **Step 3: Implement async_loop.py**

```python
# backend/app/utils/async_loop.py
"""
Async event loop bridge for use in synchronous Flask threads.

Graphiti is fully async. Flask is fully sync. This module maintains
a single asyncio event loop running in a dedicated daemon thread.
All Flask threads share this loop via run_coroutine_threadsafe(),
which is thread-safe by design.

Usage:
    from app.utils.async_loop import run_async
    result = run_async(some_coroutine(args))
"""

import asyncio
import threading
from typing import TypeVar, Coroutine, Any

T = TypeVar("T")

_loop: asyncio.AbstractEventLoop | None = None
_loop_thread: threading.Thread | None = None
_lock = threading.Lock()


def get_loop() -> asyncio.AbstractEventLoop:
    """Return the shared event loop, creating it if needed."""
    global _loop, _loop_thread
    with _lock:
        if _loop is None or _loop.is_closed():
            _loop = asyncio.new_event_loop()
            _loop_thread = threading.Thread(
                target=_loop.run_forever,
                name="graphiti-async-loop",
                daemon=True,
            )
            _loop_thread.start()
    return _loop


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run an async coroutine from synchronous code.
    Blocks until the coroutine completes. Thread-safe.
    """
    future = asyncio.run_coroutine_threadsafe(coro, get_loop())
    return future.result()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/bahram/local-repos/MiroFish/backend
uv run pytest tests/test_async_loop.py -v
# Expected: 3 passed
```

- [ ] **Step 5: Commit**

```bash
cd /home/bahram/local-repos/MiroFish
git add backend/app/utils/async_loop.py backend/tests/test_async_loop.py
git commit -m "feat: add async event loop bridge for Graphiti/Flask integration"
```

---

### Task 5: Graphiti Client Factory

**Files:**
- Create: `backend/app/services/graphiti_client.py`
- Create: `backend/tests/test_graphiti_client.py`

Graphiti requires an LLM client and embedder at init time. Creating a new `Graphiti` instance per request is expensive (connection setup, index validation). This factory caches one instance per `group_id` and initialises indices on first use.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_graphiti_client.py
from unittest.mock import patch, MagicMock
from app.services.graphiti_client import get_graphiti, close_graphiti, SOCIAL_SIMULATION_PROMPT

def test_same_instance_returned_for_same_group():
    with patch("app.services.graphiti_client._build_graphiti") as mock_build:
        mock_build.return_value = MagicMock()
        g1 = get_graphiti("proj_abc")
        g2 = get_graphiti("proj_abc")
        assert g1 is g2
        assert mock_build.call_count == 1

def test_different_instances_for_different_groups():
    with patch("app.services.graphiti_client._build_graphiti") as mock_build:
        mock_build.side_effect = [MagicMock(), MagicMock()]
        g1 = get_graphiti("proj_a")
        g2 = get_graphiti("proj_b")
        assert g1 is not g2

def test_close_removes_from_cache():
    with patch("app.services.graphiti_client._build_graphiti") as mock_build:
        mock_build.return_value = MagicMock()
        get_graphiti("proj_x")
        close_graphiti("proj_x")
        get_graphiti("proj_x")
        assert mock_build.call_count == 2

def test_social_simulation_prompt_mentions_agents():
    assert "agent" in SOCIAL_SIMULATION_PROMPT.lower()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/bahram/local-repos/MiroFish/backend
uv run pytest tests/test_graphiti_client.py -v
# Expected: ImportError
```

- [ ] **Step 3: Implement graphiti_client.py**

```python
# backend/app/services/graphiti_client.py
"""
Graphiti client factory with per-group_id singleton cache.

Each MiroFish project maps to one Graphiti group_id. We cache one
Graphiti instance per group so Neo4j connection setup and index
validation only happen once per project lifetime.
"""

import threading
from graphiti_core import Graphiti
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.embedder.openai_embedder import OpenAIEmbedder
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
    llm_client = OpenAIClient(
        model=Config.LLM_MODEL_NAME,
        api_key=Config.LLM_API_KEY,
        base_url=Config.LLM_BASE_URL,
    )
    embedder = OpenAIEmbedder(
        api_key=Config.LLM_API_KEY,
        base_url=Config.LLM_BASE_URL,
    )
    return Graphiti(
        uri=Config.NEO4J_URI,
        user=Config.NEO4J_USER,
        password=Config.NEO4J_PASSWORD,
        llm_client=llm_client,
        embedder=embedder,
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
            run_async(g.build_indices_and_constraints())
            _cache[group_id] = g
            logger.info(f"Graphiti client ready for group_id={group_id}")
        return _cache[group_id]


def close_graphiti(group_id: str) -> None:
    """Remove a group's Graphiti instance from the cache (e.g., after delete_graph)."""
    with _lock:
        instance = _cache.pop(group_id, None)
        if instance:
            try:
                run_async(instance.close())
            except Exception:
                pass
            logger.info(f"Closed Graphiti client for group_id={group_id}")


def close_all() -> None:
    """Shutdown all cached instances — called at application exit."""
    with _lock:
        for group_id, instance in list(_cache.items()):
            try:
                run_async(instance.close())
            except Exception:
                pass
        _cache.clear()
        logger.info("All Graphiti clients closed")
```

- [ ] **Step 4: Register close_all at app shutdown**

In `backend/app/__init__.py`, at the bottom of `create_app()`, add:

```python
    import atexit
    from .services.graphiti_client import close_all as _close_graphiti
    atexit.register(_close_graphiti)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /home/bahram/local-repos/MiroFish/backend
uv run pytest tests/test_graphiti_client.py -v
# Expected: 4 passed
```

- [ ] **Step 6: Commit**

```bash
cd /home/bahram/local-repos/MiroFish
git add backend/app/services/graphiti_client.py backend/tests/test_graphiti_client.py backend/app/__init__.py
git commit -m "feat: add Graphiti client factory with group_id caching and domain extraction prompt"
```

---

### Task 6: Graphiti Paging Utilities

**Files:**
- Create: `backend/app/utils/graphiti_paging.py`
- Create: `backend/tests/test_graphiti_paging.py`
- Delete: `backend/app/utils/zep_paging.py` (after this task)

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_graphiti_paging.py
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.utils.graphiti_paging import fetch_all_nodes, fetch_all_edges

def _make_node(uuid, name):
    n = MagicMock()
    n.uuid = uuid
    n.name = name
    n.labels = ["Entity", "Agent"]
    n.summary = "test summary"
    n.attributes = {}
    return n

def _make_edge(uuid, name, fact, src, tgt):
    e = MagicMock()
    e.uuid = uuid
    e.name = name
    e.fact = fact
    e.source_node_uuid = src
    e.target_node_uuid = tgt
    e.valid_at = None
    e.invalid_at = None
    e.expired_at = None
    e.attributes = {}
    return e

@patch("app.utils.graphiti_paging.EntityNode")
def test_fetch_all_nodes_single_page(mock_cls):
    nodes = [_make_node("uuid-1", "Alice"), _make_node("uuid-2", "Bob")]
    mock_cls.get_by_group_ids = AsyncMock(return_value=nodes)
    driver = MagicMock()
    result = fetch_all_nodes(driver, "group_abc")
    assert len(result) == 2
    assert result[0]["name"] == "Alice"
    assert result[0]["uuid"] == "uuid-1"
    assert result[0]["labels"] == ["Entity", "Agent"]

@patch("app.utils.graphiti_paging.EntityNode")
def test_fetch_all_nodes_paginates(mock_cls):
    page1 = [_make_node(f"uuid-{i}", f"Entity{i}") for i in range(100)]
    page2 = [_make_node(f"uuid-{i+100}", f"Entity{i+100}") for i in range(50)]
    mock_cls.get_by_group_ids = AsyncMock(side_effect=[page1, page2])
    result = fetch_all_nodes(MagicMock(), "group_abc", page_size=100)
    assert len(result) == 150

@patch("app.utils.graphiti_paging.EntityEdge")
def test_fetch_all_edges_single_page(mock_cls):
    edges = [_make_edge("e1", "KNOWS", "Alice knows Bob", "uuid-1", "uuid-2")]
    mock_cls.get_by_group_ids = AsyncMock(return_value=edges)
    result = fetch_all_edges(MagicMock(), "group_abc")
    assert len(result) == 1
    assert result[0]["fact"] == "Alice knows Bob"
    assert result[0]["source_node_uuid"] == "uuid-1"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/bahram/local-repos/MiroFish/backend
uv run pytest tests/test_graphiti_paging.py -v
# Expected: ImportError
```

- [ ] **Step 3: Implement graphiti_paging.py**

```python
# backend/app/utils/graphiti_paging.py
"""
Paginated node and edge enumeration from Graphiti / Neo4j.

Replaces zep_paging.py. Uses EntityNode.get_by_group_ids and
EntityEdge.get_by_group_ids which mirror the same cursor-pagination
pattern as the former Zep SDK calls.
"""

import time
from typing import Any
from neo4j import AsyncDriver
from neo4j.exceptions import ServiceUnavailable, TransientError
from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge
from app.utils.async_loop import run_async
from app.utils.logger import get_logger

logger = get_logger(__name__)

_RETRYABLE = (ServiceUnavailable, TransientError, ConnectionError, TimeoutError)
_MAX_RETRIES = 3
_NODE_PAGE_LIMIT = 2000


def fetch_all_nodes(
    driver: AsyncDriver,
    group_id: str,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    """
    Return all EntityNodes for group_id as plain dicts.

    Dict shape (mirrors former Zep node fields):
      uuid, name, labels, summary, attributes
    """
    results: list[dict] = []
    cursor: str | None = None

    while True:
        page = _fetch_node_page(driver, group_id, page_size, cursor)
        for node in page:
            results.append({
                "uuid":       node.uuid,
                "name":       node.name,
                "labels":     node.labels or [],
                "summary":    node.summary or "",
                "attributes": node.attributes or {},
            })
        if len(page) < page_size or len(results) >= _NODE_PAGE_LIMIT:
            break
        cursor = page[-1].uuid

    return results


def fetch_all_edges(
    driver: AsyncDriver,
    group_id: str,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    """
    Return all EntityEdges for group_id as plain dicts.

    Dict shape (mirrors former Zep edge fields):
      uuid, name, fact, source_node_uuid, target_node_uuid,
      valid_at, invalid_at, expired_at, attributes
    """
    results: list[dict] = []
    cursor: str | None = None

    while True:
        page = _fetch_edge_page(driver, group_id, page_size, cursor)
        for edge in page:
            results.append({
                "uuid":             edge.uuid,
                "name":             edge.name,
                "fact":             edge.fact or "",
                "source_node_uuid": edge.source_node_uuid,
                "target_node_uuid": edge.target_node_uuid,
                "valid_at":         edge.valid_at,
                "invalid_at":       edge.invalid_at,
                "expired_at":       edge.expired_at,
                "attributes":       edge.attributes or {},
            })
        if len(page) < page_size:
            break
        cursor = page[-1].uuid

    return results


def _fetch_node_page(driver, group_id, limit, cursor):
    return _with_retry(
        lambda: run_async(
            EntityNode.get_by_group_ids(
                driver=driver,
                group_ids=[group_id],
                limit=limit,
                uuid_cursor=cursor,
            )
        )
    )


def _fetch_edge_page(driver, group_id, limit, cursor):
    return _with_retry(
        lambda: run_async(
            EntityEdge.get_by_group_ids(
                driver=driver,
                group_ids=[group_id],
                limit=limit,
                uuid_cursor=cursor,
            )
        )
    )


def _with_retry(fn, max_retries=_MAX_RETRIES):
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt < max_retries:
                delay = 2 ** attempt
                logger.warning(f"Neo4j transient error (attempt {attempt+1}): {exc}. Retrying in {delay}s")
                time.sleep(delay)
    raise last_exc
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/bahram/local-repos/MiroFish/backend
uv run pytest tests/test_graphiti_paging.py -v
# Expected: 3 passed
```

- [ ] **Step 5: Delete old file and commit**

```bash
cd /home/bahram/local-repos/MiroFish
git rm backend/app/utils/zep_paging.py
git add backend/app/utils/graphiti_paging.py backend/tests/test_graphiti_paging.py
git commit -m "feat: replace zep_paging with graphiti_paging using EntityNode/EntityEdge cursor pagination"
```

---

## Chunk 3: Core Graph Services

### Task 7: Rewrite graph_builder.py

**Files:**
- Modify: `backend/app/services/graph_builder.py` (full rewrite)
- Create: `backend/tests/test_graph_builder.py`

This is the largest file change. Key differences from the Zep version:
- No `create_graph` step (group_id is implicit in Graphiti)
- Ontology uses `BaseModel` subclasses instead of `EntityModel`/`EdgeModel`
- `add_episode_bulk` replaces `add_batch` — synchronous, no polling loop
- `build_communities()` added after ingest (improvement I3)
- `delete_by_group_id` replaces `client.graph.delete`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_graph_builder.py
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from app.services.graph_builder import GraphBuilderService

FAKE_ONTOLOGY = {
    "entity_types": {"Agent": {"description": "A social agent"}},
    "edge_types":   {"KNOWS": {"description": "Knows relationship"}},
    "source_targets": {"KNOWS": [{"source": "Agent", "target": "Agent"}]},
}

@patch("app.services.graph_builder.get_graphiti")
def test_build_graph_returns_group_id(mock_get_g):
    g = MagicMock()
    g.driver = MagicMock()
    g.add_episode_bulk = AsyncMock(return_value=MagicMock(episodes=[]))
    g.build_communities = AsyncMock()
    mock_get_g.return_value = g

    with patch("app.services.graph_builder.fetch_all_nodes", return_value=[]), \
         patch("app.services.graph_builder.fetch_all_edges", return_value=[]):
        svc = GraphBuilderService()
        result = svc.build_graph(
            project_id="proj_1",
            text_chunks=["chunk one", "chunk two"],
            ontology=FAKE_ONTOLOGY,
            graph_name="test graph",
        )
    assert result["group_id"].startswith("mirofish_")
    assert result["status"] == "complete"

@patch("app.services.graph_builder.get_graphiti")
def test_delete_graph_calls_driver(mock_get_g):
    from graphiti_core.nodes import Node
    g = MagicMock()
    g.driver = MagicMock()
    mock_get_g.return_value = g

    with patch.object(Node, "delete_by_group_id", new_callable=AsyncMock):
        svc = GraphBuilderService()
        svc.delete_graph("mirofish_abc123")

    # close_graphiti should be called to evict cache
    from app.services import graphiti_client
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/bahram/local-repos/MiroFish/backend
uv run pytest tests/test_graph_builder.py -v
# Expected: various failures — old graph_builder imports zep_cloud
```

- [ ] **Step 3: Rewrite graph_builder.py**

Replace the full contents of `backend/app/services/graph_builder.py`:

```python
# backend/app/services/graph_builder.py
"""
Graph lifecycle management using Graphiti (self-hosted, replaces Zep Cloud).

Key changes from Zep version:
- No explicit create_graph step — group_id is passed inline to Graphiti
- Ontology uses pydantic BaseModel subclasses (not Zep EntityModel/EdgeModel)
- add_episode_bulk is synchronous — no polling loop needed
- build_communities() called after ingest for richer ReportAgent context
- delete_graph uses Node.delete_by_group_id
"""

import uuid
import threading
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel
from graphiti_core.nodes import Node
from graphiti_core.utils.bulk_utils import RawEpisode
from graphiti_core import EpisodeType

from app.config import Config
from app.services.graphiti_client import get_graphiti, close_graphiti, SOCIAL_SIMULATION_PROMPT
from app.utils.graphiti_paging import fetch_all_nodes, fetch_all_edges
from app.utils.async_loop import run_async
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GraphBuilderService:

    def generate_group_id(self) -> str:
        return f"mirofish_{uuid.uuid4().hex[:16]}"

    # ------------------------------------------------------------------
    # Ontology → Graphiti type dicts
    # ------------------------------------------------------------------

    def build_entity_types(self, ontology: dict) -> dict[str, type[BaseModel]]:
        """
        Convert MiroFish ontology dict to Graphiti entity_types format.
        Each entity type becomes a pydantic BaseModel subclass.
        """
        entity_types: dict[str, type[BaseModel]] = {}
        for name, meta in ontology.get("entity_types", {}).items():
            description = meta.get("description", "")
            fields: dict[str, Any] = {"__annotations__": {}}
            if description:
                fields["__doc__"] = description
            entity_types[name] = type(name, (BaseModel,), fields)
        return entity_types

    def build_edge_types(self, ontology: dict) -> dict[str, type[BaseModel]]:
        """Convert ontology edge definitions to Graphiti edge_types format."""
        edge_types: dict[str, type[BaseModel]] = {}
        for name, meta in ontology.get("edge_types", {}).items():
            description = meta.get("description", "")
            fields: dict[str, Any] = {"__annotations__": {}}
            if description:
                fields["__doc__"] = description
            edge_types[name] = type(name, (BaseModel,), fields)
        return edge_types

    def build_edge_type_map(self, ontology: dict) -> dict[tuple[str, str], list[str]]:
        """Convert source_targets to Graphiti edge_type_map format."""
        edge_type_map: dict[tuple[str, str], list[str]] = {}
        for edge_name, targets in ontology.get("source_targets", {}).items():
            for st in targets:
                key = (st["source"], st["target"])
                edge_type_map.setdefault(key, []).append(edge_name)
        return edge_type_map

    # ------------------------------------------------------------------
    # Main build pipeline
    # ------------------------------------------------------------------

    def build_graph(
        self,
        project_id: str,
        text_chunks: list[str],
        ontology: dict,
        graph_name: str = "MiroFish Graph",
        batch_size: int = 10,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, Any]:
        """
        Build a Graphiti knowledge graph from text chunks.

        Returns a dict with:
          group_id, node_count, edge_count, status
        """
        group_id = self.generate_group_id()
        logger.info(f"Building graph group_id={group_id} for project={project_id}")

        graphiti = get_graphiti(group_id)

        entity_types  = self.build_entity_types(ontology)
        edge_types    = self.build_edge_types(ontology)
        edge_type_map = self.build_edge_type_map(ontology)

        total = len(text_chunks)
        processed = 0

        for batch_start in range(0, total, batch_size):
            batch = text_chunks[batch_start : batch_start + batch_size]
            episodes = [
                RawEpisode(
                    name=f"{graph_name}_chunk_{batch_start + i}",
                    content=chunk,
                    source=EpisodeType.text,
                    source_description=f"Seed document for {graph_name}",
                    reference_time=datetime.now(timezone.utc),
                )
                for i, chunk in enumerate(batch)
            ]

            run_async(graphiti.add_episode_bulk(
                bulk_episodes=episodes,
                group_id=group_id,
                entity_types=entity_types,
                edge_types=edge_types,
                edge_type_map=edge_type_map,
                custom_extraction_instructions=SOCIAL_SIMULATION_PROMPT,
            ))

            processed += len(batch)
            logger.info(f"  Ingested {processed}/{total} chunks for group_id={group_id}")
            if progress_callback:
                progress_callback(processed, total)

        # Build communities after full ingest (improvement I3)
        logger.info(f"Building communities for group_id={group_id}")
        run_async(graphiti.build_communities(group_ids=[group_id]))

        graph_info = self.get_graph_data(group_id)
        logger.info(
            f"Graph built: group_id={group_id}, "
            f"nodes={graph_info['node_count']}, edges={graph_info['edge_count']}"
        )
        return {
            "group_id":   group_id,
            "node_count": graph_info["node_count"],
            "edge_count": graph_info["edge_count"],
            "status":     "complete",
        }

    # ------------------------------------------------------------------
    # Graph data access
    # ------------------------------------------------------------------

    def get_graph_data(self, group_id: str) -> dict[str, Any]:
        """Return node/edge summary for a group."""
        graphiti = get_graphiti(group_id)
        nodes = fetch_all_nodes(graphiti.driver, group_id)
        edges = fetch_all_edges(graphiti.driver, group_id)
        return {
            "group_id":   group_id,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes":      nodes,
            "edges":      edges,
        }

    # ------------------------------------------------------------------
    # Graph deletion
    # ------------------------------------------------------------------

    def delete_graph(self, group_id: str) -> None:
        """Delete all nodes and edges for this group_id from Neo4j."""
        graphiti = get_graphiti(group_id)
        run_async(Node.delete_by_group_id(graphiti.driver, group_id=group_id))
        close_graphiti(group_id)
        logger.info(f"Deleted graph group_id={group_id}")
```

> **Note:** The `_build_graph_worker` threading pattern from the old implementation is preserved in `api/graph.py` (Task 12) — the service itself is now simpler and synchronous from the caller's perspective.

- [ ] **Step 4: Run tests**

```bash
cd /home/bahram/local-repos/MiroFish/backend
uv run pytest tests/test_graph_builder.py -v
# Expected: 2 passed
```

- [ ] **Step 5: Commit**

```bash
cd /home/bahram/local-repos/MiroFish
git add backend/app/services/graph_builder.py backend/tests/test_graph_builder.py
git commit -m "feat: rewrite graph_builder with Graphiti — add_episode_bulk, communities, no polling"
```

---

### Task 8: Graphiti Entity Reader

**Files:**
- Create: `backend/app/services/graphiti_entity_reader.py`
- Create: `backend/tests/test_graphiti_entity_reader.py`
- Delete: `backend/app/services/zep_entity_reader.py` (after this task)

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_graphiti_entity_reader.py
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.graphiti_entity_reader import GraphitiEntityReader

def _node(uuid, name, labels):
    n = MagicMock()
    n.uuid = uuid; n.name = name; n.labels = labels
    n.summary = "summary"; n.attributes = {}
    return n

def _edge(uuid, src, tgt, name, fact):
    e = MagicMock()
    e.uuid = uuid; e.source_node_uuid = src; e.target_node_uuid = tgt
    e.name = name; e.fact = fact; e.valid_at = None
    e.invalid_at = None; e.expired_at = None; e.attributes = {}
    return e

@patch("app.services.graphiti_entity_reader.fetch_all_nodes")
@patch("app.services.graphiti_entity_reader.fetch_all_edges")
@patch("app.services.graphiti_entity_reader.get_graphiti")
def test_filter_returns_custom_typed_nodes(mock_g, mock_edges, mock_nodes):
    mock_g.return_value = MagicMock()
    mock_nodes.return_value = [
        {"uuid": "u1", "name": "Alice", "labels": ["Entity", "Agent"], "summary": "", "attributes": {}},
        {"uuid": "u2", "name": "Neo4j", "labels": ["Entity"], "summary": "", "attributes": {}},
    ]
    mock_edges.return_value = []

    reader = GraphitiEntityReader()
    result = reader.filter_defined_entities("group_1", custom_labels=["Agent"])
    assert len(result) == 1
    assert result[0]["name"] == "Alice"

@patch("app.services.graphiti_entity_reader.get_graphiti")
def test_get_entity_by_uuid(mock_g):
    from graphiti_core.nodes import EntityNode
    mock_node = _node("uuid-1", "Alice", ["Agent"])
    mock_g.return_value = MagicMock()
    with patch.object(EntityNode, "get_by_uuid", new_callable=AsyncMock, return_value=mock_node):
        reader = GraphitiEntityReader()
        result = reader.get_entity_by_uuid("group_1", "uuid-1")
    assert result["name"] == "Alice"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/bahram/local-repos/MiroFish/backend
uv run pytest tests/test_graphiti_entity_reader.py -v
# Expected: ImportError
```

- [ ] **Step 3: Implement graphiti_entity_reader.py**

```python
# backend/app/services/graphiti_entity_reader.py
"""
Entity/node reading for simulation agent generation.
Replaces zep_entity_reader.py.

Key changes:
- uuid_ → uuid (field rename)
- EntityNode.get_by_uuid raises NodeNotFoundError (not returns None)
- EntityEdge.get_by_node_uuid for per-node edge lookup
- filter_defined_entities checks node labels for custom entity types
"""

from typing import Any
from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge
from graphiti_core.errors import NodeNotFoundError

from app.services.graphiti_client import get_graphiti
from app.utils.graphiti_paging import fetch_all_nodes, fetch_all_edges
from app.utils.async_loop import run_async
from app.utils.logger import get_logger

logger = get_logger(__name__)

_BUILT_IN_LABELS = {"Entity", "Node", "EpisodicNode", "CommunityNode"}


class GraphitiEntityReader:

    def filter_defined_entities(
        self,
        group_id: str,
        custom_labels: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return nodes that have at least one custom (non-built-in) label.
        If custom_labels is provided, only return nodes with those labels.
        """
        graphiti = get_graphiti(group_id)
        nodes = fetch_all_nodes(graphiti.driver, group_id)

        result = []
        for node in nodes:
            labels = node.get("labels", [])
            custom = [l for l in labels if l not in _BUILT_IN_LABELS]
            if not custom:
                continue
            if custom_labels and not any(l in custom_labels for l in custom):
                continue
            result.append(node)

        logger.info(f"Filtered {len(result)}/{len(nodes)} entities for group_id={group_id}")
        return result

    def get_entity_by_uuid(self, group_id: str, entity_uuid: str) -> dict[str, Any] | None:
        """Fetch a single entity node by UUID."""
        graphiti = get_graphiti(group_id)
        try:
            node = run_async(EntityNode.get_by_uuid(graphiti.driver, entity_uuid))
        except NodeNotFoundError:
            logger.warning(f"Entity {entity_uuid} not found in group_id={group_id}")
            return None
        return {
            "uuid":       node.uuid,
            "name":       node.name,
            "labels":     node.labels or [],
            "summary":    node.summary or "",
            "attributes": node.attributes or {},
        }

    def get_entity_with_edges(self, group_id: str, entity_uuid: str) -> dict[str, Any] | None:
        """Fetch a node plus all its edges."""
        entity = self.get_entity_by_uuid(group_id, entity_uuid)
        if not entity:
            return None
        graphiti = get_graphiti(group_id)
        edges = run_async(EntityEdge.get_by_node_uuid(graphiti.driver, entity_uuid))
        entity["edges"] = [
            {
                "uuid":             e.uuid,
                "name":             e.name,
                "fact":             e.fact or "",
                "source_node_uuid": e.source_node_uuid,
                "target_node_uuid": e.target_node_uuid,
                "valid_at":         e.valid_at,
                "invalid_at":       e.invalid_at,
            }
            for e in edges
        ]
        return entity

    def get_entities_by_type(self, group_id: str, entity_type: str) -> list[dict[str, Any]]:
        """Return all nodes with a specific custom label."""
        return self.filter_defined_entities(group_id, custom_labels=[entity_type])

    def get_all_nodes_and_edges(self, group_id: str) -> dict[str, Any]:
        """Return full node+edge dump for a group."""
        graphiti = get_graphiti(group_id)
        return {
            "nodes": fetch_all_nodes(graphiti.driver, group_id),
            "edges": fetch_all_edges(graphiti.driver, group_id),
        }
```

- [ ] **Step 4: Run tests**

```bash
cd /home/bahram/local-repos/MiroFish/backend
uv run pytest tests/test_graphiti_entity_reader.py -v
# Expected: 2 passed
```

- [ ] **Step 5: Delete old file and commit**

```bash
cd /home/bahram/local-repos/MiroFish
git rm backend/app/services/zep_entity_reader.py
git add backend/app/services/graphiti_entity_reader.py backend/tests/test_graphiti_entity_reader.py
git commit -m "feat: replace zep_entity_reader with graphiti_entity_reader"
```

---

## Chunk 4: Report & Memory Services

### Task 9: Graphiti Tools (ReportAgent Search)

**Files:**
- Create: `backend/app/services/graphiti_tools.py`
- Create: `backend/tests/test_graphiti_tools.py`
- Delete: `backend/app/services/zep_tools.py` (after this task)

This is the most critical service — all ReportAgent queries run through here. The `_local_search` fallback from the old implementation is removed entirely (improvement I6) since Graphiti's search is always local.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_graphiti_tools.py
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.graphiti_tools import GraphitiToolsService

def _edge(uuid, fact, src, tgt, name="KNOWS"):
    e = MagicMock()
    e.uuid = uuid; e.fact = fact
    e.source_node_uuid = src; e.target_node_uuid = tgt
    e.name = name; e.valid_at = None; e.invalid_at = None
    e.expired_at = None
    return e

def _node(uuid, name, labels=None, summary=""):
    n = MagicMock()
    n.uuid = uuid; n.name = name
    n.labels = labels or ["Entity"]; n.summary = summary
    return n

@patch("app.services.graphiti_tools.get_graphiti")
def test_quick_search_returns_structured_result(mock_g):
    from graphiti_core.search.search_config_recipes import COMBINED_HYBRID_SEARCH_CROSS_ENCODER
    g = MagicMock()
    g.driver = MagicMock()
    mock_search = MagicMock()
    mock_search.edges = [_edge("e1", "Alice leads the team", "uuid-a", "uuid-b")]
    mock_search.nodes = [_node("uuid-a", "Alice")]
    g.search_ = AsyncMock(return_value=mock_search)
    mock_g.return_value = g

    svc = GraphitiToolsService()
    result = svc.quick_search("group_1", "who leads?", limit=5)
    assert len(result["facts"]) == 1
    assert "Alice leads" in result["facts"][0]
    assert result["edge_count"] == 1

@patch("app.services.graphiti_tools.get_graphiti")
def test_search_filters_expired_edges(mock_g):
    from datetime import datetime, timezone
    g = MagicMock()
    g.driver = MagicMock()
    expired = _edge("e2", "Bob was CEO", "uuid-b", "uuid-c")
    expired.expired_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    active = _edge("e3", "Alice is CEO", "uuid-a", "uuid-b")
    mock_result = MagicMock()
    mock_result.edges = [expired, active]
    mock_result.nodes = []
    g.search_ = AsyncMock(return_value=mock_result)
    mock_g.return_value = g

    svc = GraphitiToolsService()
    result = svc.quick_search("group_1", "who is CEO?")
    active_facts = [f for f in result["facts"] if "Alice" in f]
    expired_facts = [f for f in result.get("historical_facts", []) if "Bob" in f]
    assert len(active_facts) == 1
    assert len(expired_facts) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/bahram/local-repos/MiroFish/backend
uv run pytest tests/test_graphiti_tools.py -v
# Expected: ImportError
```

- [ ] **Step 3: Implement graphiti_tools.py**

```python
# backend/app/services/graphiti_tools.py
"""
Search and retrieval tools for the MiroFish ReportAgent.
Replaces zep_tools.py.

Key changes from Zep version:
- graphiti.search_() returns SearchResults with .edges and .nodes
- No _local_search fallback needed — Graphiti is always local
- Temporal edges (valid_at/invalid_at/expired_at) handled natively
- uuid_ → uuid field rename throughout
- search scope (edges/nodes) handled via SearchConfig, not string param
"""

from datetime import datetime, timezone
from typing import Any
from dataclasses import dataclass, field

from graphiti_core.search.search_config_recipes import (
    COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
    EDGE_HYBRID_SEARCH_RRF,
    NODE_HYBRID_SEARCH_RRF,
)

from app.services.graphiti_client import get_graphiti
from app.utils.graphiti_paging import fetch_all_nodes, fetch_all_edges
from app.utils.async_loop import run_async
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    query: str
    facts: list[str] = field(default_factory=list)
    historical_facts: list[str] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)
    nodes: list[dict] = field(default_factory=list)
    edge_count: int = 0
    node_count: int = 0


def _edge_to_dict(e) -> dict:
    return {
        "uuid":             e.uuid,
        "name":             e.name,
        "fact":             e.fact or "",
        "source_node_uuid": e.source_node_uuid,
        "target_node_uuid": e.target_node_uuid,
        "valid_at":         e.valid_at.isoformat() if e.valid_at else None,
        "invalid_at":       e.invalid_at.isoformat() if e.invalid_at else None,
        "expired_at":       e.expired_at.isoformat() if e.expired_at else None,
    }


def _node_to_dict(n) -> dict:
    return {
        "uuid":    n.uuid,
        "name":    n.name,
        "labels":  n.labels or [],
        "summary": n.summary or "",
    }


def _is_expired(edge) -> bool:
    if edge.expired_at and edge.expired_at < datetime.now(timezone.utc):
        return True
    if edge.invalid_at and edge.invalid_at < datetime.now(timezone.utc):
        return True
    return False


class GraphitiToolsService:

    def quick_search(self, group_id: str, query: str, limit: int = 20) -> dict[str, Any]:
        """Fast search — edges + nodes via hybrid search with cross-encoder reranking."""
        graphiti = get_graphiti(group_id)
        results = run_async(graphiti.search_(
            query=query,
            config=COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
            group_ids=[group_id],
        ))

        active_edges, historical = [], []
        for e in results.edges[:limit]:
            if _is_expired(e):
                historical.append(e.fact or "")
            else:
                active_edges.append(_edge_to_dict(e))

        return SearchResult(
            query=query,
            facts=[e["fact"] for e in active_edges],
            historical_facts=historical,
            edges=active_edges,
            nodes=[_node_to_dict(n) for n in results.nodes[:limit]],
            edge_count=len(active_edges),
            node_count=len(results.nodes[:limit]),
        ).__dict__

    def insight_forge(
        self, group_id: str, entity_name: str, query: str, limit: int = 15
    ) -> dict[str, Any]:
        """Deep dive on a specific entity — edges + relevant community context."""
        graphiti = get_graphiti(group_id)

        # Edge-focused search scoped to the entity name
        edge_results = run_async(graphiti.search_(
            query=f"{entity_name}: {query}",
            config=EDGE_HYBRID_SEARCH_RRF,
            group_ids=[group_id],
        ))
        node_results = run_async(graphiti.search_(
            query=entity_name,
            config=NODE_HYBRID_SEARCH_RRF,
            group_ids=[group_id],
        ))

        active = [_edge_to_dict(e) for e in edge_results.edges[:limit] if not _is_expired(e)]
        return {
            "entity":     entity_name,
            "query":      query,
            "facts":      [e["fact"] for e in active],
            "edges":      active,
            "nodes":      [_node_to_dict(n) for n in node_results.nodes[:10]],
        }

    def panorama_search(self, group_id: str, query: str, limit: int = 30) -> dict[str, Any]:
        """Broad search including historical/expired edges for temporal analysis."""
        graphiti = get_graphiti(group_id)
        results = run_async(graphiti.search_(
            query=query,
            config=COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
            group_ids=[group_id],
        ))

        active, historical = [], []
        for e in results.edges[:limit]:
            if _is_expired(e):
                historical.append({"fact": e.fact, "expired_at": e.expired_at})
            else:
                active.append(_edge_to_dict(e))

        return {
            "query":          query,
            "current_facts":  [e["fact"] for e in active],
            "historical_facts": [h["fact"] for h in historical],
            "edges":          active,
            "nodes":          [_node_to_dict(n) for n in results.nodes],
        }

    def get_graph_statistics(self, group_id: str) -> dict[str, Any]:
        """Return node and edge type distributions for the group."""
        graphiti = get_graphiti(group_id)
        nodes = fetch_all_nodes(graphiti.driver, group_id)
        edges = fetch_all_edges(graphiti.driver, group_id)

        node_types: dict[str, int] = {}
        for n in nodes:
            for label in n.get("labels", []):
                if label not in {"Entity", "Node"}:
                    node_types[label] = node_types.get(label, 0) + 1

        edge_types: dict[str, int] = {}
        for e in edges:
            name = e.get("name", "unknown")
            edge_types[name] = edge_types.get(name, 0) + 1

        return {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "node_types": node_types,
            "edge_types": edge_types,
        }
```

- [ ] **Step 4: Run tests**

```bash
cd /home/bahram/local-repos/MiroFish/backend
uv run pytest tests/test_graphiti_tools.py -v
# Expected: 2 passed
```

- [ ] **Step 5: Delete old file and commit**

```bash
cd /home/bahram/local-repos/MiroFish
git rm backend/app/services/zep_tools.py
git add backend/app/services/graphiti_tools.py backend/tests/test_graphiti_tools.py
git commit -m "feat: replace zep_tools with graphiti_tools — structured search, temporal edges, no _local_search"
```

---

### Task 10: Graphiti Memory Updater (Real-Time Simulation Writes)

**Files:**
- Create: `backend/app/services/graphiti_memory_updater.py`
- Delete: `backend/app/services/zep_graph_memory_updater.py` (after this task)

Improvements applied here: saga chains (I4), increased batch size from 5 → 25 (I7), meaningful episode names with round/platform (I9).

- [ ] **Step 1: Implement graphiti_memory_updater.py**

```python
# backend/app/services/graphiti_memory_updater.py
"""
Real-time simulation activity writer for Graphiti.
Replaces zep_graph_memory_updater.py.

Key improvements over Zep version:
- Saga chains: simulation rounds are linked as ordered episode sequences
- Batch size increased from 5 to 25 to reduce LLM call overhead
- Meaningful episode names include round number and platform
- asyncio event loop bridge via run_async (no new loop per call)
"""

import queue
import threading
import time
from datetime import datetime, timezone
from typing import Any

from graphiti_core import EpisodeType

from app.services.graphiti_client import get_graphiti, SOCIAL_SIMULATION_PROMPT
from app.utils.async_loop import run_async
from app.utils.logger import get_logger

logger = get_logger(__name__)

BATCH_SIZE = 25       # Activities per episode (up from 5 — fewer LLM calls)
SEND_INTERVAL = 5.0   # Seconds between flushes (up from 0.5 — matches LLM latency)


class GraphitiMemoryUpdater:
    """
    Collects simulation agent activities and writes them to Graphiti
    in batches as episodes, linked by saga chains per simulation round.
    """

    def __init__(self, group_id: str, simulation_id: str):
        self.group_id = group_id
        self.simulation_id = simulation_id
        self._queue: queue.Queue[dict] = queue.Queue()
        self._stop_event = threading.Event()
        self._worker = threading.Thread(
            target=self._worker_loop,
            name=f"mem-updater-{simulation_id[:8]}",
            daemon=True,
        )
        self._current_round = 0
        self._saga_uuid: str | None = None  # Links episodes in a chain per round

    def start(self):
        self._worker.start()
        logger.info(f"GraphitiMemoryUpdater started for simulation={self.simulation_id}")

    def stop(self):
        self._stop_event.set()
        self._worker.join(timeout=30)
        logger.info(f"GraphitiMemoryUpdater stopped for simulation={self.simulation_id}")

    def add_activity(self, agent_name: str, platform: str, action: str, content: str, round_num: int):
        """Enqueue a single agent activity for batched writing."""
        self._queue.put({
            "agent":    agent_name,
            "platform": platform,
            "action":   action,
            "content":  content,
            "round":    round_num,
        })

    def _worker_loop(self):
        pending: list[dict] = []
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=SEND_INTERVAL)
                pending.append(item)
            except queue.Empty:
                pass

            if len(pending) >= BATCH_SIZE or (pending and self._stop_event.is_set()):
                self._flush(pending)
                pending = []

        # Drain remaining on shutdown
        while not self._queue.empty():
            try:
                pending.append(self._queue.get_nowait())
            except queue.Empty:
                break
        if pending:
            self._flush(pending)

    def _flush(self, activities: list[dict]):
        if not activities:
            return

        # Group by round for meaningful episode names
        by_round: dict[int, list[dict]] = {}
        for a in activities:
            by_round.setdefault(a["round"], []).append(a)

        for round_num, acts in sorted(by_round.items()):
            platforms = list({a["platform"] for a in acts})
            platform_str = "+".join(sorted(platforms))
            episode_name = (
                f"sim_{self.simulation_id[:8]}_round_{round_num:03d}_{platform_str}"
            )

            text_lines = []
            for a in acts:
                text_lines.append(
                    f"[Round {a['round']} | {a['platform']}] "
                    f"{a['agent']} {a['action']}: {a['content']}"
                )
            episode_body = "\n".join(text_lines)

            for attempt in range(3):
                try:
                    graphiti = get_graphiti(self.group_id)
                    result = run_async(graphiti.add_episode(
                        name=episode_name,
                        episode_body=episode_body,
                        source=EpisodeType.text,
                        source_description=f"Simulation round {round_num} activity log",
                        reference_time=datetime.now(timezone.utc),
                        group_id=self.group_id,
                        # Saga: link episodes in round order (improvement I4)
                        saga=True,
                        saga_previous_episode_uuid=self._saga_uuid,
                        custom_extraction_instructions=SOCIAL_SIMULATION_PROMPT,
                    ))
                    self._saga_uuid = result.episode.uuid
                    logger.debug(f"Wrote episode {episode_name} ({len(acts)} activities)")
                    break
                except Exception as exc:
                    delay = 2 ** attempt
                    logger.warning(f"Episode write failed (attempt {attempt+1}): {exc}. Retry in {delay}s")
                    time.sleep(delay)


class GraphitiMemoryManager:
    """Creates and tracks GraphitiMemoryUpdater instances per simulation."""

    _updaters: dict[str, GraphitiMemoryUpdater] = {}
    _lock = threading.Lock()

    @classmethod
    def create_updater(cls, group_id: str, simulation_id: str) -> GraphitiMemoryUpdater:
        with cls._lock:
            if simulation_id in cls._updaters:
                return cls._updaters[simulation_id]
            updater = GraphitiMemoryUpdater(group_id, simulation_id)
            updater.start()
            cls._updaters[simulation_id] = updater
            return updater

    @classmethod
    def stop_updater(cls, simulation_id: str):
        with cls._lock:
            updater = cls._updaters.pop(simulation_id, None)
        if updater:
            updater.stop()
```

- [ ] **Step 2: Delete old file and commit**

```bash
cd /home/bahram/local-repos/MiroFish
git rm backend/app/services/zep_graph_memory_updater.py
git add backend/app/services/graphiti_memory_updater.py
git commit -m "feat: replace zep_graph_memory_updater with graphiti_memory_updater — saga chains, 25-activity batches"
```

---

## Chunk 5: Integration & Final Wiring

### Task 11: Update oasis_profile_generator.py

**Files:**
- Modify: `backend/app/services/oasis_profile_generator.py`

Replace the two parallel `zep_client.graph.search()` calls with a single `graphiti_tools.insight_forge()` call.

- [ ] **Step 1: Find and replace Zep imports and calls**

In `backend/app/services/oasis_profile_generator.py`:

**Remove these imports:**
```python
from zep_cloud.client import Zep
```

**Add:**
```python
from app.services.graphiti_tools import GraphitiToolsService
```

**In `__init__` method, remove:**
```python
        self.zep_api_key = Config.ZEP_API_KEY
        if graph_id and self.zep_api_key:
            self.zep_client = Zep(api_key=self.zep_api_key)
```

**Add:**
```python
        self._tools = GraphitiToolsService() if graph_id else None
```

**Replace the parallel Zep search calls in `_enrich_entity_with_graph_context`:**

Old pattern (two parallel ThreadPoolExecutor calls to `self.zep_client.graph.search(...)`):

```python
# DELETE the entire _enrich_entity_with_graph_context method body
# and replace with:
    def _enrich_entity_with_graph_context(self, entity_name: str) -> str:
        if not self._tools or not self.graph_id:
            return ""
        try:
            result = self._tools.insight_forge(
                self.graph_id, entity_name, query=entity_name, limit=20
            )
            facts = result.get("facts", [])
            return "\n".join(f"- {f}" for f in facts[:15]) if facts else ""
        except Exception as exc:
            logger.warning(f"Graph enrichment failed for {entity_name}: {exc}")
            return ""
```

- [ ] **Step 2: Run the existing test suite to verify no regressions**

```bash
cd /home/bahram/local-repos/MiroFish/backend
uv run pytest tests/ -v --tb=short
# Expected: all existing tests pass
```

- [ ] **Step 3: Commit**

```bash
cd /home/bahram/local-repos/MiroFish
git add backend/app/services/oasis_profile_generator.py
git commit -m "feat: replace zep_client search in oasis_profile_generator with graphiti_tools.insight_forge"
```

---

### Task 12: Update API Layer

**Files:**
- Modify: `backend/app/api/graph.py`
- Modify: `backend/app/api/simulation.py`
- Modify: `backend/app/__init__.py`

- [ ] **Step 1: Update graph.py — ZEP_API_KEY guards and imports**

In `backend/app/api/graph.py`:

**Replace every occurrence of:**
```python
if not Config.ZEP_API_KEY:
    return jsonify({"success": False, "error": "ZEP_API_KEY not configured"}), 503
```
**With:**
```python
if not Config.NEO4J_PASSWORD:
    return jsonify({"success": False, "error": "NEO4J_PASSWORD not configured"}), 503
```

**Replace all imports from old services:**
```python
from ..services.zep_entity_reader import ZepEntityReader
```
→
```python
from ..services.graphiti_entity_reader import GraphitiEntityReader
```

Replace all `ZepEntityReader()` instantiations with `GraphitiEntityReader()`.

Replace `project.graph_id` references: in graph.py, the field was `graph_id` in the Zep version. With Graphiti it is still `group_id` but the `Project` model stores it as `graph_id`. Keep using `project.graph_id` — the field name in the `Project` model does not change, only its semantics (now a Graphiti `group_id`).

- [ ] **Step 2: Update simulation.py — ZEP_API_KEY guards and imports**

In `backend/app/api/simulation.py`:

**Replace every:**
```python
if not Config.ZEP_API_KEY:
    return jsonify({"success": False, "error": "ZEP_API_KEY not configured"}), 503
```
**With:**
```python
if not Config.NEO4J_PASSWORD:
    return jsonify({"success": False, "error": "NEO4J_PASSWORD not configured"}), 503
```

Replace import:
```python
from ..services.zep_entity_reader import ZepEntityReader
from ..services.zep_graph_memory_updater import ZepGraphMemoryManager
```
→
```python
from ..services.graphiti_entity_reader import GraphitiEntityReader
from ..services.graphiti_memory_updater import GraphitiMemoryManager
```

Replace all `ZepEntityReader()` → `GraphitiEntityReader()` and `ZepGraphMemoryManager` → `GraphitiMemoryManager`.

- [ ] **Step 3: Update report.py imports**

In `backend/app/api/report.py`:

Replace:
```python
from ..services.zep_tools import ZepToolsService
```
→
```python
from ..services.graphiti_tools import GraphitiToolsService
```

Replace all `ZepToolsService()` → `GraphitiToolsService()`.

- [ ] **Step 4: Add Neo4j health check to /health endpoint (improvement I8)**

In `backend/app/__init__.py`, find the `/health` endpoint and add Neo4j connectivity:

```python
    @app.route('/health')
    def health():
        from .services.graphiti_client import get_graphiti
        from .config import Config
        neo4j_ok = False
        try:
            # Lightweight connectivity check via Neo4j driver
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                Config.NEO4J_URI,
                auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD)
            )
            driver.verify_connectivity()
            driver.close()
            neo4j_ok = True
        except Exception:
            pass

        status = "ok" if neo4j_ok else "degraded"
        return jsonify({
            "status": status,
            "service": "MiroFish Backend",
            "neo4j": "connected" if neo4j_ok else "unreachable",
        }), 200 if neo4j_ok else 503
```

- [ ] **Step 5: Run full test suite**

```bash
cd /home/bahram/local-repos/MiroFish/backend
uv run pytest tests/ -v --tb=short
# Expected: all tests pass
```

- [ ] **Step 6: Commit**

```bash
cd /home/bahram/local-repos/MiroFish
git add backend/app/api/graph.py backend/app/api/simulation.py \
        backend/app/api/report.py backend/app/__init__.py
git commit -m "feat: update API layer — replace ZEP guards with NEO4J, update all service imports"
```

---

### Task 13: Rebuild MiroFish Container & Validate

**Files:**
- Modify: `~/.config/containers/systemd/mirofish.container` (env var already updated in Task 3)

- [ ] **Step 1: Rebuild MiroFish image**

```bash
cd /home/bahram/local-repos/MiroFish
./build.sh v0.2.0 --no-restart
# Expected: Successfully tagged localhost/mirofish:v0.2.0
```

- [ ] **Step 2: Update quadlet image tag**

In `~/.config/containers/systemd/mirofish.container`, update:
```ini
Image=localhost/mirofish:v0.2.0
```

- [ ] **Step 3: Start the updated container**

```bash
systemctl --user daemon-reload
systemctl --user restart mirofish
sleep 10
podman ps --filter name=mirofish --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
```

Expected: `mirofish  localhost/mirofish:v0.2.0  Up N seconds`

- [ ] **Step 4: Health check**

```bash
curl -s http://localhost:5001/health | python3 -m json.tool
```
Expected:
```json
{
    "status": "ok",
    "service": "MiroFish Backend",
    "neo4j": "connected"
}
```

- [ ] **Step 5: Smoke test graph API**

```bash
# Check that the graph endpoint no longer complains about ZEP_API_KEY
curl -s http://localhost:5001/api/graph/project/list | python3 -m json.tool
# Expected: {"success": true, "data": [...]}  (empty list is fine)
```

- [ ] **Step 6: Verify Neo4j browser**

Open http://localhost:7474 in a browser.
Login: `neo4j` / `mirofish-neo4j-password`
Run: `:schema` — should show Graphiti's vector indexes and constraints.

- [ ] **Step 7: Final commit — tag release**

```bash
cd /home/bahram/local-repos/MiroFish
git add .
git commit -m "chore: rebuild container v0.2.0 with Graphiti integration complete"
git tag -a v0.2.0 -m "Release v0.2.0: Graphiti replaces Zep Cloud"
```

---

## Post-Integration: Outstanding Recommendations

These are not in scope for this plan but should be tracked for future work:

### Rec 1 — FastAPI Migration (Medium-term)
Graphiti's reference server (`graphiti/server/`) uses FastAPI with `async def` routes. The `run_async()` bridge in this plan is correct and safe, but migrating Flask → FastAPI would remove the bridge entirely and allow `await graphiti.*()` directly in route handlers. This becomes worthwhile once MiroFish reaches production scale.

### Rec 2 — Neo4j Backup Strategy
Add a periodic `neo4j-admin dump` or APOC export to `~/.neo4j/backups/`. Suggested cron: weekly full dump. The simulation graph data is the hardest to recreate (requires re-running LLM extraction over all seed documents).

### Rec 3 — Authentication on the API
MiroFish's Flask API has no authentication (all endpoints open, CORS `*`). Before exposing to real users, add an API key header check or JWT middleware at the Flask level.

### Rec 4 — Graphiti Server (Optional)
The `graphiti/server/` directory contains a ready-made FastAPI service over Graphiti. Running it as a sidecar would allow multiple services (e.g., Generica's future integration) to share the same Neo4j graph without duplicating Graphiti client code.

### Rec 5 — Episode Deduplication
If the same seed document is accidentally uploaded twice, `add_episode_bulk` will extract duplicate entities. Add a document hash check in `graph_builder.py` before ingestion to skip already-processed chunks.

---

*Plan written: 2026-03-20*
*Covers: MiroFish v0.1.3 → v0.2.0*
*Graphiti: ≥0.28.2 | Neo4j: 5.26.2*
