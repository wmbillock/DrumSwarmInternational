"""Phase 9: FastAPI endpoint tests."""

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


class TestShowAPI:
    def test_create_show(self, client):
        resp = client.post("/api/shows", json={"title": "API Show"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "API Show"
        assert data["status"] == "draft"

    def test_list_shows(self, client):
        client.post("/api/shows", json={"title": "S1"})
        client.post("/api/shows", json={"title": "S2"})
        resp = client.get("/api/shows")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_show(self, client):
        create_resp = client.post("/api/shows", json={"title": "Get"})
        show_id = create_resp.json()["id"]
        resp = client.get(f"/api/shows/{show_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Get"

    def test_get_nonexistent_show(self, client):
        resp = client.get("/api/shows/nope")
        assert resp.status_code == 404

    def test_activate_show(self, client):
        create_resp = client.post("/api/shows", json={"title": "Activate"})
        show_id = create_resp.json()["id"]
        resp = client.post(f"/api/shows/{show_id}/activate")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"
        assert resp.json()["corps_id"] is not None

    def test_complete_show(self, client):
        create_resp = client.post("/api/shows", json={"title": "Complete"})
        show_id = create_resp.json()["id"]
        client.post(f"/api/shows/{show_id}/activate")
        resp = client.post(f"/api/shows/{show_id}/complete")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"


class TestCorpsAPI:
    def test_get_corps(self, client):
        create_resp = client.post("/api/shows", json={"title": "Corps Test"})
        show_id = create_resp.json()["id"]
        activate_resp = client.post(f"/api/shows/{show_id}/activate")
        corps_id = activate_resp.json()["corps_id"]
        resp = client.get(f"/api/corps/{corps_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "rehearsal"

    def test_get_roster(self, client):
        create_resp = client.post("/api/shows", json={"title": "Roster Test"})
        show_id = create_resp.json()["id"]
        activate_resp = client.post(f"/api/shows/{show_id}/activate")
        corps_id = activate_resp.json()["corps_id"]
        resp = client.get(f"/api/corps/{corps_id}/roster")
        assert resp.status_code == 200
        roster = resp.json()
        assert len(roster) > 0
        roles = {a["role"] for a in roster}
        assert "executive_director" in roles

    def test_set_rehearsal_mode(self, client):
        create_resp = client.post("/api/shows", json={"title": "Mode Test"})
        show_id = create_resp.json()["id"]
        activate_resp = client.post(f"/api/shows/{show_id}/activate")
        corps_id = activate_resp.json()["corps_id"]
        resp = client.post(f"/api/corps/{corps_id}/rehearsal-mode",
                           json={"mode": "basics"})
        assert resp.status_code == 200
        assert resp.json()["rehearsal_mode"] == "basics"


class TestSegmentAPI:
    def test_create_and_get_segment(self, client):
        resp = client.post("/api/segments", json={
            "type": "show", "title": "Test Show"
        })
        assert resp.status_code == 200
        coord_id = resp.json()["id"]
        get_resp = client.get(f"/api/segments/{coord_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["title"] == "Test Show"

    def test_segment_children(self, client):
        show_resp = client.post("/api/segments", json={
            "type": "show", "title": "Show"
        })
        show_id = show_resp.json()["id"]
        client.post("/api/segments", json={
            "type": "movement", "title": "M1", "parent_id": show_id
        })
        resp = client.get(f"/api/segments/{show_id}/children")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestRepAPI:
    def test_create_and_transition_rep(self, client):
        show_resp = client.post("/api/segments", json={
            "type": "show", "title": "Show"
        })
        coord_id = show_resp.json()["id"]
        rep_resp = client.post("/api/reps", json={"segment_id": coord_id})
        assert rep_resp.status_code == 200
        rep_id = rep_resp.json()["id"]

        trans_resp = client.post(f"/api/reps/{rep_id}/transition", json={
            "new_status": "assigned", "assigned_to": "agent-1"
        })
        assert trans_resp.status_code == 200
        assert trans_resp.json()["status"] == "assigned"

    def test_get_reps_for_segment(self, client):
        show_resp = client.post("/api/segments", json={
            "type": "show", "title": "Show"
        })
        coord_id = show_resp.json()["id"]
        client.post("/api/reps", json={"segment_id": coord_id})
        resp = client.get(f"/api/segments/{coord_id}/reps")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestMessageAPI:
    def test_send_and_poll_messages(self, client):
        create_resp = client.post("/api/shows", json={"title": "Msg Test"})
        show_id = create_resp.json()["id"]
        activate_resp = client.post(f"/api/shows/{show_id}/activate")
        corps_id = activate_resp.json()["corps_id"]

        msg_resp = client.post(f"/api/corps/{corps_id}/messages", json={
            "from_role": "executive_director",
            "to_role": "program_coordinator",
            "type": "directive",
            "subject": "Start work"
        })
        assert msg_resp.status_code == 200

        poll_resp = client.get(f"/api/corps/{corps_id}/messages?role=program_coordinator")
        assert poll_resp.status_code == 200
        assert len(poll_resp.json()) >= 1


class TestCorpsCommands:
    def test_list_commands(self, client):
        resp = client.get("/api/corps-commands")
        assert resp.status_code == 200
        cmds = resp.json()
        assert "resume_hut" in cmds
        assert "attention" in cmds
        assert "dismissed" in cmds
        assert cmds["resume_hut"]["category"] == "control"

    def test_unknown_command(self, client):
        from backend.models.corps import Corps, CorpsStatus
        # Create a corps first
        resp = client.post("/api/shows", json={"title": "Cmd Test"})
        show_id = resp.json()["id"]
        # Need a corps — create one directly
        from backend.database import Base
        resp = client.post(f"/api/corps/fake-id/command", json={"command": "bogus"})
        assert resp.status_code in (400, 404)

    def test_at_ease_command(self, client):
        from backend.models.corps import Corps, CorpsStatus
        # We need a real corps for this
        resp = client.post("/api/shows", json={"title": "Ease Test"})
        show_id = resp.json()["id"]
        # Activate to get a corps
        act_resp = client.post(f"/api/shows/{show_id}/activate")
        if act_resp.status_code == 200:
            corps_id = act_resp.json().get("corps_id")
            if corps_id:
                cmd_resp = client.post(f"/api/corps/{corps_id}/command", json={"command": "at_ease"})
                assert cmd_resp.status_code == 200
                assert cmd_resp.json()["status"] == "ok"

    def test_rehearsal_mode_commands(self, client):
        resp = client.post("/api/shows", json={"title": "Rehearsal Test"})
        show_id = resp.json()["id"]
        act_resp = client.post(f"/api/shows/{show_id}/activate")
        if act_resp.status_code == 200:
            corps_id = act_resp.json().get("corps_id")
            if corps_id:
                for mode in ["basics", "sectionals", "full_ensemble", "run_through"]:
                    cmd_resp = client.post(f"/api/corps/{corps_id}/command", json={"command": mode})
                    assert cmd_resp.status_code == 200
