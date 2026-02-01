"""TDD tests for Executive Director retrospective chat grounded in binder artifacts."""

import yaml
from pathlib import Path

import pytest

from backend.services.llm_client import MockLLMClient, LLMResponse, ModelTier
from backend.services.ed_chat import build_ed_prompt, ed_respond, STRICT_PREAMBLE, RELAXED_PREAMBLE


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, default_flow_style=False, sort_keys=False))


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _make_session(tmp_path: Path, corps_id: str = "cavaliers") -> dict:
    """Create a corps with history, build index, create seance, return session."""
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
        "results": [
            {"corps_id": corps_id, "rank": 1, "final_score": 85.0,
             "caption_scores": {"brass": 80, "percussion": 90, "guard": 78, "visual": 82, "general_effect": 95}},
        ],
    })
    _write_yaml(tmp_path / "seasons" / "s1" / "performances" / corps_id / "scores.yaml", {
        "corps_id": corps_id,
        "caption_scores": {"brass": 80, "percussion": 90, "guard": 78, "visual": 82, "general_effect": 95},
        "final_score": 85.0,
    })
    _write_yaml(tmp_path / "shows" / "my-show" / "status.yaml", {"status": "approved"})
    _write_text(tmp_path / "shows" / "my-show" / "design_notes.md",
                "# Design Notes\nMovement 2 features a brass chorale with dynamic contrast.")

    from backend.services.corps_history import build_history_index
    build_history_index(tmp_path, corps_id)

    from backend.services.seance_session import create_session
    return create_session(tmp_path, corps_id, f"{corps_id}-s1")


# ---------------------------------------------------------------------------
# Prompt Building
# ---------------------------------------------------------------------------

class TestBuildPrompt:
    def test_prompt_contains_artifact_content(self, tmp_path):
        session = _make_session(tmp_path)
        prompt = build_ed_prompt(tmp_path, session, mode="strict")

        # Should include standings data
        assert "brass" in prompt
        assert "80" in prompt
        # Should include design notes
        assert "brass chorale" in prompt

    def test_prompt_contains_binder_manifest(self, tmp_path):
        session = _make_session(tmp_path)
        prompt = build_ed_prompt(tmp_path, session, mode="strict")

        # Should list artifact types
        assert "standings" in prompt
        assert "corps_scores" in prompt

    def test_strict_mode_includes_strict_rules(self, tmp_path):
        session = _make_session(tmp_path)
        prompt = build_ed_prompt(tmp_path, session, mode="strict")
        assert STRICT_PREAMBLE in prompt

    def test_relaxed_mode_includes_relaxed_rules(self, tmp_path):
        session = _make_session(tmp_path)
        prompt = build_ed_prompt(tmp_path, session, mode="relaxed")
        assert RELAXED_PREAMBLE in prompt

    def test_prompt_truncates_large_artifacts(self, tmp_path):
        session = _make_session(tmp_path)
        # Write a very large design notes file
        large_content = "x" * 20_000
        _write_text(tmp_path / "shows" / "my-show" / "design_notes.md", large_content)

        prompt = build_ed_prompt(tmp_path, session, mode="strict")
        # The full 20k chars should not appear
        assert len(prompt) < 25_000

    def test_prompt_includes_session_metadata(self, tmp_path):
        session = _make_session(tmp_path)
        prompt = build_ed_prompt(tmp_path, session, mode="strict")
        assert "cavaliers" in prompt
        assert "s1" in prompt


# ---------------------------------------------------------------------------
# ED Response (with MockLLMClient)
# ---------------------------------------------------------------------------

