# backend/tests/test_graphiti_tools.py
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.graphiti_tools import GraphitiToolsService


def _edge(uuid, fact, src, tgt, name="KNOWS", expired_at=None, invalid_at=None):
    e = MagicMock()
    e.uuid = uuid
    e.fact = fact
    e.source_node_uuid = src
    e.target_node_uuid = tgt
    e.name = name
    e.valid_at = None
    e.invalid_at = invalid_at
    e.expired_at = expired_at
    return e


def _node(uuid, name, labels=None, summary=""):
    n = MagicMock()
    n.uuid = uuid
    n.name = name
    n.labels = labels or ["Entity"]
    n.summary = summary
    return n


@patch("app.services.graphiti_tools.get_graphiti")
def test_quick_search_returns_structured_result(mock_g):
    g = MagicMock()
    g.driver = MagicMock()
    mock_result = MagicMock()
    mock_result.edges = [_edge("e1", "Alice leads the team", "uuid-a", "uuid-b")]
    mock_result.nodes = [_node("uuid-a", "Alice")]
    g.search_ = AsyncMock(return_value=mock_result)
    mock_g.return_value = g

    svc = GraphitiToolsService()
    result = svc.quick_search("group_1", "who leads?", limit=5)
    assert len(result["facts"]) == 1
    assert "Alice leads" in result["facts"][0]
    assert result["edge_count"] == 1


@patch("app.services.graphiti_tools.get_graphiti")
def test_search_filters_expired_edges(mock_g):
    from datetime import datetime, timezone
    g = MagicMock()
    g.driver = MagicMock()
    expired = _edge("e2", "Bob was CEO", "uuid-b", "uuid-c",
                    expired_at=datetime(2020, 1, 1, tzinfo=timezone.utc))
    active = _edge("e3", "Alice is CEO", "uuid-a", "uuid-b")
    mock_result = MagicMock()
    mock_result.edges = [expired, active]
    mock_result.nodes = []
    g.search_ = AsyncMock(return_value=mock_result)
    mock_g.return_value = g

    svc = GraphitiToolsService()
    result = svc.quick_search("group_1", "who is CEO?")
    active_facts = [f for f in result["facts"] if "Alice" in f]
    historical_facts = [f for f in result.get("historical_facts", []) if "Bob" in f]
    assert len(active_facts) == 1
    assert len(historical_facts) == 1
