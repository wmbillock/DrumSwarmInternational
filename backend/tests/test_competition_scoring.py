"""Tests for competition scoring — breakdown endpoint, score shape, placement recording."""

import os
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient


@pytest.fixture
def project_root(tmp_path, monkeypatch):
    monkeypatch.setenv("DCI_PROJECT_ROOT", str(tmp_path))
    (tmp_path / "shows").mkdir()
    (tmp_path / "corps").mkdir()
    (tmp_path / "seasons").mkdir()
    return tmp_path


@pytest.fixture
def client(project_root, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from backend.database import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSessionFactory = sessionmaker(bind=engine)

    monkeypatch.setattr("backend.api.app.SessionFactory", TestSessionFactory)

    from backend.api.app import app
    return TestClient(app)


@pytest.fixture
def corps_dir(project_root):
    for name in ["alpha", "bravo"]:
        d = project_root / "corps" / name
        d.mkdir(parents=True)
        (d / "corps.yaml").write_text(yaml.dump({
            "corps_id": name,
            "display_name": name.capitalize(),
            "philosophy": "test",
            "state": "active",
            "history": [],
        }))
        (d / "roster.yaml").write_text(yaml.dump({"assignments": []}))
    return project_root / "corps"


@pytest.fixture
def show_dir(project_root):
    from backend.services.show_persistence import create_show, write_spec, approve_spec
    d = create_show("test-show", project_root / "shows")
    write_spec(d, "# Test Show\n\n## Decisions\n- D1\n")
    approve_spec(d)
    return d


@pytest.fixture
def season_dir(project_root):
    d = project_root / "seasons" / "s1"
    d.mkdir(parents=True)
    (d / "season.yaml").write_text(yaml.dump({
        "season_id": "s1",
        "status": "active",
    }))
    return d


@pytest.fixture
def competition(client, corps_dir, show_dir, season_dir):
    """Create and return a competition with two corps."""
    r = client.post("/api/v1/competitions", json={
        "season_id": "s1",
        "show_slug": "test-show",
        "corps_ids": ["alpha", "bravo"],
    })
    assert r.status_code == 200
    return r.json()


class TestRunCompetition:
    def test_run_competition_yields_score_payload(self, client, competition):
        r = client.post("/api/v1/competitions/s1-test-show/run")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "completed"
        assert len(data["standings"]) == 2
        for entry in data["standings"]:
            assert "rank" in entry
            assert "final_score" in entry
            assert "raw_score" in entry
            assert "caption_scores" in entry
            assert isinstance(entry["caption_scores"], dict)
            assert len(entry["caption_scores"]) >= 5

    def test_scores_endpoint_after_run(self, client, competition):
        client.post("/api/v1/competitions/s1-test-show/run")
        r = client.get("/api/v1/competitions/s1-test-show/scores")
        assert r.status_code == 200
        data = r.json()
        assert data["competition_id"] == "s1-test-show"
        assert data["show_slug"] == "test-show"
        assert len(data["results"]) == 2


class TestCorpsBreakdown:
    def test_corps_breakdown_endpoint(self, client, competition):
        client.post("/api/v1/competitions/s1-test-show/run")
        r = client.get("/api/v1/competitions/s1-test-show/corps/alpha/breakdown")
        assert r.status_code == 200
        data = r.json()
        assert data["corps_id"] == "alpha"
        assert "caption_scores" in data
        for cap, detail in data["caption_scores"].items():
            assert "score" in detail
            assert "weight" in detail
            assert "weighted" in detail
        assert "commentary" in data
        assert isinstance(data["commentary"], dict)
        assert data["final_score"] > 0

    def test_breakdown_not_found_before_run(self, client, competition):
        r = client.get("/api/v1/competitions/s1-test-show/corps/alpha/breakdown")
        assert r.status_code == 404


class TestPlacementRecording:
    def test_competition_records_placement(self, client, competition, project_root):
        client.post("/api/v1/competitions/s1-test-show/run")
        corps_yaml = project_root / "corps" / "alpha" / "corps.yaml"
        data = yaml.safe_load(corps_yaml.read_text())
        history = data.get("history", [])
        assert len(history) >= 1
        entry = history[-1]
        assert entry["season_id"] == "s1"
        assert "placement" in entry
        assert "final_score" in entry
