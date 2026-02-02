"""V1 API routes for asynchronous messaging.

Extracted from router.py — all messaging thread and archive endpoints.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _validate_id, _get_db_session
from backend.api.v1.schemas import (
    MessagingCreateThreadRequest,
    MessagingAddMessageRequest,
    MessagingMarkThreadCompleteRequest,
    MessagingBulkArchiveRequest,
)

router = APIRouter(prefix="/api/v1")


@router.get("/messaging/unread-count")
def v1_get_unread_message_count():
    """Get count of unread messages (pending threads)."""
    from backend.services.messaging_service import MessagingService

    db = _get_db_session()
    try:
        service = MessagingService(db)
        count = service.get_unread_count()
        return {"unread_count": count}
    finally:
        db.close()


@router.post("/messaging/threads")
def v1_create_messaging_thread(req: MessagingCreateThreadRequest):
    """Create a new messaging thread with an initial message.

    Permission: Only EDs and PCs can create threads.
    """
    from backend.services.messaging_service import MessagingService
    from backend.services.messaging_permissions import MessagingPermissions

    # Check permissions
    if not MessagingPermissions.can_create_thread(req.user_role):
        raise HTTPException(
            403,
            f"User role '{req.user_role}' cannot create threads. "
            "Only Executive Directors and Program Coordinators may initiate threads.",
        )

    db = _get_db_session()
    try:
        service = MessagingService(db)
        thread = service.create_thread(
            originator_role=req.originator_role,
            subject=req.subject,
            initial_message_body=req.initial_message_body,
            initial_sender_name=req.initial_sender_name or "Agent",
        )
        return {
            "thread_id": thread.id,
            "originator_role": thread.originator_role.value,
            "subject": thread.subject,
            "status": thread.status.value,
            "created_at": thread.created_at.isoformat(),
            "message_count": len(thread.messages),
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to create thread: {e}")
    finally:
        db.close()


@router.get("/messaging/threads")
def v1_list_messaging_threads(
    status: Optional[str] = None,
    originator_role: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List active messaging threads with optional filtering."""
    from backend.services.messaging_service import MessagingService

    db = _get_db_session()
    try:
        service = MessagingService(db)
        threads, total = service.list_threads(
            status=status,
            originator_role=originator_role,
            limit=limit,
            offset=offset,
        )
        return {
            "threads": [
                {
                    "thread_id": t.id,
                    "originator_role": t.originator_role.value,
                    "subject": t.subject,
                    "status": t.status.value,
                    "created_at": t.created_at.isoformat(),
                    "updated_at": t.updated_at.isoformat(),
                    "message_count": len(t.messages),
                    "archive_candidate_at": t.archive_candidate_at.isoformat()
                    if t.archive_candidate_at
                    else None,
                }
                for t in threads
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    finally:
        db.close()


@router.get("/messaging/threads/{thread_id}")
def v1_get_messaging_thread(thread_id: str):
    """Get a messaging thread with all its messages."""
    from backend.services.messaging_service import MessagingService

    _validate_id(thread_id, "thread_id")

    db = _get_db_session()
    try:
        service = MessagingService(db)
        thread = service.get_thread(thread_id)
        if not thread:
            raise HTTPException(404, f"Thread {thread_id} not found")

        return {
            "thread_id": thread.id,
            "originator_role": thread.originator_role.value,
            "subject": thread.subject,
            "status": thread.status.value,
            "created_at": thread.created_at.isoformat(),
            "updated_at": thread.updated_at.isoformat(),
            "completed_at": thread.completed_at.isoformat()
            if thread.completed_at
            else None,
            "completed_by": thread.completed_by,
            "messages": [
                {
                    "message_id": m.id,
                    "sender_type": m.sender_type.value,
                    "sender_role": m.sender_role,
                    "sender_name": m.sender_name,
                    "body": m.body,
                    "created_at": m.created_at.isoformat(),
                }
                for m in sorted(thread.messages, key=lambda x: x.created_at)
            ],
        }
    finally:
        db.close()


@router.post("/messaging/threads/{thread_id}/messages")
def v1_add_messaging_thread_message(thread_id: str, req: MessagingAddMessageRequest):
    """Add a message to an existing thread."""
    from backend.services.messaging_service import MessagingService

    _validate_id(thread_id, "thread_id")

    db = _get_db_session()
    try:
        service = MessagingService(db)
        message = service.add_message_to_thread(
            thread_id=thread_id,
            sender_type=req.sender_type,
            sender_role=req.sender_role,
            sender_name=req.sender_name,
            body=req.body,
        )
        return {
            "message_id": message.id,
            "thread_id": message.thread_id,
            "sender_type": message.sender_type.value,
            "sender_role": message.sender_role,
            "sender_name": message.sender_name,
            "body": message.body,
            "created_at": message.created_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to add message: {e}")
    finally:
        db.close()


@router.patch("/messaging/threads/{thread_id}")
def v1_mark_messaging_thread_complete(
    thread_id: str, req: MessagingMarkThreadCompleteRequest
):
    """Mark a messaging thread as completed.

    Permission: Only admins or the ED/PC originator can mark it complete.
    """
    from backend.services.messaging_service import MessagingService
    from backend.services.messaging_permissions import MessagingPermissions

    _validate_id(thread_id, "thread_id")

    db = _get_db_session()
    try:
        service = MessagingService(db)
        thread = service.get_thread(thread_id)
        if not thread:
            raise HTTPException(404, f"Thread {thread_id} not found")

        # Check permissions: admin or originator can mark complete
        is_originator = req.completed_by_user_role == thread.originator_role.value
        if not MessagingPermissions.can_mark_thread_complete(
            user_role=req.completed_by_user_role,
            thread_originator_role=thread.originator_role.value,
            is_originator=is_originator,
        ):
            raise HTTPException(
                403,
                "Only admins or the thread originator (ED/PC) can mark threads complete.",
            )

        thread = service.mark_thread_complete(thread_id, req.completed_by_user_id)
        return {
            "thread_id": thread.id,
            "status": thread.status.value,
            "completed_at": thread.completed_at.isoformat(),
            "completed_by": thread.completed_by,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to mark thread complete: {e}")
    finally:
        db.close()


@router.get("/messaging/archive")
def v1_list_archived_threads(
    search: Optional[str] = None,
    originator_role: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user_role: Optional[str] = None,
):
    """List archived messaging threads with optional search and filtering.

    Permission: Admins (full access) and EDs (read-only).
    """
    from backend.services.messaging_service import MessagingService
    from backend.services.messaging_permissions import MessagingPermissions

    # Check permissions
    if user_role and not MessagingPermissions.can_search_archive(user_role):
        raise HTTPException(
            403,
            f"User role '{user_role}' cannot search archives. "
            "Only Admins and Executive Directors may access archived threads.",
        )

    db = _get_db_session()
    try:
        service = MessagingService(db)
        threads, total = service.list_archived_threads(
            search_query=search,
            originator_role=originator_role,
            limit=limit,
            offset=offset,
        )
        return {
            "archived_threads": [
                {
                    "archived_thread_id": t.id,
                    "original_thread_id": t.original_thread_id,
                    "originator_role": t.originator_role,
                    "subject": t.subject,
                    "summary": t.summary,
                    "message_count": t.message_count,
                    "created_at": t.created_at.isoformat(),
                    "archived_at": t.archived_at.isoformat(),
                    "tags": t.tags.split(",") if t.tags else [],
                    "decision": t.decision,
                }
                for t in threads
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    finally:
        db.close()


@router.get("/messaging/archive/{archived_thread_id}")
def v1_get_archived_messaging_thread(archived_thread_id: str):
    """Get an archived messaging thread (read-only view)."""
    from backend.services.messaging_service import MessagingService

    _validate_id(archived_thread_id, "archived_thread_id")

    db = _get_db_session()
    try:
        service = MessagingService(db)
        thread = service.get_archived_thread(archived_thread_id)
        if not thread:
            raise HTTPException(404, f"Archived thread {archived_thread_id} not found")

        return {
            "archived_thread_id": thread.id,
            "original_thread_id": thread.original_thread_id,
            "originator_role": thread.originator_role,
            "subject": thread.subject,
            "summary": thread.summary,
            "message_count": thread.message_count,
            "created_at": thread.created_at.isoformat(),
            "archived_at": thread.archived_at.isoformat(),
            "archived_by": thread.archived_by,
            "full_text": thread.full_text,
            "tags": thread.tags.split(",") if thread.tags else [],
            "decision": thread.decision,
        }
    finally:
        db.close()


@router.post("/messaging/archive/bulk-archive")
def v1_bulk_archive_messaging_threads(req: MessagingBulkArchiveRequest):
    """Bulk-archive completed threads with LLM-generated summaries.

    Returns operation summary with count and metadata of archived threads.
    Permission: Admins only.
    """
    from backend.services.messaging_service import MessagingService
    from backend.services.messaging_permissions import MessagingPermissions

    # Check permissions
    if not MessagingPermissions.can_bulk_archive_threads(req.archived_by_user_role):
        raise HTTPException(
            403,
            "Only Admins can bulk-archive threads. "
            "Agents cannot archive to prevent accidental data loss.",
        )

    db = _get_db_session()
    try:
        service = MessagingService(db)

        # Get threads to archive
        threads_to_archive = []
        for thread_id in req.thread_ids:
            thread = service.get_thread(thread_id)
            if thread:
                threads_to_archive.append(thread)

        if not threads_to_archive:
            raise HTTPException(400, "No valid threads found to archive")

        # Generate LLM-based summaries and extract decisions + tags
        from backend.services.messaging_summary_service import generate_thread_summary

        summaries = {}
        decisions = {}
        tags_dict = {}

        for thread in threads_to_archive:
            # Prepare message data for LLM
            message_data = [
                {
                    "sender_name": m.sender_name,
                    "body": m.body,
                    "created_at": m.created_at.isoformat(),
                }
                for m in thread.messages
            ]

            # Generate summary via LLM (with fallback)
            summary, decision, tags = generate_thread_summary(
                subject=thread.subject, messages=message_data
            )
            summaries[thread.id] = summary
            decisions[thread.id] = decision
            tags_dict[thread.id] = tags

        # Archive threads
        archived = service.archive_threads(
            thread_ids=req.thread_ids,
            archived_by_user_id=req.archived_by_user_id,
            summaries=summaries,
            decisions=decisions,
            tags_dict=tags_dict,
        )

        return {
            "operation_id": str(uuid.uuid4()),
            "count_archived": len(archived),
            "archived_threads": [
                {
                    "archived_thread_id": at.id,
                    "original_thread_id": at.original_thread_id,
                    "subject": at.subject,
                    "summary": at.summary,
                }
                for at in archived
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to bulk-archive threads: {e}")
    finally:
        db.close()
