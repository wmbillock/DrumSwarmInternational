"""Asynchronous messaging system — thread management, archival, and search."""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.orm import Session

from backend.models.messaging_thread import (
    Thread,
    ThreadMessage,
    ArchivedThread,
    ThreadStatus,
    OriginatorRole,
    SenderType,
)


class MessagingService:
    """Service for thread management, completion, archival, and search."""

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # Thread Management
    # =========================================================================

    def create_thread(
        self,
        originator_role: str,
        subject: str,
        initial_message_body: str,
        initial_sender_type: str = "agent",
        initial_sender_role: str = "agent",
        initial_sender_name: str = "Agent",
    ) -> Thread:
        """Create a new thread with an initial message."""
        thread = Thread(
            originator_role=OriginatorRole(originator_role),
            subject=subject,
            status=ThreadStatus.PENDING,
        )
        self.db.add(thread)
        self.db.flush()

        message = ThreadMessage(
            thread_id=thread.id,
            sender_type=SenderType(initial_sender_type),
            sender_role=initial_sender_role,
            sender_name=initial_sender_name,
            body=initial_message_body,
        )
        self.db.add(message)
        self.db.commit()

        return self._fetch_thread(thread.id)

    def get_thread(self, thread_id: str) -> Optional[Thread]:
        """Get a thread with all its messages (ordered by created_at)."""
        return self._fetch_thread(thread_id)

    def _fetch_thread(self, thread_id: str) -> Optional[Thread]:
        """Fetch thread and eager-load messages."""
        stmt = select(Thread).where(Thread.id == thread_id)
        thread = self.db.scalars(stmt).first()
        if thread:
            # Force load messages (ordered by created_at)
            _ = thread.messages
        return thread

    def list_threads(
        self,
        status: Optional[str] = None,
        originator_role: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Thread], int]:
        """List active threads with optional filtering."""
        stmt = select(Thread)

        if status:
            stmt = stmt.where(Thread.status == ThreadStatus(status))
        if originator_role:
            stmt = stmt.where(
                Thread.originator_role == OriginatorRole(originator_role)
            )

        # Count total
        count_stmt = select(func.count()).select_from(Thread)
        if status:
            count_stmt = count_stmt.where(Thread.status == ThreadStatus(status))
        if originator_role:
            count_stmt = count_stmt.where(
                Thread.originator_role == OriginatorRole(originator_role)
            )
        total = self.db.scalar(count_stmt) or 0

        # Fetch paginated results, ordered by updated_at (newest first)
        stmt = stmt.order_by(Thread.updated_at.desc()).limit(limit).offset(offset)
        threads = list(self.db.scalars(stmt).all())
        return threads, total

    def add_message_to_thread(
        self,
        thread_id: str,
        sender_type: str,
        sender_role: str,
        sender_name: str,
        body: str,
    ) -> ThreadMessage:
        """Add a message to an existing thread."""
        thread = self._fetch_thread(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")

        message = ThreadMessage(
            thread_id=thread_id,
            sender_type=SenderType(sender_type),
            sender_role=sender_role,
            sender_name=sender_name,
            body=body,
        )
        self.db.add(message)

        # Update thread's updated_at
        thread.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return message

    def mark_thread_complete(
        self, thread_id: str, completed_by_user_id: str
    ) -> Thread:
        """Mark a thread as completed."""
        thread = self._fetch_thread(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")

        thread.status = ThreadStatus.COMPLETED
        thread.completed_at = datetime.now(timezone.utc)
        thread.completed_by = completed_by_user_id
        thread.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return self._fetch_thread(thread.id)

    def get_threads_eligible_for_archival(self) -> list[Thread]:
        """Get all completed threads that are 30+ days old."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        stmt = select(Thread).where(
            and_(
                Thread.status == ThreadStatus.COMPLETED,
                Thread.completed_at <= cutoff,
            )
        )
        return list(self.db.scalars(stmt).all())

    def get_threads_ready_for_archive_suggestion(self) -> list[Thread]:
        """Get threads inactive for 14+ days (for UI suggestion)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        stmt = select(Thread).where(
            and_(
                Thread.status == ThreadStatus.PENDING,
                Thread.updated_at <= cutoff,
                Thread.archive_candidate_at.is_(None),
            )
        )
        threads = list(self.db.scalars(stmt).all())

        # Mark them as archive candidates
        for thread in threads:
            thread.archive_candidate_at = datetime.now(timezone.utc)
        self.db.commit()

        return threads

    # =========================================================================
    # Archive Management
    # =========================================================================

    def archive_threads(
        self,
        thread_ids: list[str],
        archived_by_user_id: str,
        summaries: dict[str, str],  # {thread_id: summary}
        decisions: dict[str, Optional[str]] = None,  # {thread_id: decision}
        tags_dict: dict[str, list[str]] = None,  # {thread_id: [tags]}
    ) -> list[ArchivedThread]:
        """Archive completed threads as summarized records."""
        if not decisions:
            decisions = {}
        if not tags_dict:
            tags_dict = {}

        archived = []
        for thread_id in thread_ids:
            thread = self._fetch_thread(thread_id)
            if not thread:
                continue

            # Concatenate all message bodies for full_text indexing
            full_text = "\n".join(msg.body for msg in thread.messages)

            # Flatten tags to CSV string
            tags_str = None
            if thread_id in tags_dict:
                tags_str = ",".join(tags_dict[thread_id])

            archived_thread = ArchivedThread(
                original_thread_id=thread.id,
                originator_role=thread.originator_role.value,
                subject=thread.subject,
                summary=summaries.get(thread_id, ""),
                message_count=len(thread.messages),
                created_at=thread.created_at,
                archived_by=archived_by_user_id,
                full_text=full_text,
                tags=tags_str,
                decision=decisions.get(thread_id),
            )
            self.db.add(archived_thread)
            archived.append(archived_thread)

            # Remove thread from active list
            self.db.delete(thread)

        self.db.commit()
        return archived

    def get_archived_thread(self, archived_thread_id: str) -> Optional[ArchivedThread]:
        """Get an archived thread (read-only view)."""
        stmt = select(ArchivedThread).where(ArchivedThread.id == archived_thread_id)
        return self.db.scalars(stmt).first()

    def list_archived_threads(
        self,
        search_query: Optional[str] = None,
        originator_role: Optional[str] = None,
        tags: Optional[list[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ArchivedThread], int]:
        """List archived threads with search, filtering, and relevance ranking.

        Returns (threads, total_count) sorted by relevance score descending.
        """
        stmt = select(ArchivedThread)

        # Apply filters
        if originator_role:
            stmt = stmt.where(
                ArchivedThread.originator_role == originator_role
            )
        if tags:
            # Filter by tags (CSV string matching)
            or_conditions = [
                ArchivedThread.tags.like(f"%{tag}%") for tag in tags
            ]
            stmt = stmt.where(or_(*or_conditions))

        # Count total before search
        count_stmt = select(func.count()).select_from(ArchivedThread)
        if originator_role:
            count_stmt = count_stmt.where(
                ArchivedThread.originator_role == originator_role
            )
        if tags:
            or_conditions = [
                ArchivedThread.tags.like(f"%{tag}%") for tag in tags
            ]
            count_stmt = count_stmt.where(or_(*or_conditions))
        total = self.db.scalar(count_stmt) or 0

        if search_query:
            # Simple full-text search: match in subject, summary, or full_text
            search_pattern = f"%{search_query}%"
            stmt = stmt.where(
                or_(
                    ArchivedThread.subject.ilike(search_pattern),
                    ArchivedThread.summary.ilike(search_pattern),
                    ArchivedThread.full_text.ilike(search_pattern),
                )
            )

        # Order by: decision_boost, recency, then by ID
        # Archives with decisions rank higher; recent archives rank higher
        stmt = stmt.order_by(
            (ArchivedThread.decision.isnot(None)).desc(),
            ArchivedThread.archived_at.desc(),
            ArchivedThread.id,
        ).limit(limit).offset(offset)

        threads = list(self.db.scalars(stmt).all())
        return threads, total

    def search_archive(
        self,
        search_query: str,
        originator_role: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ArchivedThread], int]:
        """Search archived threads by keyword with date range filtering."""
        stmt = select(ArchivedThread)

        # Full-text keyword search
        search_pattern = f"%{search_query}%"
        stmt = stmt.where(
            or_(
                ArchivedThread.subject.ilike(search_pattern),
                ArchivedThread.summary.ilike(search_pattern),
                ArchivedThread.full_text.ilike(search_pattern),
            )
        )

        # Optional role filter
        if originator_role:
            stmt = stmt.where(
                ArchivedThread.originator_role == originator_role
            )

        # Optional date range
        if date_from:
            stmt = stmt.where(ArchivedThread.archived_at >= date_from)
        if date_to:
            stmt = stmt.where(ArchivedThread.archived_at <= date_to)

        # Count total
        count_stmt = select(func.count()).select_from(ArchivedThread).where(
            or_(
                ArchivedThread.subject.ilike(search_pattern),
                ArchivedThread.summary.ilike(search_pattern),
                ArchivedThread.full_text.ilike(search_pattern),
            )
        )
        if originator_role:
            count_stmt = count_stmt.where(
                ArchivedThread.originator_role == originator_role
            )
        if date_from:
            count_stmt = count_stmt.where(ArchivedThread.archived_at >= date_from)
        if date_to:
            count_stmt = count_stmt.where(ArchivedThread.archived_at <= date_to)
        total = self.db.scalar(count_stmt) or 0

        # Order by: decision prominence, recency
        stmt = stmt.order_by(
            (ArchivedThread.decision.isnot(None)).desc(),
            ArchivedThread.archived_at.desc(),
        ).limit(limit).offset(offset)

        results = list(self.db.scalars(stmt).all())
        return results, total
