"""Tests for Design Room — spec persistence, API endpoints, and security."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from backend.services.show_persistence import (
    create_show,
    read_spec,
    write_spec,
    approve_spec,
    list_spec_versions,
    load_status,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def show_dir(tmp_path):
    """Create a show workspace in a temp directory."""
    return create_show("test-show", tmp_path)


# ---------------------------------------------------------------------------
# Spec persistence (filesystem)
# ---------------------------------------------------------------------------

class TestSpecPersistence:
    def test_write_and_read_spec(self, show_dir):
        content = "---\nshow_slug: test\n---\n# Test\n## Decisions\n- Item 1\n"
        write_spec(show_dir, content)
        assert read_spec(show_dir) == content

    def test_read_spec_nonexistent(self, show_dir):
        assert read_spec(show_dir) == ""

    def test_approve_spec_creates_versioned_copy(self, show_dir):
        write_spec(show_dir, "# Spec\n## Decisions\n- D1\n")
        approve_spec(show_dir)
        assert (show_dir / "spec_v1.md").exists()

    def test_approve_spec_updates_status(self, show_dir):
        write_spec(show_dir, "# Spec\ncontent\n")
        approve_spec(show_dir)
        status = load_status(show_dir)
        assert status["status"] == "approved"

    def test_approve_spec_provenance(self, show_dir):
        write_spec(show_dir, "---\nshow_slug: test\napproved_at: null\n---\n# Spec\n")
        approve_spec(show_dir)
        frozen = (show_dir / "spec_v1.md").read_text()
        assert "approved_at:" in frozen
        assert "null" not in frozen.split("---")[1]  # front matter should have real timestamp

    def test_approve_empty_spec_fails(self, show_dir):
        with pytest.raises(ValueError, match="empty"):
            approve_spec(show_dir)

    def test_approve_empty_string_spec_fails(self, show_dir):
        write_spec(show_dir, "")
        with pytest.raises(ValueError, match="empty"):
            approve_spec(show_dir)

    def test_double_approve_increments_version(self, show_dir):
        write_spec(show_dir, "# Spec v1\n")
        approve_spec(show_dir)
        write_spec(show_dir, "# Spec v2\n")
        result = approve_spec(show_dir)
        assert result["version"] == 2
        assert (show_dir / "spec_v2.md").exists()

    def test_list_versions(self, show_dir):
        write_spec(show_dir, "# Spec\n")
        approve_spec(show_dir)
        write_spec(show_dir, "# Spec 2\n")
        approve_spec(show_dir)
        versions = list_spec_versions(show_dir)
        assert versions == [1, 2]

    def test_list_versions_empty(self, show_dir):
        assert list_spec_versions(show_dir) == []


# ---------------------------------------------------------------------------
# API endpoints (TestClient)
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client(tmp_path, monkeypatch):
    """Create a FastAPI test client with DCI_PROJECT_ROOT set to tmp_path."""
    monkeypatch.setenv("DCI_PROJECT_ROOT", str(tmp_path))
    # Create shows directory
    (tmp_path / "shows").mkdir()
    from backend.api.design_room_routes import router, _get_shows_dir
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestDesignRoomAPI:
    def test_create_design_show(self, api_client, tmp_path):
        resp = api_client.post("/api/design/shows", json={"title": "My Show"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "my-show"
        assert (tmp_path / "shows" / "my-show" / "spec.md").exists()

    def test_get_spec(self, api_client, tmp_path):
        api_client.post("/api/design/shows", json={"title": "My Show"})
        resp = api_client.get("/api/design/shows/my-show/spec")
        assert resp.status_code == 200
        data = resp.json()
        assert "content" in data

    def test_update_spec(self, api_client):
        api_client.post("/api/design/shows", json={"title": "My Show"})
        resp = api_client.put(
            "/api/design/shows/my-show/spec",
            json={"content": "# Updated\n## Decisions\n- New decision\n"},
        )
        assert resp.status_code == 200
        # Verify update persisted
        get_resp = api_client.get("/api/design/shows/my-show/spec")
        assert "Updated" in get_resp.json()["content"]

    def test_conversation_routes_note(self, api_client):
        api_client.post("/api/design/shows", json={"title": "My Show"})
        resp = api_client.post(
            "/api/design/shows/my-show/conversation",
            json={"message": "Add a brass fanfare in the opener"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "role" in data
        assert "tags" in data
        assert "architecture" in data["tags"]

    def test_approve_endpoint(self, api_client, tmp_path):
        api_client.post("/api/design/shows", json={"title": "My Show"})
        api_client.put(
            "/api/design/shows/my-show/spec",
            json={"content": "# My Show\n## Decisions\n- D1\n"},
        )
        resp = api_client.post("/api/design/shows/my-show/approve")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == 1
        assert (tmp_path / "shows" / "my-show" / "spec_v1.md").exists()

    def test_approve_already_approved(self, api_client):
        """Second approve should succeed with incremented version."""
        api_client.post("/api/design/shows", json={"title": "My Show"})
        api_client.put("/api/design/shows/my-show/spec", json={"content": "# Spec\n"})
        api_client.post("/api/design/shows/my-show/approve")
        api_client.put("/api/design/shows/my-show/spec", json={"content": "# Spec v2\n"})
        resp = api_client.post("/api/design/shows/my-show/approve")
        assert resp.status_code == 200
        assert resp.json()["version"] == 2

    def test_versions_endpoint(self, api_client):
        api_client.post("/api/design/shows", json={"title": "My Show"})
        api_client.put("/api/design/shows/my-show/spec", json={"content": "# Spec\n"})
        api_client.post("/api/design/shows/my-show/approve")
        resp = api_client.get("/api/design/shows/my-show/versions")
        assert resp.status_code == 200
        assert resp.json()["versions"] == [1]


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

class TestDesignRoomSecurity:
    def test_slug_traversal_rejected(self, api_client):
        resp = api_client.get("/api/design/shows/../etc/passwd/spec")
        # FastAPI may 404 due to routing, but any slug with .. should be rejected
        assert resp.status_code in (400, 404, 422)

    def test_slug_with_dotdot_rejected(self, api_client):
        resp = api_client.post(
            "/api/design/shows",
            json={"title": "../../etc/passwd"},
        )
        # slugify will strip these, so it should either fail or produce a safe slug
        if resp.status_code == 200:
            assert ".." not in resp.json()["slug"]

    def test_spec_path_traversal_blocked(self, api_client):
        resp = api_client.get("/api/design/shows/..%2F..%2Fetc%2Fpasswd/spec")
        assert resp.status_code in (400, 404, 422)
