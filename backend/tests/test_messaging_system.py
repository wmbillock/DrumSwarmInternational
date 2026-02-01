"""Tests for asynchronous messaging system.

Covers thread creation, messaging, completion, archival, and search as per spec.
"""

import pytest
from datetime import datetime, timedelta, timezone

from backend.services.messaging_service import MessagingService
from backend.services.messaging_permissions import MessagingPermissions
from backend.models.messaging_thread import (
    Thread,
    ThreadMessage,
    ArchivedThread,
    ThreadStatus,
    OriginatorRole,
    SenderType,
)


class TestThreadCreation:
    """Test thread creation and initial messaging."""

    def test_create_thread_with_initial_message(self, db):
        """Agent escalates question → thread created in inbox."""
        service = MessagingService(db)

        thread = service.create_thread(
            originator_role="executive_director",
            subject="Design direction for brass section",
            initial_message_body="Need approval on new brass arrangement",
            initial_sender_type="agent",
            initial_sender_role="music_writer",
            initial_sender_name="Music Writer Agent",
        )

        assert thread is not None
        assert thread.id
        assert thread.subject == "Design direction for brass section"
        assert thread.status == ThreadStatus.PENDING
        assert len(thread.messages) == 1
        assert thread.messages[0].sender_name == "Music Writer Agent"
        assert thread.messages[0].body == "Need approval on new brass arrangement"

    def test_thread_persistence(self, db):
        """Thread data persists across queries."""
        service = MessagingService(db)

        thread1 = service.create_thread(
            originator_role="program_coordinator",
            subject="Schedule update",
            initial_message_body="Tour dates changed",
        )
        thread_id = thread1.id

        # Fetch again
        thread2 = service.get_thread(thread_id)
        assert thread2 is not None
        assert thread2.id == thread_id
        assert thread2.subject == "Schedule update"


class TestThreadMessaging:
    """Test multi-turn conversation in threads."""

    def test_add_message_to_thread(self, db):
        """User replies to thread → message appended, originator notified."""
        service = MessagingService(db)

        thread = service.create_thread(
            originator_role="executive_director",
            subject="Brass section design",
            initial_message_body="Need feedback on arrangement",
        )

        # User replies
        message = service.add_message_to_thread(
            thread_id=thread.id,
            sender_type="user",
            sender_role="user",
            sender_name="Executive Director",
            body="Approved. Sounds good.",
        )

        assert message.id
        assert message.sender_name == "Executive Director"
        assert message.body == "Approved. Sounds good."

        # Fetch thread and verify message was appended
        updated_thread = service.get_thread(thread.id)
        assert len(updated_thread.messages) == 2
        assert updated_thread.messages[1].body == "Approved. Sounds good."

    def test_multi_turn_conversation_preserves_all_messages(self, db):
        """Multi-turn conversation completes without data loss."""
        service = MessagingService(db)

        thread = service.create_thread(
            originator_role="program_coordinator",
            subject="Percussion timing issue",
            initial_message_body="Issue: percussion not syncing with drill",
        )

        # Message 2
        service.add_message_to_thread(
            thread_id=thread.id,
            sender_type="user",
            sender_role="user",
            sender_name="PC",
            body="Can you provide video reference?",
        )

        # Message 3
        service.add_message_to_thread(
            thread_id=thread.id,
            sender_type="agent",
            sender_role="caption_head",
            sender_name="Percussion Caption Head",
            body="Attached timing reference video.",
        )

        # Message 4
        service.add_message_to_thread(
            thread_id=thread.id,
            sender_type="user",
            sender_role="user",
            sender_name="PC",
            body="Great! Fix confirmed.",
        )

        # Verify all messages are present and ordered
        updated = service.get_thread(thread.id)
        assert len(updated.messages) == 4
        assert updated.messages[0].body == "Issue: percussion not syncing with drill"
        assert updated.messages[1].body == "Can you provide video reference?"
        assert updated.messages[2].body == "Attached timing reference video."
        assert updated.messages[3].body == "Great! Fix confirmed."


