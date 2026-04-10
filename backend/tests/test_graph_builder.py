# backend/tests/test_graph_builder.py
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from app.services.graph_builder import GraphBuilderService

FAKE_ONTOLOGY = {
    "entity_types": [{"name": "Agent", "description": "A social agent"}],
    "edge_types":   [{"name": "KNOWS", "description": "Knows relationship"}],
    "source_targets": {"KNOWS": [{"source": "Agent", "target": "Agent"}]},
}


@patch("app.services.graph_builder.get_graphiti")
def test_build_graph_returns_group_id(mock_get_g):
    g = MagicMock()
    g.driver = MagicMock()
    g.add_episode_bulk = AsyncMock(return_value=MagicMock())
    g.build_communities = AsyncMock()
    mock_get_g.return_value = g

    with patch("app.services.graph_builder.fetch_all_nodes", return_value=[]), \
         patch("app.services.graph_builder.fetch_all_edges", return_value=[]):
        svc = GraphBuilderService()
        result = svc.build_graph(
            project_id="proj_1",
            text_chunks=["chunk one", "chunk two"],
            ontology=FAKE_ONTOLOGY,
            graph_name="test graph",
        )
    assert result["group_id"].startswith("mirofish_")
    assert result["status"] == "complete"


@patch("app.services.graph_builder.get_graphiti")
@patch("app.services.graph_builder.close_graphiti")
def test_delete_graph_closes_cache(mock_close, mock_get_g):
    g = MagicMock()
    g.driver = MagicMock()
    mock_get_g.return_value = g

    with patch("app.services.graph_builder.run_async"):
        svc = GraphBuilderService()
        svc.delete_graph("mirofish_abc123")

    mock_close.assert_called_once_with("mirofish_abc123")
