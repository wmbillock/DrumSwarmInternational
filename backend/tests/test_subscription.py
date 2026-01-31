import pytest

from backend.models.segment import SegmentType
from backend.models.subscription import EventType
from backend.services.segment_service import create_segment
from backend.services.message_service import poll_messages
from backend.services.subscription_service import (
    get_subscribers,
    notify_subscribers,
    subscribe,
    unsubscribe,
)


CORPS_ID = "test-corps-1"


class TestSubscribe:
    def _make_segment(self, db):
        show = create_segment(db, SegmentType.SHOW, "Show")
        m = create_segment(db, SegmentType.MOVEMENT, "M1", parent_id=show.id)
        s = create_segment(db, SegmentType.SET, "S1", parent_id=m.id)
        return create_segment(db, SegmentType.SEGMENT, "C1", parent_id=s.id)

    def test_subscribe_to_event(self, db):
        c = self._make_segment(db)
        sub = subscribe(db, c.id, "brass_caption_head", CORPS_ID, EventType.REP_COMPLETED)
        assert sub.id is not None
        assert sub.active is True
        assert sub.event_type == EventType.REP_COMPLETED

    def test_duplicate_subscription_returns_existing(self, db):
        c = self._make_segment(db)
        sub1 = subscribe(db, c.id, "brass_caption_head", CORPS_ID, EventType.REP_COMPLETED)
        sub2 = subscribe(db, c.id, "brass_caption_head", CORPS_ID, EventType.REP_COMPLETED)
        assert sub1.id == sub2.id

    def test_different_events_create_separate_subscriptions(self, db):
        c = self._make_segment(db)
        sub1 = subscribe(db, c.id, "brass_caption_head", CORPS_ID, EventType.REP_COMPLETED)
        sub2 = subscribe(db, c.id, "brass_caption_head", CORPS_ID, EventType.REP_FAILED)
        assert sub1.id != sub2.id

    def test_unsubscribe(self, db):
        c = self._make_segment(db)
        sub = subscribe(db, c.id, "brass_caption_head", CORPS_ID, EventType.REP_COMPLETED)
        unsubscribe(db, sub.id)
        db.refresh(sub)
        assert sub.active is False

    def test_unsubscribed_not_in_get_subscribers(self, db):
        c = self._make_segment(db)
        sub = subscribe(db, c.id, "brass_caption_head", CORPS_ID, EventType.REP_COMPLETED)
        unsubscribe(db, sub.id)
        subs = get_subscribers(db, c.id, EventType.REP_COMPLETED)
        assert len(subs) == 0


class TestGetSubscribers:
    def _make_segment(self, db):
        show = create_segment(db, SegmentType.SHOW, "Show")
        m = create_segment(db, SegmentType.MOVEMENT, "M1", parent_id=show.id)
        s = create_segment(db, SegmentType.SET, "S1", parent_id=m.id)
        return create_segment(db, SegmentType.SEGMENT, "C1", parent_id=s.id)

    def test_multiple_subscribers(self, db):
        c = self._make_segment(db)
        subscribe(db, c.id, "brass_caption_head", CORPS_ID, EventType.REP_COMPLETED)
        subscribe(db, c.id, "program_coordinator", CORPS_ID, EventType.REP_COMPLETED)

        subs = get_subscribers(db, c.id, EventType.REP_COMPLETED)
        assert len(subs) == 2
        roles = {s.subscriber_role for s in subs}
        assert roles == {"brass_caption_head", "program_coordinator"}

    def test_only_matching_event_type(self, db):
        c = self._make_segment(db)
        subscribe(db, c.id, "brass_caption_head", CORPS_ID, EventType.REP_COMPLETED)
        subscribe(db, c.id, "brass_caption_head", CORPS_ID, EventType.PROBLEM_POSTED)

        subs = get_subscribers(db, c.id, EventType.REP_COMPLETED)
        assert len(subs) == 1


class TestNotifySubscribers:
    def _make_segment(self, db):
        show = create_segment(db, SegmentType.SHOW, "Show")
        m = create_segment(db, SegmentType.MOVEMENT, "M1", parent_id=show.id)
        s = create_segment(db, SegmentType.SET, "S1", parent_id=m.id)
        return create_segment(db, SegmentType.SEGMENT, "C1", parent_id=s.id)

    def test_notify_creates_messages(self, db):
        c = self._make_segment(db)
        subscribe(db, c.id, "brass_caption_head", CORPS_ID, EventType.REP_COMPLETED)
        subscribe(db, c.id, "program_coordinator", CORPS_ID, EventType.REP_COMPLETED)

        messages = notify_subscribers(
            db, c.id, CORPS_ID, EventType.REP_COMPLETED,
            subject="Rep completed for C1",
            body="Segment C1 has a completed rep",
        )
        assert len(messages) == 2

    def test_notified_messages_appear_in_poll(self, db):
        c = self._make_segment(db)
        subscribe(db, c.id, "brass_caption_head", CORPS_ID, EventType.REP_COMPLETED)

        notify_subscribers(
            db, c.id, CORPS_ID, EventType.REP_COMPLETED,
            subject="Rep done",
        )

        msgs = poll_messages(db, CORPS_ID, role="brass_caption_head")
        assert len(msgs) == 1
        assert msgs[0].subject == "Rep done"
        assert msgs[0].segment_id == c.id

    def test_no_subscribers_no_messages(self, db):
        c = self._make_segment(db)
        messages = notify_subscribers(
            db, c.id, CORPS_ID, EventType.REP_COMPLETED,
            subject="Nobody listening",
        )
        assert len(messages) == 0

    def test_inactive_subscribers_not_notified(self, db):
        c = self._make_segment(db)
        sub = subscribe(db, c.id, "brass_caption_head", CORPS_ID, EventType.REP_COMPLETED)
        unsubscribe(db, sub.id)

        messages = notify_subscribers(
            db, c.id, CORPS_ID, EventType.REP_COMPLETED,
            subject="Should not arrive",
        )
        assert len(messages) == 0
