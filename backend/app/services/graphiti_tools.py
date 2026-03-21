# backend/app/services/graphiti_tools.py
"""
Search and retrieval tools for the MiroFish ReportAgent.
Replaces zep_tools.py.

Key changes from Zep version:
- graphiti.search_() returns SearchResults with .edges and .nodes
- No _local_search fallback — Graphiti is always local
- Temporal edges (valid_at/invalid_at/expired_at) handled natively
- uuid_ → uuid field rename throughout
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
class _SearchData:
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
    now = datetime.now(timezone.utc)
    if edge.expired_at and edge.expired_at < now:
        return True
    if edge.invalid_at and edge.invalid_at < now:
        return True
    return False


class GraphitiToolsService:

    def _search(self, graphiti, query: str, config, group_id: str):
        """Call graphiti.search_() or graphiti.search() depending on API version."""
        if hasattr(graphiti, 'search_'):
            return run_async(graphiti.search_(
                query=query,
                config=config,
                group_ids=[group_id],
            ))
        else:
            return run_async(graphiti.search(
                query=query,
                config=config,
                group_ids=[group_id],
            ))

    def quick_search(self, group_id: str, query: str, limit: int = 20) -> dict[str, Any]:
        """Fast search — edges + nodes via hybrid search with cross-encoder reranking."""
        graphiti = get_graphiti(group_id)
        results = self._search(graphiti, query, COMBINED_HYBRID_SEARCH_CROSS_ENCODER, group_id)

        active_edges, historical = [], []
        for e in results.edges[:limit]:
            if _is_expired(e):
                historical.append(e.fact or "")
            else:
                active_edges.append(_edge_to_dict(e))

        return _SearchData(
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
        """Deep dive on a specific entity."""
        graphiti = get_graphiti(group_id)

        edge_results = self._search(graphiti, f"{entity_name}: {query}", EDGE_HYBRID_SEARCH_RRF, group_id)
        node_results = self._search(graphiti, entity_name, NODE_HYBRID_SEARCH_RRF, group_id)

        active = [_edge_to_dict(e) for e in edge_results.edges[:limit] if not _is_expired(e)]
        return {
            "entity":  entity_name,
            "query":   query,
            "facts":   [e["fact"] for e in active],
            "edges":   active,
            "nodes":   [_node_to_dict(n) for n in node_results.nodes[:10]],
        }

    def panorama_search(self, group_id: str, query: str, limit: int = 30) -> dict[str, Any]:
        """Broad search including historical/expired edges for temporal analysis."""
        graphiti = get_graphiti(group_id)
        results = self._search(graphiti, query, COMBINED_HYBRID_SEARCH_CROSS_ENCODER, group_id)

        active, historical = [], []
        for e in results.edges[:limit]:
            if _is_expired(e):
                historical.append({"fact": e.fact, "expired_at": e.expired_at})
            else:
                active.append(_edge_to_dict(e))

        return {
            "query":            query,
            "current_facts":    [e["fact"] for e in active],
            "historical_facts": [h["fact"] for h in historical],
            "edges":            active,
            "nodes":            [_node_to_dict(n) for n in results.nodes],
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


# ---------------------------------------------------------------------------
# Result wrappers and ZepToolsService — previously in zep_tools.py shim
# ---------------------------------------------------------------------------

import json as _json
from typing import Optional as _Optional, List as _List


class _DictResult:
    """Wraps a dict result with a to_text() method expected by report_agent."""

    def __init__(self, data: dict):
        self._data = data

    def to_text(self) -> str:
        return _json.dumps(self._data, ensure_ascii=False, indent=2)

    def get(self, key, default=None):
        return self._data.get(key, default)


class InsightForgeResult(_DictResult):
    pass


class PanoramaResult(_DictResult):
    pass


class SearchResult(_DictResult):
    pass


class InterviewResult(_DictResult):
    pass


class ZepToolsService:
    """
    Tools service with the legacy Zep-compatible interface, backed by GraphitiToolsService.
    Previously in zep_tools.py — moved here when shim was removed.
    """

    def __init__(self, api_key: _Optional[str] = None):
        from .graphiti_entity_reader import ZepEntityReader as _ZepEntityReader
        self._tools = GraphitiToolsService()
        self._entity_reader = _ZepEntityReader()

    def insight_forge(
        self,
        graph_id: str,
        query: str,
        simulation_requirement: str = "",
        report_context: str = "",
        entity_name: str = "",
        limit: int = 15,
    ) -> InsightForgeResult:
        name = entity_name or " ".join(query.split()[:3])
        result = self._tools.insight_forge(group_id=graph_id, entity_name=name, query=query, limit=limit)
        return InsightForgeResult(result)

    def panorama_search(
        self,
        graph_id: str,
        query: str,
        include_expired: bool = True,
        limit: int = 30,
    ) -> PanoramaResult:
        result = self._tools.panorama_search(group_id=graph_id, query=query, limit=limit)
        return PanoramaResult(result)

    def quick_search(
        self,
        graph_id: str,
        query: str,
        limit: int = 20,
    ) -> SearchResult:
        result = self._tools.quick_search(group_id=graph_id, query=query, limit=limit)
        return SearchResult(result)

    def interview_agents(
        self,
        simulation_id: str,
        interview_requirement: str,
        simulation_requirement: str = "",
        max_agents: int = 5,
    ) -> InterviewResult:
        return InterviewResult({
            "note": "interview_agents is not supported in Graphiti mode",
            "simulation_id": simulation_id,
            "interview_requirement": interview_requirement,
            "answers": [],
        })

    def get_graph_statistics(self, graph_id: str) -> dict:
        stats = self._tools.get_graph_statistics(group_id=graph_id)
        return {
            "total_nodes":  stats.get("node_count", 0),
            "total_edges":  stats.get("edge_count", 0),
            "node_count":   stats.get("node_count", 0),
            "edge_count":   stats.get("edge_count", 0),
            "node_types":   stats.get("node_types", {}),
            "edge_types":   stats.get("edge_types", {}),
            "entity_types": stats.get("node_types", {}),
        }

    def get_entity_summary(self, graph_id: str, entity_name: str) -> dict:
        nodes = self._entity_reader.get_entities_by_type(graph_id=graph_id, entity_type=entity_name)
        if not nodes:
            filtered = self._entity_reader.filter_defined_entities(graph_id=graph_id)
            nodes = [e for e in filtered.entities if entity_name.lower() in e.name.lower()]
        if nodes:
            return nodes[0].to_dict()
        return {"name": entity_name, "found": False}

    def get_entities_by_type(self, graph_id: str, entity_type: str) -> list:
        return self._entity_reader.get_entities_by_type(graph_id=graph_id, entity_type=entity_type)

    def get_simulation_context(self, graph_id: str, simulation_requirement: str = "") -> dict:
        stats = self.get_graph_statistics(graph_id)
        try:
            search = self._tools.quick_search(
                group_id=graph_id,
                query=simulation_requirement or "simulation overview",
                limit=10,
            )
            related_facts = search.get("facts", []) if isinstance(search, dict) else []
        except Exception:
            related_facts = []
        return {
            "graph_statistics": {
                "total_nodes":  stats["total_nodes"],
                "total_edges":  stats["total_edges"],
                "entity_types": stats["entity_types"],
            },
            "total_entities": stats["total_nodes"],
            "related_facts":  related_facts,
        }
