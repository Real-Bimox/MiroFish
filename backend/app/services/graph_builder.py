# backend/app/services/graph_builder.py
"""
Graph lifecycle management using Graphiti (self-hosted, replaces Zep Cloud).

Key changes from Zep version:
- No explicit create_graph step — group_id is passed inline to Graphiti
- Ontology uses pydantic BaseModel subclasses (not Zep EntityModel/EdgeModel)
- add_episode_bulk is synchronous from caller's perspective (bridge via run_async)
- build_communities() called after ingest for richer ReportAgent context
- delete_graph uses Node.delete_by_group_id
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel

from app.services.graphiti_client import get_graphiti, close_graphiti, SOCIAL_SIMULATION_PROMPT
from app.utils.graphiti_paging import fetch_all_nodes, fetch_all_edges
from app.utils.async_loop import run_async
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GraphBuilderService:

    def generate_group_id(self) -> str:
        return f"mirofish_{uuid.uuid4().hex[:16]}"

    def build_entity_types(self, ontology: dict) -> dict[str, type[BaseModel]]:
        """Convert MiroFish ontology dict to Graphiti entity_types format."""
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

        Returns a dict with: group_id, node_count, edge_count, status
        """
        group_id = self.generate_group_id()
        logger.info(f"Building graph group_id={group_id} for project={project_id}")

        graphiti = get_graphiti(group_id)
        entity_types  = self.build_entity_types(ontology)
        edge_types    = self.build_edge_types(ontology)
        edge_type_map = self.build_edge_type_map(ontology)

        # EpisodeType lives in bulk_utils, not graphiti_core top-level
        from graphiti_core.utils.bulk_utils import RawEpisode, EpisodeType
        episode_source = EpisodeType.text

        total = len(text_chunks)
        processed = 0

        for batch_start in range(0, total, batch_size):
            batch = text_chunks[batch_start : batch_start + batch_size]

            episodes = [
                RawEpisode(
                    name=f"{graph_name}_chunk_{batch_start + i}",
                    content=chunk,
                    source=episode_source,
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

    def delete_graph(self, group_id: str) -> None:
        """Delete all nodes and edges for this group_id from Neo4j."""
        graphiti = get_graphiti(group_id)
        from graphiti_core.nodes import Node
        run_async(Node.delete_by_group_id(graphiti.driver, group_id))
        close_graphiti(group_id)
        logger.info(f"Deleted graph group_id={group_id}")
