import json

import pytest

from backend.models.agent_definition import ModelTier
from backend.models.agent_session import SessionStatus
from backend.services.agent_lifecycle import (
    ApprovalRequired,
    InvalidSessionTransition,
    check_tool_permission,
    complete_session,
    create_definition,
    fail_session,
    get_children,
    is_alive,
    modify_definition,
    spawn_session,
    timeout_session,
)


CORPS_ID = "test-corps-1"


class TestAgentDefinition:
    def test_create_definition(self, db):
        defn = create_definition(
            db,
            role="brass_caption_head",
            system_prompt="You are the brass caption head.",
            model_tier=ModelTier.OPUS,
            tools_allowed=["tuner", "gock_block"],
        )
        assert defn.id is not None
        assert defn.role == "brass_caption_head"
        assert defn.model_tier == ModelTier.OPUS
        assert defn.tools_allowed_list == ["tuner", "gock_block"]
        assert defn.version == 1

    def test_create_definition_defaults(self, db):
        defn = create_definition(db, role="performer", system_prompt="You are a performer.")
        assert defn.model_tier == ModelTier.SONNET
        assert defn.tools_allowed_list == []

    def test_empty_tools_list(self, db):
        defn = create_definition(db, role="performer", system_prompt="test", tools_allowed=[])
        assert defn.tools_allowed_list == []


class TestDefinitionModification:
    def test_minor_change_free(self, db):
        defn = create_definition(db, role="performer", system_prompt="v1")
        modified = modify_definition(
            db, defn.id, "tech-session-1",
            changes={"system_prompt": "v2 - improved instructions"},
        )
        assert modified.system_prompt == "v2 - improved instructions"
        assert modified.version == 2
        assert modified.modified_by == "tech-session-1"

    def test_major_change_requires_approval(self, db):
        defn = create_definition(db, role="performer", system_prompt="test")
        with pytest.raises(ApprovalRequired, match="tools_allowed"):
            modify_definition(
                db, defn.id, "tech-session-1",
                changes={"tools_allowed": ["tuner", "dressing"]},
            )

    def test_major_change_with_approval(self, db):
        defn = create_definition(db, role="performer", system_prompt="test")
        modified = modify_definition(
            db, defn.id, "tech-session-1",
            changes={"tools_allowed": ["tuner", "dressing"]},
            approved=True,
        )
        assert modified.tools_allowed_list == ["tuner", "dressing"]
        assert modified.version == 2

    def test_model_tier_change_requires_approval(self, db):
        defn = create_definition(db, role="performer", system_prompt="test")
        with pytest.raises(ApprovalRequired, match="model_tier"):
            modify_definition(
                db, defn.id, "tech-session-1",
                changes={"model_tier": ModelTier.OPUS},
            )

    def test_model_tier_change_with_approval(self, db):
        defn = create_definition(db, role="performer", system_prompt="test")
        modified = modify_definition(
            db, defn.id, "tech-session-1",
            changes={"model_tier": ModelTier.OPUS},
            approved=True,
        )
        assert modified.model_tier == ModelTier.OPUS

    def test_mixed_minor_and_major_requires_approval(self, db):
        defn = create_definition(db, role="performer", system_prompt="test")
        with pytest.raises(ApprovalRequired):
            modify_definition(
                db, defn.id, "tech-session-1",
                changes={"system_prompt": "new", "model_tier": ModelTier.HAIKU},
            )

    def test_version_increments(self, db):
        defn = create_definition(db, role="performer", system_prompt="v1")
        modify_definition(db, defn.id, "s1", changes={"system_prompt": "v2"})
        modify_definition(db, defn.id, "s2", changes={"system_prompt": "v3"})
        db.refresh(defn)
        assert defn.version == 3


class TestAgentSession:
    def _make_definition(self, db, role="performer"):
        return create_definition(
            db, role=role, system_prompt=f"You are a {role}.",
            tools_allowed=["tuner"],
        )

    def test_spawn_session(self, db):
        defn = self._make_definition(db)
        session = spawn_session(db, defn.id, CORPS_ID)
        assert session.id is not None
        assert session.status == SessionStatus.ACTIVE
        assert session.definition_id == defn.id
        assert session.corps_id == CORPS_ID
        assert session.parent_session_id is None

    def test_spawn_with_parent(self, db):
        defn = self._make_definition(db, "brass_caption_head")
        child_defn = self._make_definition(db, "brass_tech")

        parent = spawn_session(db, defn.id, CORPS_ID)
        child = spawn_session(db, child_defn.id, CORPS_ID, parent_session_id=parent.id)

        assert child.parent_session_id == parent.id

    def test_spawn_tree(self, db):
        head_defn = self._make_definition(db, "brass_caption_head")
        tech_defn = self._make_definition(db, "brass_tech")
        perf_defn = self._make_definition(db, "performer")

        head = spawn_session(db, head_defn.id, CORPS_ID)
        tech = spawn_session(db, tech_defn.id, CORPS_ID, parent_session_id=head.id)
        p1 = spawn_session(db, perf_defn.id, CORPS_ID, parent_session_id=tech.id)
        p2 = spawn_session(db, perf_defn.id, CORPS_ID, parent_session_id=tech.id)

        children = get_children(db, tech.id)
        assert len(children) == 2
        assert {c.id for c in children} == {p1.id, p2.id}

    def test_invalid_parent_rejected(self, db):
        defn = self._make_definition(db)
        with pytest.raises(ValueError, match="Parent session"):
            spawn_session(db, defn.id, CORPS_ID, parent_session_id="nonexistent")

    def test_invalid_definition_rejected(self, db):
        with pytest.raises(ValueError, match="Definition"):
            spawn_session(db, "nonexistent", CORPS_ID)


