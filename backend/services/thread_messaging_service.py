"""Thread Messaging Service — Asynchronous Message Threading and Archival."""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from backend.models.messaging_thread import (
    Thread,
    ThreadMessage,
    ArchivedThread,
    ThreadStatus,
    OriginatorRole,
    SenderType,
)


async def create_thread(
    db: Session,
    corps_id: Optional[str],
    initiator_agent_id: Optional[str],
    originator_role: OriginatorRole,
    subject: str,
    initial_message_body: str,
    sender_name: str,
) -> Thread:
    """Create a new message thread with an initial message.

    Args:
        db: Database session
        corps_id: ID of the corps (nullable for system-wide threads)
        initiator_agent_id: ID of the agent session that initiated the thread
        originator_role: Role of the originator (ED, PC, etc.)
        subject: Thread subject line
        initial_message_body: Body of the first message
        sender_name: Name of the sender (agent name)

    Returns:
        The created Thread object
    """
    thread = Thread(
        id=str(uuid.uuid4()),
        corps_id=corps_id,
        initiator_agent_id=initiator_agent_id,
        originator_role=originator_role,
        subject=subject,
        status=ThreadStatus.PENDING,
    )
    db.add(thread)
    db.flush()  # Ensure thread ID is available

    # Add initial message
    initial_message = ThreadMessage(
        id=str(uuid.uuid4()),
        thread_id=thread.id,
        sender_type=SenderType.AGENT,
        sender_role=originator_role.value,
        sender_name=sender_name,
        body=initial_message_body,
    )
    db.add(initial_message)
    db.commit()
    db.refresh(thread)

    return thread


async def add_message(
    db: Session,
    thread_id: str,
    sender_type: SenderType,
    sender_role: str,
    sender_name: str,
    body: str,
) -> ThreadMessage:
    """Add a message to an existing thread.

    Args:
        db: Database session
        thread_id: ID of the thread
        sender_type: USER or AGENT
        sender_role: Role of the sender
        sender_name: Name of the sender
        body: Message content (markdown)

    Returns:
        The created ThreadMessage object
    """
    message = ThreadMessage(
        id=str(uuid.uuid4()),
        thread_id=thread_id,
        sender_type=sender_type,
        sender_role=sender_role,
        sender_name=sender_name,
        body=body,
    )
    db.add(message)

    # Update thread's updated_at timestamp
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if thread:
        thread.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(message)

    return message


async def mark_viewed(db: Session, thread_id: str) -> Thread:
    """Mark a thread as viewed.

    Args:
        db: Database session
        thread_id: ID of the thread

    Returns:
        The updated Thread object
    """
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise ValueError(f"Thread {thread_id} not found")

    thread.viewed_at = datetime.utcnow()
    db.commit()
    db.refresh(thread)

    return thread


async def mark_completed(db: Session, thread_id: str, completed_by: str) -> Thread:
    """Mark a thread as completed.

    Args:
        db: Database session
        thread_id: ID of the thread
        completed_by: User ID who marked it complete

    Returns:
        The updated Thread object
    """
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise ValueError(f"Thread {thread_id} not found")

    thread.status = ThreadStatus.COMPLETED
    thread.completed_at = datetime.utcnow()
    thread.completed_by = completed_by

    # Set archive_candidate_at to 14 days from now
    thread.archive_candidate_at = datetime.utcnow() + timedelta(days=14)

    db.commit()
    db.refresh(thread)

    return thread


async def generate_archive_summary(
    db: Session, thread_id: str, llm_client
) -> Tuple[str, Optional[str], Optional[List[str]]]:
    """Generate an LLM summary of a thread for archival.

    Args:
        db: Database session
        thread_id: ID of the thread to summarize
        llm_client: LLM client instance

    Returns:
        Tuple of (summary, decision, tags)
    """
    messages = (
        db.query(ThreadMessage)
        .filter(ThreadMessage.thread_id == thread_id)
        .order_by(ThreadMessage.created_at)
        .all()
    )

    if not messages:
        return "Empty thread - no messages.", None, None

    conversation_text = "\n\n".join(
        [f"{m.sender_name} ({m.sender_role}): {m.body}" for m in messages]
    )

    prompt = f"""Analyze this conversation thread and provide:
1. A 2-3 sentence summary
2. The key decision made (or "None" if no decision)
3. 3-5 keywords/tags (comma-separated)

Conversation:
{conversation_text}

Format your response as:
SUMMARY: [summary here]
DECISION: [decision here or None]
TAGS: [tag1, tag2, tag3]
"""

    try:
        response = await llm_client.generate(prompt)
        lines = response.strip().split("\n")

        summary = "Summary generation failed"
        decision = None
        tags = None

        for line in lines:
            if line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()
            elif line.startswith("DECISION:"):
                dec = line.replace("DECISION:", "").strip()
                decision = None if dec.lower() == "none" else dec
            elif line.startswith("TAGS:"):
                tag_str = line.replace("TAGS:", "").strip()
                tags = [t.strip() for t in tag_str.split(",") if t.strip()]

        return summary, decision, tags

    except Exception as e:
        return f"Summary generation failed: {str(e)}", None, None


