"""Tests for workspace API routes (filesystem-reading endpoints)."""

import os

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base

# Import all models to populate Base.metadata
import backend.models.segment  # noqa: F401
import backend.models.rep  # noqa: F401
import backend.models.message  # noqa: F401
import backend.models.problem  # noqa: F401
import backend.models.subscription  # noqa: F401
import backend.models.agent_definition  # noqa: F401
import backend.models.agent_session  # noqa: F401
import backend.models.score  # noqa: F401
import backend.models.penalty  # noqa: F401
import backend.models.corps  # noqa: F401
import backend.models.show  # noqa: F401

from backend.api.app import app, get_db


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _create_run_manifest(root, season_id, corps_id, run_id, status="completed"):
    """Create a run manifest on disk."""
    perf_dir = root / "seasons" / season_id / "performances" / corps_id / run_id
    perf_dir.mkdir(parents=True)
    manifest = {
        "run_id": run_id,
        "show_slug": "demo",
        "corps_id": corps_id,
        "season_id": season_id,
        "started_at": "2026-01-15T10:00:00+00:00",
        "completed_at": "2026-01-15T10:05:00+00:00",
        "status": status,
        "config": {"max_iterations": 30, "timeout": 300},
        "inputs": {"show_dir": "shows/demo", "corps_dir": f"corps/{corps_id}"},
        "outputs": ["output.txt"],
    }
    (perf_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest))
    (perf_dir / "output.txt").write_text("Run output content here.")
    return manifest


def _create_corps_workspace(root, corps_id, history=None):
    """Create a corps workspace on disk."""
    corps_dir = root / "corps" / corps_id
    corps_dir.mkdir(parents=True)
    data = {
        "corps_id": corps_id,
        "display_name": corps_id.replace("-", " ").title(),
        "philosophy": "Test philosophy",
        "state": "active",
    }
    if history:
        data["history"] = history
    (corps_dir / "corps.yaml").write_text(yaml.safe_dump(data))
    (corps_dir / "roster.yaml").write_text(yaml.safe_dump({
        "corps_id": corps_id,
        "assignments": [{"agent_id": "agent-alpha", "role": "brass"}],
    }))


def _create_season(root, season_id):
    """Create a season workspace on disk."""
    season_dir = root / "seasons" / season_id
    season_dir.mkdir(parents=True)
    (season_dir / "season.yaml").write_text(yaml.safe_dump({
        "season_id": season_id,
        "metadata": {"season_id": season_id},
    }))
    (season_dir / "performances").mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Runs endpoints
# ---------------------------------------------------------------------------

class TestGetRuns:
    def test_get_runs_empty(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("DCI_PROJECT_ROOT", str(tmp_path))
        (tmp_path / "seasons").mkdir()
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_runs_with_manifests(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("DCI_PROJECT_ROOT", str(tmp_path))
        _create_season(tmp_path, "s1")
        _create_run_manifest(tmp_path, "s1", "bluecoats", "run-001")
        _create_run_manifest(tmp_path, "s1", "cavaliers", "run-002")

        resp = client.get("/api/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        run_ids = {r["run_id"] for r in data}
        assert run_ids == {"run-001", "run-002"}

    def test_get_runs_sorted_by_date(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("DCI_PROJECT_ROOT", str(tmp_path))
        _create_season(tmp_path, "s1")
        m1 = _create_run_manifest(tmp_path, "s1", "bluecoats", "run-early")
        # Modify started_at for second run to be later
        late_dir = tmp_path / "seasons" / "s1" / "performances" / "bluecoats" / "run-late"
        late_dir.mkdir(parents=True)
        (late_dir / "manifest.yaml").write_text(yaml.safe_dump({
            "run_id": "run-late",
            "show_slug": "demo",
            "corps_id": "bluecoats",
            "season_id": "s1",
            "started_at": "2026-02-01T10:00:00+00:00",
            "status": "completed",
            "config": {},
        }))

        resp = client.get("/api/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["run_id"] == "run-late"  # most recent first


class TestGetRunDetail:
    def test_get_run_detail(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("DCI_PROJECT_ROOT", str(tmp_path))
        _create_season(tmp_path, "s1")
        _create_run_manifest(tmp_path, "s1", "bluecoats", "run-001")

        resp = client.get("/api/runs/run-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == "run-001"
        assert data["corps_id"] == "bluecoats"
        assert data["output"] == "Run output content here."

    def test_get_run_detail_not_found(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("DCI_PROJECT_ROOT", str(tmp_path))
        (tmp_path / "seasons").mkdir()
        resp = client.get("/api/runs/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Corps workspace endpoints
# ---------------------------------------------------------------------------

class TestCorpsHistory:
    def test_get_corps_history(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("DCI_PROJECT_ROOT", str(tmp_path))
        _create_corps_workspace(tmp_path, "bluecoats", history=[
            {"season_id": "s1", "placement": 1, "final_score": 85.5, "notes": "show:demo"},
            {"season_id": "s2", "placement": 2, "final_score": 78.0, "notes": "show:finals"},
        ])

        resp = client.get("/api/corps-workspace/bluecoats/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["season_id"] == "s1"
        assert data[0]["placement"] == 1

    def test_get_corps_history_no_history(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("DCI_PROJECT_ROOT", str(tmp_path))
        _create_corps_workspace(tmp_path, "bluecoats")

        resp = client.get("/api/corps-workspace/bluecoats/history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_corps_history_not_found(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("DCI_PROJECT_ROOT", str(tmp_path))
        (tmp_path / "corps").mkdir()
        resp = client.get("/api/corps-workspace/nonexistent/history")
        assert resp.status_code == 404


class TestCorpsWorkspaceList:
    def test_list_corps_workspaces(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("DCI_PROJECT_ROOT", str(tmp_path))
        _create_corps_workspace(tmp_path, "bluecoats")
        _create_corps_workspace(tmp_path, "cavaliers")

        resp = client.get("/api/corps-workspace")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        ids = {c["corps_id"] for c in data}
        assert ids == {"bluecoats", "cavaliers"}

    def test_list_corps_workspaces_empty(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("DCI_PROJECT_ROOT", str(tmp_path))
        (tmp_path / "corps").mkdir()
        resp = client.get("/api/corps-workspace")
        assert resp.status_code == 200
        assert resp.json() == []