class TestThreadCompletion:
    """Test manual thread completion."""

    def test_mark_thread_complete(self, db):
        """User marks thread complete → status changes, timestamp recorded."""
        service = MessagingService(db)

        thread = service.create_thread(
            originator_role="executive_director",
            subject="Design approval",
            initial_message_body="Please review",
        )

        completed_thread = service.mark_thread_complete(
            thread_id=thread.id,
            completed_by_user_id="user-123",
        )

        assert completed_thread.status == ThreadStatus.COMPLETED
        assert completed_thread.completed_at is not None
        assert completed_thread.completed_by == "user-123"

    def test_completed_thread_remains_visible(self, db):
        """Completed threads remain visible but visually distinguished."""
        service = MessagingService(db)

        thread = service.create_thread(
            originator_role="program_coordinator",
            subject="Test thread",
            initial_message_body="Test",
        )

        service.mark_thread_complete(thread.id, "user-456")

        # Should still be retrievable
        retrieved = service.get_thread(thread.id)
        assert retrieved is not None
        assert retrieved.status == ThreadStatus.COMPLETED

    def test_reading_does_not_auto_complete(self, db):
        """Reading a message does not auto-complete thread."""
        service = MessagingService(db)

        thread = service.create_thread(
            originator_role="executive_director",
            subject="Message to read",
            initial_message_body="This is readable but shouldn't complete thread",
        )

        # Fetch thread (implicit "read")
        retrieved = service.get_thread(thread.id)

        # Thread should still be pending
        assert retrieved.status == ThreadStatus.PENDING
        assert retrieved.completed_at is None


class TestBulkArchival:
    """Test bulk archival and record summarization."""

    def test_bulk_archive_multiple_threads(self, db):
        """Admin selects threads → bulk-archive executes, removes from active list."""
        service = MessagingService(db)

        # Create 3 threads
        thread_ids = []
        for i in range(3):
            thread = service.create_thread(
                originator_role="executive_director",
                subject=f"Thread {i}",
                initial_message_body=f"Message {i}",
            )
            service.mark_thread_complete(thread.id, "user-123")
            thread_ids.append(thread.id)

        # Verify they're in active threads
        active, total = service.list_threads(status="completed")
        assert total == 3

        # Archive them
        summaries = {tid: f"Summary of {tid}" for tid in thread_ids}
        archived = service.archive_threads(
            thread_ids=thread_ids,
            archived_by_user_id="admin-user",
            summaries=summaries,
        )

        assert len(archived) == 3

        # Verify removed from active list
        active_after, total_after = service.list_threads(status="completed")
        assert total_after == 0

    def test_archived_thread_immutable(self, db):
        """Archived summaries are immutable, reference original thread ID."""
        service = MessagingService(db)

        thread = service.create_thread(
            originator_role="program_coordinator",
            subject="Archived record test",
            initial_message_body="Original message",
        )
        thread_id = thread.id
        service.mark_thread_complete(thread_id, "user-123")

        # Archive
        archived_list = service.archive_threads(
            thread_ids=[thread_id],
            archived_by_user_id="admin-user",
            summaries={thread_id: "Test summary"},
        )

        archived = archived_list[0]
        assert archived.original_thread_id == thread_id
        assert archived.summary == "Test summary"
        assert archived.archived_by == "admin-user"
        assert archived.archived_at is not None

    def test_archive_operation_timing(self, db):
        """Bulk-archive of 50 threads executes in reasonable time."""
        service = MessagingService(db)

        # Create 50 completed threads
        thread_ids = []
        for i in range(50):
            thread = service.create_thread(
                originator_role="executive_director",
                subject=f"Thread {i}",
                initial_message_body=f"Body {i}",
            )
            service.mark_thread_complete(thread.id, "user-123")
            thread_ids.append(thread.id)

        # Archive all 50 (this should complete quickly even without LLM)
        summaries = {tid: f"Summary {i}" for i, tid in enumerate(thread_ids)}
        import time

        start = time.time()
        archived = service.archive_threads(
            thread_ids=thread_ids,
            archived_by_user_id="admin-user",
            summaries=summaries,
        )
        elapsed = time.time() - start

        assert len(archived) == 50
        # Should complete in reasonable time (not asserting exact timing)
        assert elapsed < 10  # 10 seconds is very generous


