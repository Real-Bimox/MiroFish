# backend/tests/test_graphiti_entity_reader.py
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.graphiti_entity_reader import GraphitiEntityReader


def _node(uuid, name, labels):
    n = MagicMock()
    n.uuid = uuid
    n.name = name
    n.labels = labels
    n.summary = "summary"
    n.attributes = {}
    return n


def _edge(uuid, src, tgt, name, fact):
    e = MagicMock()
    e.uuid = uuid
    e.source_node_uuid = src
    e.target_node_uuid = tgt
    e.name = name
    e.fact = fact
    e.valid_at = None
    e.invalid_at = None
    e.expired_at = None
    e.attributes = {}
    return e


@patch("app.services.graphiti_entity_reader.fetch_all_nodes")
@patch("app.services.graphiti_entity_reader.fetch_all_edges")
@patch("app.services.graphiti_entity_reader.get_graphiti")
def test_filter_returns_custom_typed_nodes(mock_g, mock_edges, mock_nodes):
    mock_g.return_value = MagicMock()
    mock_nodes.return_value = [
        {"uuid": "u1", "name": "Alice", "labels": ["Entity", "Agent"], "summary": "", "attributes": {}},
        {"uuid": "u2", "name": "Neo4j", "labels": ["Entity"], "summary": "", "attributes": {}},
    ]
    mock_edges.return_value = []

    reader = GraphitiEntityReader()
    result = reader.filter_defined_entities("group_1", custom_labels=["Agent"])
    assert len(result) == 1
    assert result[0]["name"] == "Alice"


@patch("app.services.graphiti_entity_reader.get_graphiti")
def test_get_entity_not_found_returns_none(mock_g):
    mock_g.return_value = MagicMock()
    # Mock run_async to raise an exception representing "not found"
    with patch("app.services.graphiti_entity_reader.run_async", side_effect=Exception("not found")):
        reader = GraphitiEntityReader()
        result = reader.get_entity_by_uuid("group_1", "nonexistent-uuid")
    assert result is None
