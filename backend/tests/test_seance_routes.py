"""Tests for seance & corps history API routes."""

import os
import yaml
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, default_flow_style=False, sort_keys=False))


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _setup_corps(tmp_path: Path, corps_id: str = "cavaliers") -> None:
    """Create a corps with one history entry and artifacts on disk."""
    _write_yaml(tmp_path / "corps" / corps_id / "corps.yaml", {
        "corps_id": corps_id,
        "display_name": corps_id.title(),
        "philosophy": "",
        "state": "active",
        "history": [
            {"season_id": "s1", "placement": 1, "final_score": 85.0, "notes": "show:my-show"},
        ],
    })
    _write_yaml(tmp_path / "seasons" / "s1" / "standings.yaml", {
        "season_id": "s1",
        "results": [{"corps_id": corps_id, "rank": 1, "final_score": 85.0}],
    })
    _write_yaml(tmp_path / "seasons" / "s1" / "performances" / corps_id / "scores.yaml", {
        "corps_id": corps_id,
        "caption_scores": {"brass": 80, "percussion": 90},
    })
    _write_yaml(tmp_path / "shows" / "my-show" / "status.yaml", {"status": "approved"})
    _write_text(tmp_path / "shows" / "my-show" / "design_notes.md", "# Design Notes\nBrass feature.")

    from backend.services.corps_history import build_history_index
    build_history_index(tmp_path, corps_id)


@pytest.fixture()
def client(tmp_path):
    os.environ["DCI_PROJECT_ROOT"] = str(tmp_path)
    _setup_corps(tmp_path)

    from backend.api.seance_routes import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    yield TestClient(app)
    os.environ.pop("DCI_PROJECT_ROOT", None)


# ---------------------------------------------------------------------------
# Corps History Index
# ---------------------------------------------------------------------------

class TestHistoryIndex:
    def test_get_history_index(self, client):
        resp = client.get("/api/corps/cavaliers/history-index")
        assert resp.status_code == 200
        data = resp.json()
        assert data["corps_id"] == "cavaliers"
        assert len(data["entries"]) == 1
        assert data["entries"][0]["entry_id"] == "cavaliers-s1"

    def test_get_history_index_not_found(self, client):
        resp = client.get("/api/corps/nonexistent/history-index")
        assert resp.status_code == 404

    def test_get_history_index_traversal(self, client):
        resp = client.get("/api/corps/..%2Fetc/history-index")
        assert resp.status_code in (400, 404)  # FastAPI decodes %2F, splitting the path


# ---------------------------------------------------------------------------
# Seance Creation
# ---------------------------------------------------------------------------

class TestSeanceCreation:
    def test_create_seance(self, client):
        resp = client.post("/api/seances", json={
            "corps_id": "cavaliers",
            "entry_id": "cavaliers-s1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["corps_id"] == "cavaliers"
        assert data["status"] == "active"
        assert data["participant"] == "executive_director"
        assert len(data["context_binder"]) > 0

    def test_create_seance_bad_entry(self, client):
        resp = client.post("/api/seances", json={
            "corps_id": "cavaliers",
            "entry_id": "cavaliers-nope",
        })
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Seance Operations
# ---------------------------------------------------------------------------

class TestSeanceOperations:
    def _create(self, client) -> str:
        resp = client.post("/api/seances", json={
            "corps_id": "cavaliers",
            "entry_id": "cavaliers-s1",
        })
        return resp.json()["seance_id"]

    def test_get_seance(self, client):
        sid = self._create(client)
        resp = client.get(f"/api/seances/{sid}")
        assert resp.status_code == 200
        assert resp.json()["seance_id"] == sid

    def test_get_binder(self, client):
        sid = self._create(client)
        resp = client.get(f"/api/seances/{sid}/binder")
        assert resp.status_code == 200
        data = resp.json()
        assert data["seance_id"] == sid
        assert len(data["context_binder"]) > 0

    def test_get_transcript(self, client):
        sid = self._create(client)
        resp = client.get(f"/api/seances/{sid}/transcript")
        assert resp.status_code == 200
        assert "cavaliers" in resp.json()["transcript"]

    def test_post_message(self, client):
        sid = self._create(client)
        resp = client.post(f"/api/seances/{sid}/message", json={"message": "Hello ED"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "executive_director"
        assert data["mode"] == "strict"

        # Verify transcript updated
        resp2 = client.get(f"/api/seances/{sid}/transcript")
        transcript = resp2.json()["transcript"]
        assert "Hello ED" in transcript
        assert "executive_director" in transcript

    def test_artifact_preview(self, client):
        sid = self._create(client)
        binder = client.get(f"/api/seances/{sid}/binder").json()["context_binder"]
        standings_path = next(b["path"] for b in binder if b["type"] == "standings")

        resp = client.get(f"/api/seances/{sid}/artifact-preview", params={"path": standings_path})
        assert resp.status_code == 200
        assert "season_id" in resp.json()["content"]

    def test_artifact_preview_not_in_binder(self, client):
        sid = self._create(client)
        resp = client.get(f"/api/seances/{sid}/artifact-preview", params={"path": "evil/file.txt"})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

class TestSecurity:
    def test_seance_id_traversal(self, client):
        resp = client.get("/api/seances/../etc/passwd")
        # FastAPI will match the route or 400
        assert resp.status_code in (400, 404, 422)

    def test_artifact_preview_traversal(self, client):
        # Create valid session first
        resp = client.post("/api/seances", json={
            "corps_id": "cavaliers",
            "entry_id": "cavaliers-s1",
        })
        sid = resp.json()["seance_id"]
        resp = client.get(f"/api/seances/{sid}/artifact-preview", params={"path": "../../../etc/passwd"})
        assert resp.status_code == 400