class TestSessionLifecycle:
    def _make_session(self, db):
        defn = create_definition(db, role="performer", system_prompt="test")
        return spawn_session(db, defn.id, CORPS_ID)

    def test_complete(self, db):
        session = self._make_session(db)
        completed = complete_session(db, session.id, context_snapshot='{"key": "value"}')
        assert completed.status == SessionStatus.COMPLETED
        assert completed.context_snapshot == '{"key": "value"}'
        assert completed.ended_at is not None

    def test_fail(self, db):
        session = self._make_session(db)
        failed = fail_session(db, session.id, error="Something broke")
        assert failed.status == SessionStatus.FAILED
        assert failed.error == "Something broke"
        assert failed.ended_at is not None

    def test_timeout(self, db):
        session = self._make_session(db)
        timed_out = timeout_session(db, session.id)
        assert timed_out.status == SessionStatus.TIMED_OUT
        assert timed_out.ended_at is not None

    def test_cannot_complete_twice(self, db):
        session = self._make_session(db)
        complete_session(db, session.id)
        with pytest.raises(InvalidSessionTransition, match="terminal"):
            complete_session(db, session.id)

    def test_cannot_fail_completed(self, db):
        session = self._make_session(db)
        complete_session(db, session.id)
        with pytest.raises(InvalidSessionTransition, match="terminal"):
            fail_session(db, session.id)

    def test_cannot_complete_failed(self, db):
        session = self._make_session(db)
        fail_session(db, session.id)
        with pytest.raises(InvalidSessionTransition, match="terminal"):
            complete_session(db, session.id)


class TestIsAlive:
    def _make_session(self, db):
        defn = create_definition(db, role="performer", system_prompt="test")
        return spawn_session(db, defn.id, CORPS_ID)

    def test_active_is_alive(self, db):
        session = self._make_session(db)
        assert is_alive(db, session.id) is True

    def test_completed_not_alive(self, db):
        session = self._make_session(db)
        complete_session(db, session.id)
        assert is_alive(db, session.id) is False

    def test_failed_not_alive(self, db):
        session = self._make_session(db)
        fail_session(db, session.id)
        assert is_alive(db, session.id) is False

    def test_nonexistent_not_alive(self, db):
        assert is_alive(db, "nonexistent") is False


class TestContextSnapshot:
    def _make_session(self, db):
        defn = create_definition(db, role="performer", system_prompt="test")
        return spawn_session(db, defn.id, CORPS_ID)

    def test_snapshot_on_complete(self, db):
        session = self._make_session(db)
        snapshot = json.dumps({"summary": "Implemented login", "artifacts": ["auth.py"]})
        completed = complete_session(db, session.id, context_snapshot=snapshot)

        loaded = json.loads(completed.context_snapshot)
        assert loaded["summary"] == "Implemented login"

    def test_snapshot_on_fail(self, db):
        session = self._make_session(db)
        snapshot = json.dumps({"progress": "50%", "blocker": "missing API key"})
        failed = fail_session(db, session.id, error="blocked", context_snapshot=snapshot)

        loaded = json.loads(failed.context_snapshot)
        assert loaded["blocker"] == "missing API key"

    def test_no_snapshot(self, db):
        session = self._make_session(db)
        completed = complete_session(db, session.id)
        assert completed.context_snapshot is None


class TestToolPermissions:
    def test_allowed_tool(self, db):
        defn = create_definition(
            db, role="performer", system_prompt="test",
            tools_allowed=["tuner", "gock_block"],
        )
        session = spawn_session(db, defn.id, CORPS_ID)
        assert check_tool_permission(db, session.id, "tuner") is True
        assert check_tool_permission(db, session.id, "gock_block") is True

    def test_disallowed_tool(self, db):
        defn = create_definition(
            db, role="performer", system_prompt="test",
            tools_allowed=["tuner"],
        )
        session = spawn_session(db, defn.id, CORPS_ID)
        assert check_tool_permission(db, session.id, "dressing") is False

    def test_no_tools_allowed(self, db):
        defn = create_definition(
            db, role="performer", system_prompt="test",
        )
        session = spawn_session(db, defn.id, CORPS_ID)
        assert check_tool_permission(db, session.id, "tuner") is False

    def test_nonexistent_session(self, db):
        assert check_tool_permission(db, "nonexistent", "tuner") is False
