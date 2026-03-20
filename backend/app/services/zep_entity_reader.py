# backend/app/services/zep_entity_reader.py
"""
Compatibility shim: maps old Zep entity reader API onto GraphitiEntityReader.

Files that still import from here (simulation_manager, simulation_config_generator,
oasis_profile_generator) continue to work unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .graphiti_entity_reader import GraphitiEntityReader as _Graphiti

_BUILT_IN_LABELS = {"Entity", "Node", "EpisodicNode", "CommunityNode"}


@dataclass
class EntityNode:
    """Drop-in replacement for the old Zep EntityNode dataclass."""

    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    related_edges: List[Dict[str, Any]] = field(default_factory=list)
    related_nodes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid":          self.uuid,
            "name":          self.name,
            "labels":        self.labels,
            "summary":       self.summary,
            "attributes":    self.attributes,
            "related_edges": self.related_edges,
            "related_nodes": self.related_nodes,
        }

    def get_entity_type(self) -> Optional[str]:
        """Return the first non-built-in label, or None."""
        for label in self.labels:
            if label not in _BUILT_IN_LABELS:
                return label
        return None


@dataclass
class FilteredEntities:
    """Drop-in replacement for the old Zep FilteredEntities dataclass."""

    entities: List[EntityNode]
    entity_types: Set[str]
    total_count: int
    filtered_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities":       [e.to_dict() for e in self.entities],
            "entity_types":   list(self.entity_types),
            "total_count":    self.total_count,
            "filtered_count": self.filtered_count,
        }


def _dict_to_entity_node(d: Dict[str, Any]) -> EntityNode:
    return EntityNode(
        uuid=d.get("uuid", ""),
        name=d.get("name", ""),
        labels=d.get("labels", []),
        summary=d.get("summary", ""),
        attributes=d.get("attributes", {}),
        related_edges=d.get("edges", []),   # graphiti_entity_reader stores edges as "edges"
        related_nodes=[],
    )


class ZepEntityReader:
    """
    Drop-in replacement for the old ZepEntityReader backed by GraphitiEntityReader.
    The old API used graph_id / defined_entity_types keyword args.
    """

    def __init__(self, api_key: Optional[str] = None):
        # api_key is ignored — Graphiti uses Neo4j, not Zep Cloud
        self._reader = _Graphiti()

    def filter_defined_entities(
        self,
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = False,
    ) -> FilteredEntities:
        """Return FilteredEntities matching the old Zep interface."""
        raw_nodes = self._reader.filter_defined_entities(
            group_id=graph_id,
            custom_labels=defined_entity_types if defined_entity_types else None,
        )

        entities: List[EntityNode] = []
        entity_types: Set[str] = set()

        for node in raw_nodes:
            if enrich_with_edges:
                enriched = self._reader.get_entity_with_edges(graph_id, node["uuid"])
                if enriched:
                    node = enriched
            en = _dict_to_entity_node(node)
            entities.append(en)
            t = en.get_entity_type()
            if t:
                entity_types.add(t)

        return FilteredEntities(
            entities=entities,
            entity_types=entity_types,
            total_count=len(raw_nodes),
            filtered_count=len(entities),
        )

    def get_entities_by_type(
        self,
        graph_id: str,
        entity_type: str,
        enrich_with_edges: bool = False,
    ) -> List[EntityNode]:
        raw_nodes = self._reader.get_entities_by_type(group_id=graph_id, entity_type=entity_type)
        result = []
        for node in raw_nodes:
            if enrich_with_edges:
                enriched = self._reader.get_entity_with_edges(graph_id, node["uuid"])
                if enriched:
                    node = enriched
            result.append(_dict_to_entity_node(node))
        return result

    def get_entity_with_context(
        self,
        graph_id: str,
        entity_uuid: str,
    ) -> Optional[EntityNode]:
        node = self._reader.get_entity_with_edges(graph_id, entity_uuid)
        if node is None:
            return None
        return _dict_to_entity_node(node)

    def get_all_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        data = self._reader.get_all_nodes_and_edges(graph_id)
        return data.get("nodes", [])

    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        data = self._reader.get_all_nodes_and_edges(graph_id)
        return data.get("edges", [])
