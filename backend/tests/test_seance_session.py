"""TDD tests for seance sessions anchored to corps history entries."""

import yaml
from pathlib import Path

import pytest

from backend.services.seance_session import (
    create_session,
    load_session,
    append_transcript,
    read_transcript,
    assemble_context,
    close_session,
)


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, default_flow_style=False, sort_keys=False))


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _make_corps_with_index(tmp_path: Path, corps_id: str = "cavaliers") -> None:
    """Create a corps with one history entry and a built index, plus artifacts on disk."""
    _write_yaml(tmp_path / "corps" / corps_id / "corps.yaml", {
        "corps_id": corps_id,
        "display_name": corps_id.title(),
        "philosophy": "",
        "state": "active",
        "history": [
            {"season_id": "s1", "placement": 1, "final_score": 85.0, "notes": "show:my-show"},
        ],
    })
    # Season-level artifacts
    _write_yaml(tmp_path / "seasons" / "s1" / "standings.yaml", {
        "season_id": "s1",
        "results": [{"corps_id": corps_id, "rank": 1, "final_score": 85.0}],
    })
    _write_yaml(tmp_path / "seasons" / "s1" / "performances" / corps_id / "scores.yaml", {
        "corps_id": corps_id,
        "caption_scores": {"brass": 80, "percussion": 90},
    })
    # Show-level artifacts
    _write_yaml(tmp_path / "shows" / "my-show" / "status.yaml", {"status": "approved"})
    _write_text(tmp_path / "shows" / "my-show" / "design_notes.md", "# Design Notes\nBrass feature in movement 2.")
    _write_text(tmp_path / "shows" / "my-show" / "show_prompt.md", "")  # empty = not loaded

    # Build index
    from backend.services.corps_history import build_history_index
    build_history_index(tmp_path, corps_id)


# ---------------------------------------------------------------------------
# Session Creation
# ---------------------------------------------------------------------------

class TestCreateSession:
    def test_create_session_from_history_entry(self, tmp_path):
        _make_corps_with_index(tmp_path)

        session = create_session(tmp_path, "cavaliers", "cavaliers-s1")

        assert session["corps_id"] == "cavaliers"
        assert session["entry_id"] == "cavaliers-s1"
        assert session["season_id"] == "s1"
        assert session["show_slug"] == "my-show"
        assert session["status"] == "active"
        assert session["participant"] == "executive_director"
        assert "seance_id" in session
        assert "created_at" in session

        # Context binder populated
        binder = session["context_binder"]
        assert len(binder) > 0
        types = {item["type"] for item in binder}
        assert "standings" in types
        assert "corps_scores" in types

    def test_create_session_writes_session_yaml(self, tmp_path):
        _make_corps_with_index(tmp_path)

        session = create_session(tmp_path, "cavaliers", "cavaliers-s1")
        sid = session["seance_id"]

        session_path = tmp_path / "seances" / sid / "session.yaml"
        assert session_path.exists()
        data = yaml.safe_load(session_path.read_text())
        assert data["seance_id"] == sid
        assert data["corps_id"] == "cavaliers"
        assert data["status"] == "active"

    def test_create_session_writes_empty_transcript(self, tmp_path):
        _make_corps_with_index(tmp_path)

        session = create_session(tmp_path, "cavaliers", "cavaliers-s1")
        sid = session["seance_id"]

        transcript_path = tmp_path / "seances" / sid / "transcript.md"
        assert transcript_path.exists()
        content = transcript_path.read_text()
        # Header comment present, no conversation yet
        assert "seance:" in content
        assert "cavaliers" in content

    def test_create_session_binder_loaded_flags(self, tmp_path):
        _make_corps_with_index(tmp_path)

        session = create_session(tmp_path, "cavaliers", "cavaliers-s1")
        binder = session["context_binder"]

        loaded_map = {item["type"]: item["loaded"] for item in binder}
        # standings and corps_scores exist and are non-empty
        assert loaded_map["standings"] is True
        assert loaded_map["corps_scores"] is True
        # design_notes exists and is non-empty
        assert loaded_map["design_notes"] is True
        # show_prompt exists but is empty
        assert loaded_map["show_prompt"] is False

    def test_create_session_refuses_missing_standings(self, tmp_path):
        """Standings is required — without it, no performance record to discuss."""
        _write_yaml(tmp_path / "corps" / "cavaliers" / "corps.yaml", {
            "corps_id": "cavaliers", "display_name": "Cavaliers",
            "philosophy": "", "state": "active",
            "history": [{"season_id": "s1", "placement": 1, "final_score": 80.0, "notes": ""}],
        })
        # No standings on disk — only build an index (which will have empty artifacts)
        from backend.services.corps_history import build_history_index
        build_history_index(tmp_path, "cavaliers")

        with pytest.raises(ValueError, match="Required artifact missing: standings"):
            create_session(tmp_path, "cavaliers", "cavaliers-s1")

    def test_create_session_allows_missing_optional_artifacts(self, tmp_path):
        """design_notes, show_prompt, show_status are optional."""
        _write_yaml(tmp_path / "corps" / "cavaliers" / "corps.yaml", {
            "corps_id": "cavaliers", "display_name": "Cavaliers",
            "philosophy": "", "state": "active",
            "history": [{"season_id": "s1", "placement": 1, "final_score": 80.0, "notes": "show:missing-show"}],
        })
        _write_yaml(tmp_path / "seasons" / "s1" / "standings.yaml", {"season_id": "s1", "results": []})
        _write_yaml(tmp_path / "seasons" / "s1" / "performances" / "cavaliers" / "scores.yaml", {"corps_id": "cavaliers"})
        from backend.services.corps_history import build_history_index
        build_history_index(tmp_path, "cavaliers")

        session = create_session(tmp_path, "cavaliers", "cavaliers-s1")
        types = {item["type"] for item in session["context_binder"]}
        assert "standings" in types
        assert "corps_scores" in types
        # No show-level artifacts
        assert "design_notes" not in types
        assert "show_prompt" not in types

    def test_create_session_nonexistent_entry_raises(self, tmp_path):
        _make_corps_with_index(tmp_path)

        with pytest.raises(ValueError, match="not found"):
            create_session(tmp_path, "cavaliers", "cavaliers-nope")


