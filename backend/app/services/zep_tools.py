# backend/app/services/zep_tools.py
"""
Compatibility shim: maps old Zep tools API onto GraphitiToolsService.

report_agent.py still imports ZepToolsService, InsightForgeResult, etc.
This shim provides those names backed by graphiti_tools.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .graphiti_tools import GraphitiToolsService as _GraphitiTools
from .zep_entity_reader import EntityNode, ZepEntityReader


# ---------------------------------------------------------------------------
# Result wrapper classes — provide .to_text() that report_agent.py expects
# ---------------------------------------------------------------------------

class _DictResult:
    """Base class wrapping a dict result with a to_text() method."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def to_text(self) -> str:
        return json.dumps(self._data, ensure_ascii=False, indent=2)

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


# ---------------------------------------------------------------------------
# ZepToolsService shim
# ---------------------------------------------------------------------------

class ZepToolsService:
    """
    Drop-in replacement for the old ZepToolsService backed by GraphitiToolsService.
    """

    def __init__(self, api_key: Optional[str] = None):
        # api_key is ignored — Graphiti uses Neo4j
        self._tools = _GraphitiTools()
        self._entity_reader = ZepEntityReader()

    # --- Core search tools ---

    def insight_forge(
        self,
        graph_id: str,
        query: str,
        simulation_requirement: str = "",
        report_context: str = "",
        entity_name: str = "",
        limit: int = 15,
    ) -> InsightForgeResult:
        # Use entity_name if provided, else extract first noun-phrase from query
        name = entity_name or query.split()[:3]
        name = name if isinstance(name, str) else " ".join(name)
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
        # interview_agents is not implemented in graphiti_tools (no simulation IPC).
        # Return a placeholder so report generation degrades gracefully.
        return InterviewResult({
            "note": "interview_agents is not supported in Graphiti mode",
            "simulation_id": simulation_id,
            "interview_requirement": interview_requirement,
            "answers": [],
        })

    # --- Statistics / metadata ---

    def get_graph_statistics(self, graph_id: str) -> Dict[str, Any]:
        stats = self._tools.get_graph_statistics(group_id=graph_id)
        # Normalise key names to match what report_agent.py expects
        return {
            "total_nodes":  stats.get("node_count", 0),
            "total_edges":  stats.get("edge_count", 0),
            "node_count":   stats.get("node_count", 0),
            "edge_count":   stats.get("edge_count", 0),
            "node_types":   stats.get("node_types", {}),
            "edge_types":   stats.get("edge_types", {}),
            "entity_types": stats.get("node_types", {}),
        }

    def get_entity_summary(self, graph_id: str, entity_name: str) -> Dict[str, Any]:
        nodes = self._entity_reader.get_entities_by_type(graph_id=graph_id, entity_type=entity_name)
        if not nodes:
            # Try name-match via filter
            filtered = self._entity_reader.filter_defined_entities(graph_id=graph_id)
            nodes = [e for e in filtered.entities if entity_name.lower() in e.name.lower()]
        if nodes:
            return nodes[0].to_dict()
        return {"name": entity_name, "found": False}

    def get_entities_by_type(self, graph_id: str, entity_type: str) -> List[EntityNode]:
        return self._entity_reader.get_entities_by_type(graph_id=graph_id, entity_type=entity_type)

    def get_simulation_context(
        self,
        graph_id: str,
        simulation_requirement: str = "",
    ) -> Dict[str, Any]:
        """Return a context dict that report_agent.py's plan_outline() expects."""
        stats = self.get_graph_statistics(graph_id)
        # Quick broad search for related facts
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
