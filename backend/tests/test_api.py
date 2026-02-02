"""Phase 9: FastAPI endpoint tests — V1 API."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base

# Import all models BEFORE app to ensure Base.metadata is populated
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
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DCI_PROJECT_ROOT", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "shows").mkdir()
    (tmp_path / "corps").mkdir()
    (tmp_path / "seasons").mkdir()

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
    monkeypatch.setattr("backend.api.app.SessionFactory", TestingSession)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _create_corps(client) -> str:
    """Helper: create a corps via V1 API and return its corps_id."""
    resp = client.post("/api/v1/corps", json={"name": f"Test Corps {id(client)}"})
    assert resp.status_code == 200
    return resp.json()["corps_id"]


class TestShowAPI:
    def test_create_show(self, client):
        resp = client.post("/api/v1/shows", json={"title": "API Show"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "API Show"
        assert data["status"] == "draft"
        assert "slug" in data

    def test_list_shows(self, client):
        client.post("/api/v1/shows", json={"title": "S1"})
        client.post("/api/v1/shows", json={"title": "S2"})
        resp = client.get("/api/v1/shows")
        assert resp.status_code == 200
        shows = resp.json()
        slugs = {s.get("slug") for s in shows}
        assert "s1" in slugs
        assert "s2" in slugs

    def test_get_show(self, client):
        create_resp = client.post("/api/v1/shows", json={"title": "Get"})
        slug = create_resp.json()["slug"]
        resp = client.get(f"/api/v1/shows/{slug}/detail")
        assert resp.status_code == 200
        assert resp.json()["slug"] == slug

    def test_get_nonexistent_show(self, client):
        resp = client.get("/api/v1/shows/nope/detail")
        assert resp.status_code == 404

    def test_activate_show(self, client):
        create_resp = client.post("/api/v1/shows", json={"title": "Activate"})
        slug = create_resp.json()["slug"]
        resp = client.post(f"/api/v1/shows/{slug}/activate")
        assert resp.status_code == 200
        assert resp.json()["status"] == "activated"
        assert resp.json()["slug"] == slug

    def test_complete_show(self, client):
        create_resp = client.post("/api/v1/shows", json={"title": "Complete"})
        slug = create_resp.json()["slug"]
        client.post(f"/api/v1/shows/{slug}/activate")
        resp = client.post(f"/api/v1/shows/{slug}/complete")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"


class TestCorpsAPI:
    def test_get_corps(self, client):
        corps_id = _create_corps(client)
        resp = client.get(f"/api/v1/corps/{corps_id}")
        assert resp.status_code == 200
        assert resp.json()["state"] == "winter_camps"

    def test_get_roster(self, client):
        corps_id = _create_corps(client)
        resp = client.get(f"/api/v1/corps/{corps_id}/roster")
        assert resp.status_code == 200
        # DB-created corps won't have agent sessions, so roster may be empty
        assert isinstance(resp.json(), list)

    def test_set_rehearsal_mode(self, client):
        corps_id = _create_corps(client)
        resp = client.post(f"/api/v1/corps/{corps_id}/rehearsal-mode",
                           json={"mode": "basics"})
        assert resp.status_code == 200
        assert resp.json()["rehearsal_mode"] == "basics"


class TestSegmentAPI:
    def test_create_and_get_segment(self, client):
        resp = client.post("/api/v1/segments", json={
            "type": "show", "title": "Test Show"
        })
        assert resp.status_code == 200
        coord_id = resp.json()["id"]
        get_resp = client.get(f"/api/v1/segments/{coord_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["title"] == "Test Show"

    def test_segment_children(self, client):
        show_resp = client.post("/api/v1/segments", json={
            "type": "show", "title": "Show"
        })
        show_id = show_resp.json()["id"]
        client.post("/api/v1/segments", json={
            "type": "movement", "title": "M1", "parent_id": show_id
        })
        resp = client.get(f"/api/v1/segments/{show_id}/children")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestRepAPI:
    def test_create_and_transition_rep(self, client):
        show_resp = client.post("/api/v1/segments", json={
            "type": "show", "title": "Show"
        })
        coord_id = show_resp.json()["id"]
        rep_resp = client.post("/api/v1/reps", json={"segment_id": coord_id})
        assert rep_resp.status_code == 200
        rep_id = rep_resp.json()["id"]

        trans_resp = client.post(f"/api/v1/reps/{rep_id}/transition", json={
            "new_status": "assigned", "assigned_to": "agent-1"
        })
        assert trans_resp.status_code == 200
        assert trans_resp.json()["status"] == "assigned"

    def test_get_reps_for_segment(self, client):
        show_resp = client.post("/api/v1/segments", json={
            "type": "show", "title": "Show"
        })
        coord_id = show_resp.json()["id"]
        client.post("/api/v1/reps", json={"segment_id": coord_id})
        resp = client.get(f"/api/v1/segments/{coord_id}/reps")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestMessageAPI:
    def test_send_and_poll_messages(self, client):
        corps_id = _create_corps(client)

        msg_resp = client.post(f"/api/v1/corps/{corps_id}/messages", json={
            "from_role": "executive_director",
            "to_role": "program_coordinator",
            "type": "directive",
            "subject": "Start work",
            "priority": "normal"
        })
        assert msg_resp.status_code == 200

        poll_resp = client.get(f"/api/v1/corps/{corps_id}/messages/poll")
        assert poll_resp.status_code == 200
        assert len(poll_resp.json()) >= 1


class TestCorpsCommands:
    def test_list_commands(self, client):
        resp = client.get("/api/v1/corps-commands")
        assert resp.status_code == 200
        cmds = resp.json()
        assert "resume_hut" in cmds
        assert "attention" in cmds
        assert "dismissed" in cmds
        assert cmds["resume_hut"]["category"] == "control"

    def test_unknown_command(self, client):
        resp = client.post("/api/v1/corps/fake-id/command", json={"command": "bogus"})
        assert resp.status_code in (400, 404)

    def test_at_ease_command(self, client):
        corps_id = _create_corps(client)
        cmd_resp = client.post(f"/api/v1/corps/{corps_id}/command", json={"command": "at_ease"})
        assert cmd_resp.status_code == 200
        assert cmd_resp.json()["status"] == "ok"

    def test_rehearsal_mode_commands(self, client):
        corps_id = _create_corps(client)
        for mode in ["basics", "sectionals", "full_ensemble", "run_through"]:
            cmd_resp = client.post(f"/api/v1/corps/{corps_id}/command", json={"command": mode})
            assert cmd_resp.status_code == 200
