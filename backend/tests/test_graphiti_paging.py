# backend/tests/test_graphiti_paging.py
"""
Tests for graphiti_paging.py — paginated node/edge enumeration using
EntityNode.get_by_group_ids and EntityEdge.get_by_group_ids.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers to build fake EntityNode / EntityEdge objects
# ---------------------------------------------------------------------------

def _make_node(uuid: str, name: str = "Node", labels=None, summary="", attributes=None):
    node = MagicMock()
    node.uuid = uuid
    node.name = name
    node.labels = labels or []
    node.summary = summary
    node.attributes = attributes or {}
    return node


def _make_edge(
    uuid: str,
    name: str = "RELATES_TO",
    fact: str = "some fact",
    source_node_uuid: str = "src-uuid",
    target_node_uuid: str = "tgt-uuid",
    valid_at=None,
    invalid_at=None,
    expired_at=None,
    attributes=None,
):
    edge = MagicMock()
    edge.uuid = uuid
    edge.name = name
    edge.fact = fact
    edge.source_node_uuid = source_node_uuid
    edge.target_node_uuid = target_node_uuid
    edge.valid_at = valid_at
    edge.invalid_at = invalid_at
    edge.expired_at = expired_at
    edge.attributes = attributes or {}
    return edge


# ---------------------------------------------------------------------------
# Node tests
# ---------------------------------------------------------------------------

class TestFetchAllNodes:
    def test_returns_list_of_dicts(self):
        """fetch_all_nodes returns a list of dicts with required keys."""
        fake_nodes = [
            _make_node("uuid-1", "Alice", ["Person"], "A person", {"age": 30}),
            _make_node("uuid-2", "Bob", [], "", {}),
        ]

        async def fake_get_by_group_ids(driver, group_ids, limit=None, uuid_cursor=None, **kw):
            return fake_nodes

        with patch(
            "graphiti_core.nodes.EntityNode.get_by_group_ids",
            new=fake_get_by_group_ids,
        ):
            from app.utils.graphiti_paging import fetch_all_nodes

            result = fetch_all_nodes(driver=MagicMock(), group_id="grp-1", page_size=100)

        assert len(result) == 2
        assert result[0] == {
            "uuid": "uuid-1",
            "name": "Alice",
            "labels": ["Person"],
            "summary": "A person",
            "attributes": {"age": 30},
        }
        assert result[1] == {
            "uuid": "uuid-2",
            "name": "Bob",
            "labels": [],
            "summary": "",
            "attributes": {},
        }

    def test_all_required_keys_present(self):
        """Every returned dict has exactly the required keys."""
        fake_nodes = [_make_node("u-1")]

        async def fake_get_by_group_ids(driver, group_ids, limit=None, uuid_cursor=None, **kw):
            return fake_nodes

        with patch("graphiti_core.nodes.EntityNode.get_by_group_ids", new=fake_get_by_group_ids):
            from app.utils.graphiti_paging import fetch_all_nodes

            result = fetch_all_nodes(MagicMock(), "grp-1")

        required_keys = {"uuid", "name", "labels", "summary", "attributes"}
        for row in result:
            assert set(row.keys()) == required_keys

    def test_empty_group_returns_empty_list(self):
        """When no nodes exist, returns empty list."""

        async def fake_get_by_group_ids(driver, group_ids, limit=None, uuid_cursor=None, **kw):
            return []

        with patch("graphiti_core.nodes.EntityNode.get_by_group_ids", new=fake_get_by_group_ids):
            from app.utils.graphiti_paging import fetch_all_nodes

            result = fetch_all_nodes(MagicMock(), "empty-group")

        assert result == []

    def test_pagination_fetches_second_page(self):
        """When first page is full, a second page is fetched."""
        page1 = [_make_node(f"u-{i}") for i in range(3)]
        page2 = [_make_node(f"u-{i}") for i in range(3, 5)]
        pages = [page1, page2]
        call_count = 0

        async def fake_get_by_group_ids(driver, group_ids, limit=None, uuid_cursor=None, **kw):
            nonlocal call_count
            result = pages[call_count]
            call_count += 1
            return result

        with patch("graphiti_core.nodes.EntityNode.get_by_group_ids", new=fake_get_by_group_ids):
            from app.utils.graphiti_paging import fetch_all_nodes

            result = fetch_all_nodes(MagicMock(), "grp-1", page_size=3)

        assert call_count == 2
        assert len(result) == 5

    def test_pagination_stops_when_page_is_partial(self):
        """When a page returns fewer items than page_size, no further pages are fetched."""
        page1 = [_make_node(f"u-{i}") for i in range(3)]
        page2 = [_make_node(f"u-{i}") for i in range(3, 5)]  # only 2 < page_size=3
        pages = [page1, page2]
        call_count = 0

        async def fake_get_by_group_ids(driver, group_ids, limit=None, uuid_cursor=None, **kw):
            nonlocal call_count
            result = pages[call_count]
            call_count += 1
            return result

        with patch("graphiti_core.nodes.EntityNode.get_by_group_ids", new=fake_get_by_group_ids):
            from app.utils.graphiti_paging import fetch_all_nodes

            result = fetch_all_nodes(MagicMock(), "grp-1", page_size=3)

        assert call_count == 2
        assert len(result) == 5

    def test_cursor_passed_on_second_page(self):
        """The uuid of the last node in page 1 is passed as cursor for page 2."""
        page1 = [_make_node("uuid-last-of-page1")]
        captured_cursors = []

        call_count = 0

        async def fake_get_by_group_ids(driver, group_ids, limit=None, uuid_cursor=None, **kw):
            nonlocal call_count
            captured_cursors.append(uuid_cursor)
            call_count += 1
            if call_count == 1:
                return page1
            return []

        with patch("graphiti_core.nodes.EntityNode.get_by_group_ids", new=fake_get_by_group_ids):
            from app.utils.graphiti_paging import fetch_all_nodes

            fetch_all_nodes(MagicMock(), "grp-1", page_size=1)

        assert captured_cursors[0] is None
        assert captured_cursors[1] == "uuid-last-of-page1"


# ---------------------------------------------------------------------------
# Edge tests
# ---------------------------------------------------------------------------

class TestFetchAllEdges:
    def test_returns_list_of_dicts(self):
        """fetch_all_edges returns a list of dicts with required keys."""
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        fake_edges = [
            _make_edge(
                "e-1",
                name="KNOWS",
                fact="Alice knows Bob",
                source_node_uuid="src-1",
                target_node_uuid="tgt-1",
                valid_at=ts,
                invalid_at=None,
                expired_at=None,
                attributes={"weight": 1},
            ),
        ]

        async def fake_get_by_group_ids(driver, group_ids, limit=None, uuid_cursor=None, **kw):
            return fake_edges

        with patch("graphiti_core.edges.EntityEdge.get_by_group_ids", new=fake_get_by_group_ids):
            from app.utils.graphiti_paging import fetch_all_edges

            result = fetch_all_edges(MagicMock(), "grp-1")

        assert len(result) == 1
        assert result[0] == {
            "uuid": "e-1",
            "name": "KNOWS",
            "fact": "Alice knows Bob",
            "source_node_uuid": "src-1",
            "target_node_uuid": "tgt-1",
            "valid_at": ts,
            "invalid_at": None,
            "expired_at": None,
            "attributes": {"weight": 1},
        }

    def test_all_required_keys_present(self):
        """Every returned dict has exactly the required keys."""
        fake_edges = [_make_edge("e-1")]

        async def fake_get_by_group_ids(driver, group_ids, limit=None, uuid_cursor=None, **kw):
            return fake_edges

        with patch("graphiti_core.edges.EntityEdge.get_by_group_ids", new=fake_get_by_group_ids):
            from app.utils.graphiti_paging import fetch_all_edges

            result = fetch_all_edges(MagicMock(), "grp-1")

        required_keys = {
            "uuid", "name", "fact",
            "source_node_uuid", "target_node_uuid",
            "valid_at", "invalid_at", "expired_at",
            "attributes",
        }
        for row in result:
            assert set(row.keys()) == required_keys

    def test_empty_group_returns_empty_list(self):
        """When no edges exist, returns empty list."""

        async def fake_get_by_group_ids(driver, group_ids, limit=None, uuid_cursor=None, **kw):
            return []

        with patch("graphiti_core.edges.EntityEdge.get_by_group_ids", new=fake_get_by_group_ids):
            from app.utils.graphiti_paging import fetch_all_edges

            result = fetch_all_edges(MagicMock(), "empty-group")

        assert result == []

    def test_pagination_fetches_second_page(self):
        """When first page is full, a second page is fetched."""
        page1 = [_make_edge(f"e-{i}") for i in range(3)]
        page2 = [_make_edge(f"e-{i}") for i in range(3, 5)]
        pages = [page1, page2]
        call_count = 0

        async def fake_get_by_group_ids(driver, group_ids, limit=None, uuid_cursor=None, **kw):
            nonlocal call_count
            result = pages[call_count]
            call_count += 1
            return result

        with patch("graphiti_core.edges.EntityEdge.get_by_group_ids", new=fake_get_by_group_ids):
            from app.utils.graphiti_paging import fetch_all_edges

            result = fetch_all_edges(MagicMock(), "grp-1", page_size=3)

        assert call_count == 2
        assert len(result) == 5

    def test_cursor_passed_on_second_page(self):
        """The uuid of the last edge in page 1 is passed as cursor for page 2."""
        page1 = [_make_edge("e-last-of-page1")]
        captured_cursors = []
        call_count = 0

        async def fake_get_by_group_ids(driver, group_ids, limit=None, uuid_cursor=None, **kw):
            nonlocal call_count
            captured_cursors.append(uuid_cursor)
            call_count += 1
            if call_count == 1:
                return page1
            return []

        with patch("graphiti_core.edges.EntityEdge.get_by_group_ids", new=fake_get_by_group_ids):
            from app.utils.graphiti_paging import fetch_all_edges

            fetch_all_edges(MagicMock(), "grp-1", page_size=1)

        assert captured_cursors[0] is None
        assert captured_cursors[1] == "e-last-of-page1"
