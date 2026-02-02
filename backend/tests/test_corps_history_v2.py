"""Tests for corps history v2 endpoints — DB fallback, cleanup, artifact-preview, list-corps-seances."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml
from fastapi.testclient import TestClient


@pytest.fixture
def project_root(tmp_path):
    """Create minimal project structure."""
    corps_dir = tmp_path / "corps" / "test-corps"
    corps_dir.mkdir(parents=True)
    (corps_dir / "corps.yaml").write_text(yaml.dump({
        "corps_id": "test-corps",
        "display_name": "Test Corps",
        "philosophy": "Testing",
        "state": "on_tour",
    }))
    (tmp_path / "seances").mkdir()
    return tmp_path


@pytest.fixture
def client(project_root):
    os.environ["DCI_PROJECT_ROOT"] = str(project_root)
    from backend.api.v1.corps import router as corps_router
    from backend.api.v1.seances import router as seances_router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(corps_router)
    app.include_router(seances_router)
    yield TestClient(app)
    os.environ.pop("DCI_PROJECT_ROOT", None)


def test_list_corps_includes_filesystem(client):
    resp = client.get("/api/v1/corps")
    assert resp.status_code == 200
    data = resp.json()
    assert any(c["corps_id"] == "test-corps" for c in data)


def test_get_corps_filesystem(client):
    resp = client.get("/api/v1/corps/test-corps")
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Test Corps"


def test_get_corps_unknown_returns_404(client):
    resp = client.get("/api/v1/corps/nonexistent-corps")
    assert resp.status_code == 404


def test_get_corps_history_filesystem(client, project_root):
    # Create history index
    history_dir = project_root / "corps" / "test-corps" / "history"
    history_dir.mkdir()
    (history_dir / "index.yaml").write_text(yaml.dump({
        "corps_id": "test-corps",
        "generated_at": "2025-01-01T00:00:00Z",
        "entries": [],
    }))
    resp = client.get("/api/v1/corps/test-corps/history")
    assert resp.status_code == 200


def test_list_corps_seances_empty(client):
    resp = client.get("/api/v1/corps/test-corps/seances")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_corps_seances_finds_matching(client, project_root):
    seance_dir = project_root / "seances" / "s1"
    seance_dir.mkdir(parents=True)
    (seance_dir / "session.yaml").write_text(yaml.dump({
        "seance_id": "s1",
        "corps_id": "test-corps",
        "entry_id": "e1",
        "season_id": "2025",
        "status": "active",
        "created_at": "2025-01-01T00:00:00Z",
        "context_binder": [],
    }))
    resp = client.get("/api/v1/corps/test-corps/seances")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["seance_id"] == "s1"


def test_artifact_preview_requires_binder_path(client, project_root):
    # Create a seance with binder
    seance_dir = project_root / "seances" / "s2"
    seance_dir.mkdir(parents=True)
    (seance_dir / "session.yaml").write_text(yaml.dump({
        "seance_id": "s2",
        "corps_id": "test-corps",
        "entry_id": "e1",
        "status": "active",
        "context_binder": [{"path": "corps/test-corps/corps.yaml", "type": "yaml", "loaded": True}],
    }))
    # Path not in binder
    resp = client.get("/api/v1/seances/s2/artifact-preview?path=secret.txt")
    assert resp.status_code == 403

    # Path in binder
    resp = client.get("/api/v1/seances/s2/artifact-preview?path=corps/test-corps/corps.yaml")
    assert resp.status_code == 200
    assert "Test Corps" in resp.json()["content"]