class TestEdRespond:
    def test_ed_response_references_artifacts(self, tmp_path):
        session = _make_session(tmp_path)
        mock = MockLLMClient()
        mock.queue_response(LLMResponse(
            content="Based on the standings, brass scored 80 which was the third-highest caption."
        ))

        result = ed_respond(
            project_root=tmp_path,
            session=session,
            user_message="How did brass perform?",
            llm_client=mock,
            mode="strict",
        )

        assert result["role"] == "executive_director"
        assert "brass" in result["message"].lower()
        assert result["mode"] == "strict"

        # Verify LLM was called with correct messages
        assert len(mock.calls) == 1
        call = mock.calls[0]
        assert call["model_tier"] == ModelTier.SONNET
        # System message should contain binder content
        system_msg = next(m for m in call["messages"] if m.role == "system")
        assert "brass" in system_msg.content

    def test_ed_response_appends_transcript(self, tmp_path):
        session = _make_session(tmp_path)
        mock = MockLLMClient()
        mock.queue_response(LLMResponse(content="The percussion section excelled."))

        ed_respond(
            project_root=tmp_path,
            session=session,
            user_message="What went well?",
            llm_client=mock,
            mode="strict",
        )

        from backend.services.seance_session import read_transcript
        transcript = read_transcript(tmp_path, session["seance_id"])
        assert "What went well?" in transcript
        assert "percussion section excelled" in transcript

    def test_strict_mode_prompt_forbids_invention(self, tmp_path):
        session = _make_session(tmp_path)
        mock = MockLLMClient()
        mock.queue_response(LLMResponse(
            content="I don't have information about the guard choreography in my binder."
        ))

        result = ed_respond(
            project_root=tmp_path,
            session=session,
            user_message="Describe the guard choreography in detail",
            llm_client=mock,
            mode="strict",
        )

        # The system prompt should have told the LLM to refuse unknown details
        call = mock.calls[0]
        system_msg = next(m for m in call["messages"] if m.role == "system")
        assert "not in the binder" in system_msg.content.lower() or "do not invent" in system_msg.content.lower()

    def test_relaxed_mode_prompt_requires_hypothesis_label(self, tmp_path):
        session = _make_session(tmp_path)
        mock = MockLLMClient()
        mock.queue_response(LLMResponse(
            content="[HYPOTHESIS] The guard section may have struggled with equipment tosses."
        ))

        result = ed_respond(
            project_root=tmp_path,
            session=session,
            user_message="What about guard?",
            llm_client=mock,
            mode="relaxed",
        )

        # The system prompt should instruct hypothesis labeling
        call = mock.calls[0]
        system_msg = next(m for m in call["messages"] if m.role == "system")
        assert "hypothesis" in system_msg.content.lower()

    def test_ed_includes_conversation_history(self, tmp_path):
        session = _make_session(tmp_path)
        mock = MockLLMClient()

        # First turn
        mock.queue_response(LLMResponse(content="Brass scored 80."))
        ed_respond(tmp_path, session, "How did brass do?", mock, mode="strict")

        # Second turn — should include previous exchange
        mock.queue_response(LLMResponse(content="That's a strong score."))
        ed_respond(tmp_path, session, "Is that good?", mock, mode="strict")

        call = mock.calls[1]
        user_msgs = [m for m in call["messages"] if m.role == "user"]
        # Should have at least 2 user messages (history + current)
        assert len(user_msgs) >= 2

    def test_ed_refuses_closed_session(self, tmp_path):
        session = _make_session(tmp_path)
        from backend.services.seance_session import close_session
        close_session(tmp_path, session["seance_id"])
        session["status"] = "closed"

        mock = MockLLMClient()
        with pytest.raises(ValueError, match="closed"):
            ed_respond(tmp_path, session, "Hello", mock, mode="strict")

    def test_ed_default_mode_is_strict(self, tmp_path):
        session = _make_session(tmp_path)
        mock = MockLLMClient()
        mock.queue_response(LLMResponse(content="Response."))

        result = ed_respond(tmp_path, session, "Hello", mock)
        assert result["mode"] == "strict"

        call = mock.calls[0]
        system_msg = next(m for m in call["messages"] if m.role == "system")
        assert STRICT_PREAMBLE in system_msg.content
