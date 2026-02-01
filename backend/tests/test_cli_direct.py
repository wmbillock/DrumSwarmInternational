"""Tests for CLI direct mode — real DB operations."""

import pytest
from backend.cli.direct import DirectClient


@pytest.fixture
def direct_client(tmp_path):
    db_path = tmp_path / "test.db"
    return DirectClient(db_url=f"sqlite:///{db_path}")


class TestDirectClient:
    def test_show_list_empty(self, direct_client):
        result = direct_client.show_list()
        assert result == []

    def test_show_create_and_list(self, direct_client):
        result = direct_client.show_create("Test Show", description="A test")
        assert result["title"] == "Test Show"
        assert result["status"] == "draft"

        shows = direct_client.show_list()
        assert len(shows) == 1
        assert shows[0]["title"] == "Test Show"

    def test_corps_status_not_found(self, direct_client):
        result = direct_client.corps_status("nonexistent")
        assert "error" in result

    def test_system_health_empty(self, direct_client):
        result = direct_client.system_health()
        assert result["active_corps"] == 0
        assert result["total_agents"] == 0

    def test_global_log_empty(self, direct_client):
        result = direct_client.global_log()
        assert result == []
