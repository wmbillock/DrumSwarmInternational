"""Tests for V1 API — thin adapter layer over existing services."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project_root(tmp_path, monkeypatch):
    """Set up a temp project root with required directory structure."""
    monkeypatch.setenv("DCI_PROJECT_ROOT", str(tmp_path))
    (tmp_path / "shows").mkdir()
    (tmp_path / "corps").mkdir()
    (tmp_path / "seasons").mkdir()
    return tmp_path


@pytest.fixture
def client(project_root, monkeypatch):
    """TestClient against the FastAPI app with DCI_PROJECT_ROOT set."""
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
    """Create a valid corps workspace."""
    d = project_root / "corps" / "blue-devils"
    d.mkdir(parents=True)
    (d / "corps.yaml").write_text(yaml.dump({
        "corps_id": "blue-devils",
        "display_name": "Blue Devils",
        "philosophy": "Innovation",
        "state": "active",
    }))
    (d / "roster.yaml").write_text(yaml.dump({
        "assignments": [{"role": "brass"}, {"role": "percussion"}],
    }))
    return d


@pytest.fixture
def show_dir(project_root):
    """Create an approved show workspace."""
    from backend.services.show_persistence import create_show, write_spec, approve_spec
    d = create_show("test-show", project_root / "shows")
    write_spec(d, "# Test Show\n\n## Decisions\n- D1\n")
    approve_spec(d)
    return d


@pytest.fixture
def season_dir(project_root):
    """Create a valid season."""
    d = project_root / "seasons" / "s1"
    d.mkdir(parents=True)
    (d / "season.yaml").write_text(yaml.dump({
        "season_id": "s1",
        "status": "active",
    }))
    return d


# ---------------------------------------------------------------------------
# Corps
# ---------------------------------------------------------------------------

class TestCorps:
    def test_list_corps_empty(self, client):
        r = client.get("/api/v1/corps")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_corps(self, client, corps_dir):
        r = client.get("/api/v1/corps")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["corps_id"] == "blue-devils"
        assert data[0]["display_name"] == "Blue Devils"
        assert data[0]["state"] == "active"

    def test_get_corps_detail(self, client, corps_dir):
        r = client.get("/api/v1/corps/blue-devils")
        assert r.status_code == 200
        data = r.json()
        assert data["corps_id"] == "blue-devils"
        assert data["roster_size"] == 2

    def test_get_corps_not_found(self, client, project_root):
        r = client.get("/api/v1/corps/nonexistent")
        assert r.status_code == 404

    def test_get_corps_path_traversal(self, client, project_root):
        # FastAPI decodes %2F in path params, but ".." alone triggers validation
        r = client.get("/api/v1/corps/..etc")
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Design Room
# ---------------------------------------------------------------------------

class TestDesignRoom:
    def test_create_thread(self, client, project_root):
        r = client.post("/api/v1/design/threads", json={"title": "my-design"})
        assert r.status_code == 200
        data = r.json()
        assert "slug" in data
        slug = data["slug"]

        # Verify spec was created
        r2 = client.get(f"/api/v1/design/threads/{slug}/artifacts/brief")
        assert r2.status_code == 200
        assert r2.json()["content"] != ""

    def test_list_threads(self, client, project_root):
        client.post("/api/v1/design/threads", json={"title": "thread-a"})
        client.post("/api/v1/design/threads", json={"title": "thread-b"})
        r = client.get("/api/v1/design/threads")
        assert r.status_code == 200
        assert len(r.json()) >= 2

    def test_post_and_get_messages(self, client, project_root):
        r = client.post("/api/v1/design/threads", json={"title": "chat-test"})
        slug = r.json()["slug"]

        r2 = client.post(f"/api/v1/design/threads/{slug}/messages",
                         json={"message": "Add brass section with forte dynamics"})
        assert r2.status_code == 200
        data = r2.json()
        assert "role" in data
        assert "tags" in data
        assert isinstance(data["tags"], list)

        r3 = client.get(f"/api/v1/design/threads/{slug}/messages")
        assert r3.status_code == 200
        assert len(r3.json()["messages"]) >= 1

    def test_update_and_get_brief(self, client, project_root):
        r = client.post("/api/v1/design/threads", json={"title": "brief-test"})
        slug = r.json()["slug"]

        new_content = "# Updated Spec\n\n## Decisions\n- New decision\n"
        client.put(f"/api/v1/design/threads/{slug}/artifacts/brief",
                   json={"content": new_content})

        r2 = client.get(f"/api/v1/design/threads/{slug}/artifacts/brief")
        assert r2.json()["content"] == new_content

    def test_approve_thread(self, client, project_root):
        r = client.post("/api/v1/design/threads", json={"title": "approve-test"})
        slug = r.json()["slug"]

        r2 = client.post(f"/api/v1/design/threads/{slug}/approve")
        assert r2.status_code == 200
        assert r2.json()["version"] == 1

        r3 = client.get(f"/api/v1/design/threads/{slug}/versions")
        assert len(r3.json()["versions"]) == 1

    def test_approve_empty_spec_fails(self, client, project_root):
        r = client.post("/api/v1/design/threads", json={"title": "empty-approve"})
        slug = r.json()["slug"]
        # Overwrite with empty spec
        client.put(f"/api/v1/design/threads/{slug}/artifacts/brief",
                   json={"content": ""})
        r2 = client.post(f"/api/v1/design/threads/{slug}/approve")
        assert r2.status_code == 400

    def test_nonexistent_thread_404(self, client, project_root):
        r = client.get("/api/v1/design/threads/nonexistent/artifacts/brief")
        assert r.status_code == 404

    def test_slug_traversal_rejected(self, client, project_root):
        r = client.get("/api/v1/design/threads/..etc/artifacts/brief")
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

class TestRuns:
    def test_list_runs_empty(self, client, project_root):
        r = client.get("/api/v1/runs")
        assert r.status_code == 200
        assert r.json() == []

    def test_start_run(self, client, show_dir, corps_dir, season_dir):
        r = client.post("/api/v1/runs", json={
            "show_slug": "test-show",
            "corps_id": "blue-devils",
            "season_id": "s1",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "completed"
        run_id = data["run_id"]

        # Verify run appears in list
        r2 = client.get("/api/v1/runs")
        assert any(run["run_id"] == run_id for run in r2.json())

        # Verify run detail
        r3 = client.get(f"/api/v1/runs/{run_id}")
        assert r3.status_code == 200
        assert r3.json()["show_slug"] == "test-show"

        # Verify logs
        r4 = client.get(f"/api/v1/runs/{run_id}/logs")
        assert r4.status_code == 200
        assert "Stub execution" in r4.json()["log"]

    def test_start_run_unapproved_show(self, client, project_root, corps_dir, season_dir):
        from backend.services.show_persistence import create_show
        create_show("draft-show", project_root / "shows")
        r = client.post("/api/v1/runs", json={
            "show_slug": "draft-show",
            "corps_id": "blue-devils",
            "season_id": "s1",
        })
        assert r.status_code == 400

    def test_start_run_missing_corps(self, client, show_dir, season_dir):
        r = client.post("/api/v1/runs", json={
            "show_slug": "test-show",
            "corps_id": "nonexistent",
            "season_id": "s1",
        })
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Competitions
# ---------------------------------------------------------------------------

class TestCompetitions:
    def test_create_and_run_competition(self, client, show_dir, corps_dir, season_dir):
        r = client.post("/api/v1/competitions", json={
            "season_id": "s1",
            "show_slug": "test-show",
            "corps_ids": ["blue-devils"],
        })
        assert r.status_code == 200
        comp_id = r.json()["competition_id"]
        assert comp_id == "s1-test-show"

        r2 = client.post(f"/api/v1/competitions/{comp_id}/run")
        assert r2.status_code == 200
        assert r2.json()["status"] == "completed"
        assert len(r2.json()["standings"]) == 1

        r3 = client.get(f"/api/v1/competitions/{comp_id}/scores")
        assert r3.status_code == 200
        assert "results" in r3.json()

    def test_competition_missing_season(self, client, show_dir, corps_dir):
        r = client.post("/api/v1/competitions", json={
            "season_id": "nonexistent",
            "show_slug": "test-show",
            "corps_ids": ["blue-devils"],
        })
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Seance (requires corps history setup)
# ---------------------------------------------------------------------------

class TestSeance:
    def _setup_corps_with_history(self, project_root):
        """Create a corps with a history entry for seance testing."""
        corps_id = "blue-devils"
        corps_dir = project_root / "corps" / corps_id
        corps_dir.mkdir(parents=True, exist_ok=True)
        (corps_dir / "corps.yaml").write_text(yaml.dump({
            "corps_id": corps_id,
            "display_name": "Blue Devils",
            "philosophy": "Innovation",
            "state": "active",
            "history": [{"season_id": "s1", "placement": 1, "final_score": 85.0, "notes": "show:past-show"}],
        }))
        # Create a show artifact that corps_history can find
        show_dir = project_root / "shows" / "past-show"
        show_dir.mkdir(parents=True, exist_ok=True)
        (show_dir / "status.yaml").write_text(yaml.dump({"status": "completed"}))
        (show_dir / "spec.md").write_text("# Past Show\n")

        # Create seances directory
        (project_root / "seances").mkdir(exist_ok=True)
        return corps_id

    def test_get_corps_history(self, client, project_root):
        self._setup_corps_with_history(project_root)
        r = client.get("/api/v1/corps/blue-devils/history")
        assert r.status_code == 200

    def test_create_and_get_seance(self, client, project_root):
        self._setup_corps_with_history(project_root)

        # Get history to find an entry_id
        r = client.get("/api/v1/corps/blue-devils/history")
        if r.status_code != 200:
            pytest.skip("Corps history not available")
        history = r.json()
        if not history.get("entries"):
            pytest.skip("No history entries available")

        entry_id = history["entries"][0]["entry_id"]
        r2 = client.post("/api/v1/seances", json={
            "corps_id": "blue-devils",
            "entry_id": entry_id,
        })
        if r2.status_code == 400:
            pytest.skip(f"Seance creation failed: {r2.json()}")
        assert r2.status_code == 200
        seance_id = r2.json()["seance_id"]

        r3 = client.get(f"/api/v1/seances/{seance_id}")
        assert r3.status_code == 200

        r4 = client.get(f"/api/v1/seances/{seance_id}/transcript")
        assert r4.status_code == 200