# ---------------------------------------------------------------------------
# Session Operations
# ---------------------------------------------------------------------------

class TestSessionOperations:
    def test_load_session(self, tmp_path):
        _make_corps_with_index(tmp_path)
        session = create_session(tmp_path, "cavaliers", "cavaliers-s1")
        sid = session["seance_id"]

        loaded = load_session(tmp_path, sid)
        assert loaded["seance_id"] == sid
        assert loaded["corps_id"] == "cavaliers"

    def test_append_and_read_transcript(self, tmp_path):
        _make_corps_with_index(tmp_path)
        session = create_session(tmp_path, "cavaliers", "cavaliers-s1")
        sid = session["seance_id"]

        append_transcript(tmp_path, sid, "user", "What went well?")
        append_transcript(tmp_path, sid, "executive_director", "Brass was strong.")

        transcript = read_transcript(tmp_path, sid)
        assert "**[user]** What went well?" in transcript
        assert "**[executive_director]** Brass was strong." in transcript

    def test_assemble_context_reads_artifacts(self, tmp_path):
        _make_corps_with_index(tmp_path)
        session = create_session(tmp_path, "cavaliers", "cavaliers-s1")

        context = assemble_context(tmp_path, session)

        # Should contain standings content
        assert "season_id" in context or "s1" in context
        # Should contain design notes content
        assert "Design Notes" in context
        # Should NOT contain show_prompt (empty file)
        # Context should have type headers
        assert "standings" in context.lower()

    def test_assemble_context_deterministic(self, tmp_path):
        """Two calls with same session produce identical output."""
        _make_corps_with_index(tmp_path)
        session = create_session(tmp_path, "cavaliers", "cavaliers-s1")

        c1 = assemble_context(tmp_path, session)
        c2 = assemble_context(tmp_path, session)
        assert c1 == c2

    def test_close_session_sets_status(self, tmp_path):
        _make_corps_with_index(tmp_path)
        session = create_session(tmp_path, "cavaliers", "cavaliers-s1")
        sid = session["seance_id"]

        close_session(tmp_path, sid)

        loaded = load_session(tmp_path, sid)
        assert loaded["status"] == "closed"


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

class TestSecurity:
    def test_seance_id_no_path_traversal(self, tmp_path):
        with pytest.raises(ValueError, match="traversal"):
            load_session(tmp_path, "../etc/passwd")

    def test_seance_id_no_path_traversal_append(self, tmp_path):
        with pytest.raises(ValueError, match="traversal"):
            append_transcript(tmp_path, "../../evil", "user", "hi")

    def test_seance_id_no_path_traversal_read(self, tmp_path):
        with pytest.raises(ValueError, match="traversal"):
            read_transcript(tmp_path, "../secret")

    def test_seance_id_no_path_traversal_close(self, tmp_path):
        with pytest.raises(ValueError, match="traversal"):
            close_session(tmp_path, "foo/../bar")