async def bulk_archive(
    db: Session,
    thread_ids: List[str],
    archived_by: str,
    llm_client,
) -> List[ArchivedThread]:
    """Bulk-archive completed threads with LLM-generated summaries.

    Args:
        db: Database session
        thread_ids: List of thread IDs to archive
        archived_by: User ID performing the archive
        llm_client: LLM client instance for summary generation

    Returns:
        List of created ArchivedThread objects
    """
    archived_threads = []

    for thread_id in thread_ids:
        thread = db.query(Thread).filter(Thread.id == thread_id).first()
        if not thread:
            continue

        # Only archive completed threads
        if thread.status != ThreadStatus.COMPLETED:
            continue

        messages = (
            db.query(ThreadMessage)
            .filter(ThreadMessage.thread_id == thread_id)
            .order_by(ThreadMessage.created_at)
            .all()
        )

        # Generate summary, decision, and tags
        summary, decision, tags = await generate_archive_summary(db, thread_id, llm_client)

        # Extract full text for search
        full_text = " ".join([m.body for m in messages])

        # Create archived record
        archived = ArchivedThread(
            id=str(uuid.uuid4()),
            original_thread_id=thread.id,
            originator_role=thread.originator_role.value,
            subject=thread.subject,
            summary=summary,
            message_count=len(messages),
            created_at=thread.created_at,
            archived_by=archived_by,
            full_text=full_text,
            tags=",".join(tags) if tags else None,
            decision=decision,
        )
        db.add(archived)
        archived_threads.append(archived)

        # Delete original thread (cascade will delete messages)
        db.delete(thread)

    db.commit()

    return archived_threads


async def search_archive(
    db: Session,
    query: Optional[str] = None,
    originator_role: Optional[str] = None,
    date_range: Optional[Tuple[datetime, datetime]] = None,
    limit: int = 50,
) -> List[ArchivedThread]:
    """Search archived threads with relevance ranking.

    Args:
        db: Database session
        query: Full-text search query (searches summary and full_text)
        originator_role: Filter by originator role
        date_range: Tuple of (start_date, end_date)
        limit: Maximum number of results

    Returns:
        List of matching ArchivedThread objects ordered by relevance
    """
    stmt = select(ArchivedThread)

    # Full-text search (SQLite LIKE-based, consider FTS5 for production)
    if query:
        search_pattern = f"%{query}%"
        stmt = stmt.where(
            or_(
                ArchivedThread.summary.like(search_pattern),
                ArchivedThread.full_text.like(search_pattern),
                ArchivedThread.subject.like(search_pattern),
                ArchivedThread.tags.like(search_pattern),
            )
        )

    # Filter by originator role
    if originator_role:
        stmt = stmt.where(ArchivedThread.originator_role == originator_role)

    # Filter by date range
    if date_range:
        start_date, end_date = date_range
        stmt = stmt.where(
            ArchivedThread.archived_at >= start_date,
            ArchivedThread.archived_at <= end_date,
        )

    # BM25-inspired ranking: fetch candidates then sort in Python.
    # For small result sets this is fine; for large-scale, migrate to FTS5.
    stmt = stmt.limit(limit * 3)  # over-fetch for re-ranking
    result = db.execute(stmt)
    candidates = list(result.scalars().all())

    if query and candidates:
        import math
        from datetime import datetime, timezone

        query_terms = query.lower().split()
        now = datetime.now(timezone.utc)

        def _score(thread: ArchivedThread) -> float:
            # Term frequency in searchable text
            text = " ".join(filter(None, [
                thread.summary or "", thread.full_text or "",
                thread.subject or "", thread.tags or "",
            ])).lower()
            tf = sum(text.count(t) for t in query_terms)
            doc_len = max(len(text.split()), 1)
            # Simplified BM25: k1=1.5, b=0.75, assume avg_dl=200
            k1, b, avg_dl = 1.5, 0.75, 200
            bm25 = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_dl))

            # Recency boost: exponential decay over 30 days
            age_days = (now - (thread.archived_at or now)).total_seconds() / 86400
            recency = math.exp(-age_days / 30)

            # Tag match boost
            tags = (thread.tags or "").lower()
            tag_hits = sum(1 for t in query_terms if t in tags)
            tag_score = tag_hits / max(len(query_terms), 1)

            # Decision marker boost (check for decision-related keywords in summary)
            decision_keywords = {"decision", "decided", "approved", "rejected", "resolved"}
            summary_lower = (thread.summary or "").lower()
            decision_boost = 0.05 if any(kw in summary_lower for kw in decision_keywords) else 0.0

            return bm25 * 0.5 + recency * 0.3 + tag_score * 0.15 + decision_boost

        candidates.sort(key=_score, reverse=True)

    return candidates[:limit]


async def get_unread_count(db: Session) -> int:
    """Get count of unread threads (threads with viewed_at = NULL).

    Args:
        db: Database session

    Returns:
        Count of unread pending threads
    """
    stmt = (
        select(func.count(Thread.id))
        .where(Thread.viewed_at.is_(None))
        .where(Thread.status == ThreadStatus.PENDING)
    )

    result = db.execute(stmt)
    return result.scalar() or 0


async def get_thread_with_messages(db: Session, thread_id: str) -> Optional[Thread]:
    """Get a thread with all its messages loaded.

    Args:
        db: Database session
        thread_id: ID of the thread

    Returns:
        Thread object with messages relationship loaded, or None if not found
    """
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        return None

    # Explicitly load messages (they should be loaded via relationship)
    # This ensures messages are ordered chronologically
    thread.messages.sort(key=lambda m: m.created_at)

    return thread


async def list_threads(
    db: Session,
    status: Optional[ThreadStatus] = None,
    corps_id: Optional[str] = None,
    limit: int = 100,
) -> List[Thread]:
    """List threads with optional filtering.

    Args:
        db: Database session
        status: Filter by status (PENDING or COMPLETED)
        corps_id: Filter by corps ID
        limit: Maximum number of results

    Returns:
        List of Thread objects ordered by most recently updated
    """
    stmt = select(Thread)

    if status:
        stmt = stmt.where(Thread.status == status)

    if corps_id:
        stmt = stmt.where(Thread.corps_id == corps_id)

    stmt = stmt.order_by(Thread.updated_at.desc()).limit(limit)

    result = db.execute(stmt)
    return list(result.scalars().all())
