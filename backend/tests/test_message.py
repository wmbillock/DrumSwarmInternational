import pytest

from backend.models.message import MessagePriority, MessageType
from backend.services.message_service import (
    InvalidMessagePath,
    InvalidMessageType,
    acknowledge_message,
    poll_messages,
    send_message,
)


CORPS_ID = "test-corps-1"


class TestSendMessage:
    def test_send_basic_message(self, db):
        msg = send_message(
            db,
            corps_id=CORPS_ID,
            from_role="brass_caption_head",
            type=MessageType.HANDOFF,
            subject="New drill for movement 1",
            to_role="brass_tech",
        )
        assert msg.id is not None
        assert msg.from_role == "brass_caption_head"
        assert msg.to_role == "brass_tech"
        assert msg.type == MessageType.HANDOFF
        assert msg.priority == MessagePriority.NORMAL

    def test_send_with_priority(self, db):
        msg = send_message(
            db,
            corps_id=CORPS_ID,
            from_role="executive_director",
            type=MessageType.DIRECTIVE,
            subject="Urgent",
            to_role="program_coordinator",
            priority=MessagePriority.CRITICAL,
        )
        assert msg.priority == MessagePriority.CRITICAL

    def test_send_broadcast(self, db):
        msg = send_message(
            db,
            corps_id=CORPS_ID,
            from_role="drum_major",
            type=MessageType.STATUS,
            subject="Show time",
        )
        assert msg.to_role is None
        assert msg.to_session_id is None


class TestHierarchyEnforcement:
    def test_valid_downward_path(self, db):
        # Caption head can message their tech
        msg = send_message(
            db,
            corps_id=CORPS_ID,
            from_role="brass_caption_head",
            type=MessageType.HANDOFF,
            subject="test",
            to_role="brass_tech",
        )
        assert msg.id is not None

    def test_valid_upward_escalation(self, db):
        # Performer can escalate to section leader
        msg = send_message(
            db,
            corps_id=CORPS_ID,
            from_role="performer",
            type=MessageType.ESCALATION,
            subject="Need help",
            to_role="section_leader",
        )
        assert msg.id is not None

    def test_performer_cannot_message_caption_head(self, db):
        with pytest.raises(InvalidMessagePath, match="cannot message"):
            send_message(
                db,
                corps_id=CORPS_ID,
                from_role="performer",
                type=MessageType.ESCALATION,
                subject="Skip the chain",
                to_role="brass_caption_head",
            )

    def test_performer_cannot_message_program_coordinator(self, db):
        with pytest.raises(InvalidMessagePath, match="cannot message"):
            send_message(
                db,
                corps_id=CORPS_ID,
                from_role="performer",
                type=MessageType.STATUS,
                subject="Skip everything",
                to_role="program_coordinator",
            )

    def test_designer_cannot_message_performer(self, db):
        with pytest.raises(InvalidMessagePath, match="cannot message"):
            send_message(
                db,
                corps_id=CORPS_ID,
                from_role="drill_writer",
                type=MessageType.HANDOFF,
                subject="Direct to performer",
                to_role="performer",
            )

    def test_cross_caption_head_communication(self, db):
        # Caption heads can message each other (for conflict resolution)
        msg = send_message(
            db,
            corps_id=CORPS_ID,
            from_role="brass_caption_head",
            type=MessageType.FLAG,
            subject="Guard alignment issue",
            to_role="guard_caption_head",
        )
        assert msg.id is not None

    def test_tech_cannot_message_other_caption_tech(self, db):
        with pytest.raises(InvalidMessagePath, match="cannot message"):
            send_message(
                db,
                corps_id=CORPS_ID,
                from_role="brass_tech",
                type=MessageType.FLAG,
                subject="Cross-caption issue",
                to_role="guard_tech",
            )

    def test_unknown_sender_rejected(self, db):
        with pytest.raises(InvalidMessagePath, match="Unknown sender"):
            send_message(
                db,
                corps_id=CORPS_ID,
                from_role="nonexistent_role",
                type=MessageType.STATUS,
                subject="test",
            )

    def test_drum_major_to_caption_leads(self, db):
        for lead in ["horn_sergeant", "center_snare", "guard_captain"]:
            msg = send_message(
                db,
                corps_id=CORPS_ID,
                from_role="drum_major",
                type=MessageType.DIRECTIVE,
                subject="test",
                to_role=lead,
            )
            assert msg.id is not None

    def test_section_leader_to_tech(self, db):
        # Section leaders can escalate to techs
        msg = send_message(
            db,
            corps_id=CORPS_ID,
            from_role="section_leader",
            type=MessageType.ESCALATION,
            subject="Need help with performer",
            to_role="brass_tech",
        )
        assert msg.id is not None


