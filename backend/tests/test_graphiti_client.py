# backend/tests/test_graphiti_client.py
from unittest.mock import patch, MagicMock
from app.services.graphiti_client import get_graphiti, close_graphiti, SOCIAL_SIMULATION_PROMPT


def test_same_instance_returned_for_same_group():
    with patch("app.services.graphiti_client._build_graphiti") as mock_build:
        mock_build.return_value = MagicMock()
        g1 = get_graphiti("proj_abc")
        g2 = get_graphiti("proj_abc")
        assert g1 is g2
        assert mock_build.call_count == 1


def test_different_instances_for_different_groups():
    with patch("app.services.graphiti_client._build_graphiti") as mock_build:
        mock_build.side_effect = [MagicMock(), MagicMock()]
        g1 = get_graphiti("proj_a")
        g2 = get_graphiti("proj_b")
        assert g1 is not g2


def test_close_removes_from_cache():
    with patch("app.services.graphiti_client._build_graphiti") as mock_build:
        mock_build.return_value = MagicMock()
        get_graphiti("proj_x")
        close_graphiti("proj_x")
        get_graphiti("proj_x")
        assert mock_build.call_count == 2


def test_social_simulation_prompt_mentions_agents():
    assert "agent" in SOCIAL_SIMULATION_PROMPT.lower()