class TestArchiveSearch:
    """Test archive searching and ranking."""

    def test_search_archived_by_keyword(self, db):
        """Search for archived threads by keyword → returns results in <1 sec."""
        service = MessagingService(db)

        # Create and archive threads with different content
        for i in range(5):
            thread = service.create_thread(
                originator_role="executive_director",
                subject="Design decision about brass section" if i == 0 else f"Topic {i}",
                initial_message_body="Need to finalize brass arrangement",
            )
            service.mark_thread_complete(thread.id, "user-123")

        # Archive
        summaries = {}
        for thread_id in [t.id for t in service.db.query(Thread).all()]:
            summaries[thread_id] = "Test summary"

        service.archive_threads(
            thread_ids=list(summaries.keys()),
            archived_by_user_id="admin-user",
            summaries=summaries,
        )

        # Search
        import time

        start = time.time()
        results, total = service.search_archive(search_query="brass")
        elapsed = time.time() - start

        assert len(results) > 0
        assert elapsed < 1.0  # Should be very fast

    def test_search_results_ranked_by_relevance(self, db):
        """Results ranked by relevance (decision prominence, recency)."""
        service = MessagingService(db)

        # Create threads with and without decisions
        thread1 = service.create_thread(
            originator_role="executive_director",
            subject="Design decision: new arrangement approved",
            initial_message_body="Decision: approved by director",
        )
        service.mark_thread_complete(thread1.id, "user-123")

        thread2 = service.create_thread(
            originator_role="program_coordinator",
            subject="Random question about scheduling",
            initial_message_body="Just asking about tour dates",
        )
        service.mark_thread_complete(thread2.id, "user-123")

        # Archive
        summaries = {
            thread1.id: "Approved new arrangement",
            thread2.id: "Answered scheduling question",
        }
        decisions = {
            thread1.id: "Arrangement approved",
            thread2.id: None,
        }

        service.archive_threads(
            thread_ids=[thread1.id, thread2.id],
            archived_by_user_id="admin-user",
            summaries=summaries,
            decisions=decisions,
        )

        # Search for keyword in both — decision-containing one should rank higher
        results, _ = service.search_archive(search_query="approved")
        # First result should be the one with the decision
        if len(results) > 1:
            assert results[0].decision is not None

    def test_full_text_indexing(self, db):
        """Full-text search includes messages and summaries."""
        service = MessagingService(db)

        thread = service.create_thread(
            originator_role="executive_director",
            subject="General topic",
            initial_message_body="Discussion about percussion synchronization issues",
        )
        service.add_message_to_thread(
            thread_id=thread.id,
            sender_type="user",
            sender_role="user",
            sender_name="User",
            body="Percussion timing is now fixed",
        )
        service.mark_thread_complete(thread.id, "user-123")

        # Archive
        service.archive_threads(
            thread_ids=[thread.id],
            archived_by_user_id="admin-user",
            summaries={thread.id: "Percussion issues were resolved through careful timing adjustments"},
        )

        # Search in message body, summary, or subject
        results1, _ = service.search_archive(search_query="percussion")
        results2, _ = service.search_archive(search_query="synchronization")
        results3, _ = service.search_archive(search_query="timing")

        assert len(results1) > 0  # Found in summary
        assert len(results2) > 0  # Found in message body
        assert len(results3) > 0  # Found in both


class TestPermissions:
    """Test role-based permission enforcement."""

    def test_only_eds_and_pcs_can_create_threads(self):
        """Permission: Only EDs and PCs can create threads."""
        assert MessagingPermissions.can_create_thread("executive_director")
        assert MessagingPermissions.can_create_thread("program_coordinator")
        assert not MessagingPermissions.can_create_thread("caption_head")
        assert not MessagingPermissions.can_create_thread("tech")
        assert not MessagingPermissions.can_create_thread("performer")

    def test_only_admins_can_bulk_archive(self):
        """Permission: Only Admins can bulk-archive."""
        assert MessagingPermissions.can_bulk_archive_threads("admin")
        assert not MessagingPermissions.can_bulk_archive_threads("executive_director")
        assert not MessagingPermissions.can_bulk_archive_threads("program_coordinator")

    def test_only_admins_and_eds_can_search_archive(self):
        """Permission: Admins and EDs can search archives; others cannot."""
        assert MessagingPermissions.can_search_archive("admin")
        assert MessagingPermissions.can_search_archive("executive_director")
        assert not MessagingPermissions.can_search_archive("program_coordinator")
        assert not MessagingPermissions.can_search_archive("caption_head")
        assert not MessagingPermissions.can_search_archive("tech")


