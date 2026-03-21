# backend/app/services/graphiti_entity_reader.py
"""
Entity/node reading for simulation agent generation.
Replaces zep_entity_reader.py.

Key changes:
- uuid_ → uuid (field rename)
- Uses EntityNode.get_by_uuid for single-entity lookups
- EntityEdge.get_by_node_uuid for per-node edge lookup
- filter_defined_entities checks node labels for custom entity types
"""

from typing import Any
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from graphiti_core.nodes import EntityNode as _CoreEntityNode
from graphiti_core.edges import EntityEdge

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
        """Return nodes that have at least one custom (non-built-in) label."""
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
            node = run_async(_CoreEntityNode.get_by_uuid(graphiti.driver, entity_uuid))
        except Exception as exc:
            logger.warning(f"Entity {entity_uuid} not found in group_id={group_id}: {exc}")
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
        try:
            edges = run_async(EntityEdge.get_by_node_uuid(graphiti.driver, entity_uuid))
        except Exception:
            edges = []
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
            for e in (edges or [])
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


# ---------------------------------------------------------------------------
# DTO types — previously in zep_entity_reader.py shim
# ---------------------------------------------------------------------------

_BUILT_IN_LABELS = {"Entity", "Node", "EpisodicNode", "CommunityNode"}


@dataclass
class EntityNode:
    """Entity node DTO used by simulation and config-generation code."""

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
    """Filtered entity collection DTO."""

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
        related_edges=d.get("edges", []),
        related_nodes=[],
    )


class ZepEntityReader:
    """
    Entity reader with the legacy Zep-compatible interface, backed by GraphitiEntityReader.
    Previously in zep_entity_reader.py — moved here when shim was removed.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._reader = GraphitiEntityReader()

    def filter_defined_entities(
        self,
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = False,
    ) -> FilteredEntities:
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
        return self._reader.get_all_nodes_and_edges(graph_id).get("nodes", [])

    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        return self._reader.get_all_nodes_and_edges(graph_id).get("edges", [])
