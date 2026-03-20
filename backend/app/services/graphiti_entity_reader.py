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
from graphiti_core.nodes import EntityNode
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
            node = run_async(EntityNode.get_by_uuid(graphiti.driver, entity_uuid))
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