class TestNotificationTimings:
    """Test notification and archival timing rules."""

    def test_14_day_archive_suggestion_eligibility(self, db):
        """14-day inactive mark for UI suggestion."""
        service = MessagingService(db)

        thread = service.create_thread(
            originator_role="executive_director",
            subject="Old thread",
            initial_message_body="This is old",
        )

        # Manually set updated_at to 15 days ago
        thread.updated_at = datetime.now(timezone.utc) - timedelta(days=15)
        service.db.commit()

        # Get threads ready for archive suggestion
        ready = service.get_threads_ready_for_archive_suggestion()

        assert len(ready) == 1
        assert ready[0].id == thread.id
        assert ready[0].archive_candidate_at is not None

    def test_30_day_auto_archive_eligibility(self, db):
        """30-day auto-archive eligibility for completed threads."""
        service = MessagingService(db)

        thread = service.create_thread(
            originator_role="executive_director",
            subject="Old completed thread",
            initial_message_body="Test",
        )
        service.mark_thread_complete(thread.id, "user-123")

        # Manually set completed_at to 31 days ago
        thread.completed_at = datetime.now(timezone.utc) - timedelta(days=31)
        service.db.commit()

        # Get eligible for archival
        eligible = service.get_threads_eligible_for_archival()

        assert len(eligible) == 1
        assert eligible[0].id == thread.id

    def test_uncompleted_thread_remains_active(self, db):
        """Uncompleted threads remain active indefinitely."""
        service = MessagingService(db)

        thread = service.create_thread(
            originator_role="executive_director",
            subject="Never completed",
            initial_message_body="Test",
        )

        # Set updated_at to 60 days ago
        thread.updated_at = datetime.now(timezone.utc) - timedelta(days=60)
        service.db.commit()

        # Should NOT be eligible for archival (not completed)
        eligible = service.get_threads_eligible_for_archival()
        assert len(eligible) == 0

        # But should appear in active threads
        active, _ = service.list_threads()
        assert any(t.id == thread.id for t in active)


class TestSystemReliability:
    """Test system reliability and data integrity."""

    def test_no_message_loss(self, db):
        """No message loss: all messages persist regardless of thread status."""
        service = MessagingService(db)

        thread = service.create_thread(
            originator_role="executive_director",
            subject="Test thread",
            initial_message_body="Message 1",
        )

        service.add_message_to_thread(
            thread_id=thread.id,
            sender_type="user",
            sender_role="user",
            sender_name="User",
            body="Message 2",
        )

        # Complete the thread
        service.mark_thread_complete(thread.id, "user-123")

        # Archive the thread
        service.archive_threads(
            thread_ids=[thread.id],
            archived_by_user_id="admin-user",
            summaries={thread.id: "Summary"},
        )

        # Check archived thread has all messages in its full_text
        archived = service.db.query(ArchivedThread).filter(
            ArchivedThread.original_thread_id == thread.id
        ).first()

        assert "Message 1" in archived.full_text
        assert "Message 2" in archived.full_text
        assert archived.message_count == 2

    def test_pagination_consistency(self, db):
        """Pagination returns consistent, ordered results."""
        service = MessagingService(db)

        # Create 25 threads
        for i in range(25):
            service.create_thread(
                originator_role="executive_director",
                subject=f"Thread {i}",
                initial_message_body=f"Body {i}",
            )

        # Get page 1 (10 items)
        page1, total1 = service.list_threads(limit=10, offset=0)
        # Get page 2 (10 items)
        page2, total2 = service.list_threads(limit=10, offset=10)
        # Get page 3 (remaining 5 items)
        page3, total3 = service.list_threads(limit=10, offset=20)

        assert total1 == 25
        assert total2 == 25
        assert total3 == 25
        assert len(page1) == 10
        assert len(page2) == 10
        assert len(page3) == 5

        # Verify no duplicates
        all_ids = set(t.id for t in page1) | set(t.id for t in page2) | set(t.id for t in page3)
        assert len(all_ids) == 25
