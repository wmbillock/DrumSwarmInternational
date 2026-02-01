"""Tests for CLI API client mode — mocked HTTP."""

import pytest
from unittest.mock import patch, MagicMock
from backend.cli.client import APIClient


class TestAPIClient:
    def test_ping_unreachable(self):
        client = APIClient(base_url="http://localhost:99999")
        assert client.ping() is False

    def test_season_create_call(self):
        client = APIClient()
        with patch.object(client, "_request", return_value={"season_id": "test_2026"}) as mock:
            result = client.season_create("Test", year=2026)
            mock.assert_called_once_with("POST", "/api/seasons", json={"name": "Test", "year": 2026})
            assert result["season_id"] == "test_2026"

    def test_corps_status_call(self):
        client = APIClient()
        with patch.object(client, "_request", return_value={"id": "abc", "status": "winter_camps"}) as mock:
            result = client.corps_status("abc")
            mock.assert_called_once_with("GET", "/api/corps/abc", params={})
            assert result["id"] == "abc"

    def test_mode_switch_call(self):
        client = APIClient()
        with patch.object(client, "_request", return_value={"id": "abc", "mode": "design_room"}) as mock:
            result = client.mode_switch("abc", "design_room")
            mock.assert_called_once_with("POST", "/api/corps/abc/mode", json={"mode": "design_room"})
            assert result["mode"] == "design_room"

    def test_show_list_call(self):
        client = APIClient()
        with patch.object(client, "_request", return_value=[]) as mock:
            result = client.show_list()
            mock.assert_called_once_with("GET", "/api/shows", params={})
            assert result == []

    def test_system_health_call(self):
        client = APIClient()
        with patch.object(client, "_request", return_value={"active_corps": 2}) as mock:
            result = client.system_health()
            assert result["active_corps"] == 2
