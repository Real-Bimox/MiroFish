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
