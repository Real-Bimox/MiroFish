# backend/app/utils/graphiti_paging.py
"""
Paginated node and edge enumeration from Graphiti / Neo4j.

Replaces zep_paging.py. Uses EntityNode.get_by_group_ids and
EntityEdge.get_by_group_ids to enumerate all nodes/edges for a group_id
with cursor-based pagination.

Pagination stops when a returned page has fewer items than page_size,
or when the running total reaches _NODE_PAGE_LIMIT (safety cap).
"""

import time
from typing import Any

from neo4j.exceptions import ServiceUnavailable, TransientError

from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge

from app.utils.async_loop import run_async
from app.utils.logger import get_logger

logger = get_logger(__name__)

_RETRYABLE = (ServiceUnavailable, TransientError, ConnectionError, TimeoutError)
_MAX_RETRIES = 3
_RETRY_DELAY = 1.0  # seconds between retries
_NODE_PAGE_LIMIT = 2000


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_all_nodes(
    driver,
    group_id: str,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    """Return all EntityNodes for *group_id* as plain dicts.

    Keys: uuid, name, labels, summary, attributes.
    """
    results: list[dict[str, Any]] = []
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

    logger.debug("fetch_all_nodes: group=%s returned %d nodes", group_id, len(results))
    return results


def fetch_all_edges(
    driver,
    group_id: str,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    """Return all EntityEdges for *group_id* as plain dicts.

    Keys: uuid, name, fact, source_node_uuid, target_node_uuid,
          valid_at, invalid_at, expired_at, attributes.
    """
    results: list[dict[str, Any]] = []
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

    logger.debug("fetch_all_edges: group=%s returned %d edges", group_id, len(results))
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_node_page(
    driver,
    group_id: str,
    limit: int,
    uuid_cursor: str | None,
) -> list:
    """Fetch one page of EntityNodes with retry logic."""
    for attempt in range(_MAX_RETRIES):
        try:
            return run_async(
                EntityNode.get_by_group_ids(
                    driver=driver,
                    group_ids=[group_id],
                    limit=limit,
                    uuid_cursor=uuid_cursor,
                )
            )
        except _RETRYABLE as exc:
            if attempt == _MAX_RETRIES - 1:
                raise
            logger.warning(
                "fetch_node_page: transient error (attempt %d/%d): %s",
                attempt + 1,
                _MAX_RETRIES,
                exc,
            )
            time.sleep(_RETRY_DELAY)
    return []  # unreachable


def _fetch_edge_page(
    driver,
    group_id: str,
    limit: int,
    uuid_cursor: str | None,
) -> list:
    """Fetch one page of EntityEdges with retry logic."""
    for attempt in range(_MAX_RETRIES):
        try:
            return run_async(
                EntityEdge.get_by_group_ids(
                    driver=driver,
                    group_ids=[group_id],
                    limit=limit,
                    uuid_cursor=uuid_cursor,
                )
            )
        except _RETRYABLE as exc:
            if attempt == _MAX_RETRIES - 1:
                raise
            logger.warning(
                "fetch_edge_page: transient error (attempt %d/%d): %s",
                attempt + 1,
                _MAX_RETRIES,
                exc,
            )
            time.sleep(_RETRY_DELAY)
    return []  # unreachable
