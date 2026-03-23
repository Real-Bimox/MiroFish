# Changelog — Real-Bimox/MiroFish fork

All notable changes to this fork of MiroFish are documented here.
Upstream source: [666ghj/MiroFish](https://github.com/666ghj/MiroFish)

Versions follow [Semantic Versioning](https://semver.org/) and match `backend/pyproject.toml`.

---

## v0.5.1 (2026-03-23)

### Changed
- **Ollama embedder** — `FastEmbedClient` completely rewritten to call Ollama's OpenAI-compatible `/v1/embeddings` endpoint using `nomic-embed-text` (768-dim semantic vectors) instead of a deterministic SHA-256 hash stub. Falls back to the hash stub only if Ollama is unreachable. Configured via `OLLAMA_BASE_URL` and `OLLAMA_EMBED_MODEL` env vars.
- **Dockerfile** — Added `ENV UV_SKIP_WHEEL_FILENAME_CHECK=1` as a persistent environment variable (not just a build-step flag) to suppress the `jupyterlab-pygments` wheel filename mismatch at both image build time and at runtime `uv run` invocations.

### Added
- **Config** — `OLLAMA_BASE_URL` (default `http://host.containers.internal:11434/v1`) and `OLLAMA_EMBED_MODEL` (default `nomic-embed-text`) added to `Config` class and read from environment variables.
- **Quadlet** — `OLLAMA_BASE_URL` and `OLLAMA_EMBED_MODEL` added to `mirofish.container` systemd quadlet.

### Integration
- **Generica v6.6.0** completes the Generica-side integration: simulation API routes, `/simulations` UI page, `DataSyncManager` bidirectional sync, and `ServiceIntegrationLayer` singleton are all live. See [Generica CHANGELOG](https://github.com/Real-Bimox/Generica/blob/master/CHANGELOG.md) and [docs/MIROFISH_INTEGRATION.md](https://github.com/Real-Bimox/Generica/blob/master/docs/MIROFISH_INTEGRATION.md).

**Generica ↔ MiroFish endpoint map:**
| MiroFish endpoint | Used by Generica |
|-------------------|-----------------|
| `GET /health` | Health monitoring (ServiceCoordinationManager) |
| `POST /api/graph/ontology/generate` | MiroFishService.generateOntology() |
| `POST /api/graph/build` | MiroFishService.buildGraph() |
| `GET /api/graph/project/list` | /api/mirofish/projects proxy |
| `POST /api/simulation/create` | Simulation step 1 |
| `POST /api/simulation/prepare` | Simulation step 2 |
| `POST /api/simulation/prepare/status` | Simulation step 2 polling |
| `POST /api/simulation/start` | Simulation step 3 |
| `GET /api/simulation/<id>` | Simulation step 4 polling |
| `POST /api/simulation/stop` | Simulation cancel |
| `POST /api/report/generate` | Simulation step 5 |
| `POST /api/report/generate/status` | Simulation step 5 polling |
| `GET /api/report/<id>` | Report retrieval |
| `GET /api/report/by-simulation/<id>` | Report retrieval fallback |
| `GET /api/simulation/list` | DataSyncManager periodic sync |

### Version
- `backend/pyproject.toml` bumped to `0.5.1`.

---

## v0.5.0 (2026-03-22)

### Removed
- **Zep compatibility shims** — `zep_entity_reader.py` and `zep_tools.py` deleted. All types and classes (`EntityNode`, `FilteredEntities`, `ZepEntityReader`, `ZepToolsService`, result wrappers) migrated into `graphiti_entity_reader.py` and `graphiti_tools.py` respectively. Consumer imports updated across `simulation_manager.py`, `simulation_config_generator.py`, `oasis_profile_generator.py`, and `services/__init__.py`.

### Added
- **API authentication** — Optional Bearer token middleware in `app/__init__.py`. When `MIROFISH_API_KEY` is set all `/api/*` requests must present `Authorization: Bearer <key>`. Leave empty (or omit) for open access. Configured via `MIROFISH_API_KEY` env var.

### Fixed
- **Report generation `NameError`** — `cleaned_content` was used before assignment in `report_agent.py:save_section`. Added the missing `cleaned_content = cls._clean_section_content(...)` call before the guard check.
- **Report agent import** — Updated `from .zep_tools import ...` to `from .graphiti_tools import ...` in `report_agent.py`.

### Version
- `backend/pyproject.toml` bumped to `0.5.0`.

---

## v0.3.0 (2026-03-21) — Graphiti Integration

### Changed
- **Full Graphiti + Neo4j knowledge graph** — Replaced Zep Cloud with self-hosted Graphiti backed by Neo4j. All graph operations (build, query, entity search) now use `GraphitiEntityReader` and `GraphitiToolsService`.
- **`fastembed_client.py`** — Introduced as Graphiti's `EmbedderClient` implementation (later upgraded to Ollama in v0.5.1).
- **LLM compatibility** — Fixed Graphiti constructor to pass `cross_encoder` flag for local thinking models; increased `max_tokens` to 8192 for ontology and report generation.

### Added
- `GraphitiEntityReader`, `GraphitiToolsService` wiring.
- `graphiti_client.py` singleton factory (`get_graphiti(group_id)`).

### Version
- `backend/pyproject.toml` bumped to `0.3.0`.

---

## v0.2.0 (upstream base — 2026-03-01)

Initial fork point from [666ghj/MiroFish](https://github.com/666ghj/MiroFish).

### Fork customisations at v0.2.0
- Replaced all hardcoded Chinese UI strings with English equivalents across all Vue components.
- Translated log messages, status indicators, and code comments to English.
- Removed upstream CI/CD and deployment references not applicable to this fork.
- Added Podman quadlet (`mirofish.container`) for rootless systemd-managed deployment.
- Configured for local LLM stack: llama.cpp-router (port 8082), Ollama (port 11434), Neo4j (port 7687).

---

*Format based on [Keep a Changelog](https://keepachangelog.com/)*