class TestDirectiveRestriction:
    def test_performer_cannot_send_directive(self, db):
        with pytest.raises(InvalidMessageType, match="cannot send directives"):
            send_message(
                db,
                corps_id=CORPS_ID,
                from_role="performer",
                type=MessageType.DIRECTIVE,
                subject="I'm in charge now",
                to_role="section_leader",
            )

    def test_section_leader_cannot_send_directive(self, db):
        with pytest.raises(InvalidMessageType, match="cannot send directives"):
            send_message(
                db,
                corps_id=CORPS_ID,
                from_role="section_leader",
                type=MessageType.DIRECTIVE,
                subject="Do this",
                to_role="performer",
            )

    def test_caption_head_can_send_directive(self, db):
        msg = send_message(
            db,
            corps_id=CORPS_ID,
            from_role="brass_caption_head",
            type=MessageType.DIRECTIVE,
            subject="Run it again",
            to_role="brass_tech",
        )
        assert msg.type == MessageType.DIRECTIVE


class TestPollMessages:
    def test_poll_by_role(self, db):
        send_message(db, CORPS_ID, "brass_caption_head", MessageType.HANDOFF, "msg1", to_role="brass_tech")
        send_message(db, CORPS_ID, "guard_caption_head", MessageType.HANDOFF, "msg2", to_role="guard_tech")

        brass_msgs = poll_messages(db, CORPS_ID, role="brass_tech")
        assert len(brass_msgs) == 1
        assert brass_msgs[0].subject == "msg1"

    def test_poll_includes_broadcasts(self, db):
        send_message(db, CORPS_ID, "drum_major", MessageType.STATUS, "broadcast")
        send_message(db, CORPS_ID, "brass_caption_head", MessageType.HANDOFF, "direct", to_role="brass_tech")

        msgs = poll_messages(db, CORPS_ID, role="brass_tech")
        assert len(msgs) == 2

    def test_priority_ordering(self, db):
        send_message(db, CORPS_ID, "brass_caption_head", MessageType.HANDOFF, "low", to_role="brass_tech", priority=MessagePriority.LOW)
        send_message(db, CORPS_ID, "brass_caption_head", MessageType.HANDOFF, "critical", to_role="brass_tech", priority=MessagePriority.CRITICAL)
        send_message(db, CORPS_ID, "brass_caption_head", MessageType.HANDOFF, "normal", to_role="brass_tech", priority=MessagePriority.NORMAL)

        msgs = poll_messages(db, CORPS_ID, role="brass_tech")
        assert [m.subject for m in msgs] == ["critical", "normal", "low"]

    def test_acknowledged_messages_excluded(self, db):
        msg = send_message(db, CORPS_ID, "brass_caption_head", MessageType.HANDOFF, "msg1", to_role="brass_tech")
        send_message(db, CORPS_ID, "brass_caption_head", MessageType.HANDOFF, "msg2", to_role="brass_tech")

        acknowledge_message(db, msg.id)

        msgs = poll_messages(db, CORPS_ID, role="brass_tech")
        assert len(msgs) == 1
        assert msgs[0].subject == "msg2"

    def test_poll_all_messages_including_acknowledged(self, db):
        msg = send_message(db, CORPS_ID, "brass_caption_head", MessageType.HANDOFF, "msg1", to_role="brass_tech")
        send_message(db, CORPS_ID, "brass_caption_head", MessageType.HANDOFF, "msg2", to_role="brass_tech")
        acknowledge_message(db, msg.id)

        msgs = poll_messages(db, CORPS_ID, role="brass_tech", unacknowledged_only=False)
        assert len(msgs) == 2

    def test_poll_scoped_to_corps(self, db):
        send_message(db, "corps-1", "brass_caption_head", MessageType.HANDOFF, "corp1", to_role="brass_tech")
        send_message(db, "corps-2", "brass_caption_head", MessageType.HANDOFF, "corp2", to_role="brass_tech")

        msgs = poll_messages(db, "corps-1", role="brass_tech")
        assert len(msgs) == 1
        assert msgs[0].subject == "corp1"


class TestSystemMessages:
    def test_system_can_message_any_role(self, db):
        for target in ["performer", "section_leader", "brass_caption_head", "executive_director"]:
            msg = send_message(
                db,
                corps_id=CORPS_ID,
                from_role="system",
                type=MessageType.STATUS,
                subject=f"Notification to {target}",
                to_role=target,
            )
            assert msg.id is not None

    def test_system_cannot_send_directive(self, db):
        with pytest.raises(InvalidMessageType, match="cannot send directives"):
            send_message(
                db,
                corps_id=CORPS_ID,
                from_role="system",
                type=MessageType.DIRECTIVE,
                subject="System directive",
                to_role="performer",
            )
