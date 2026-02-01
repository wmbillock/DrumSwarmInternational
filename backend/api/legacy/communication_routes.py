"""Legacy communication/chat endpoints extracted from app.py."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.app import get_db, get_task_manager, manager, SessionFactory

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Pydantic Schemas ---

class MessageCreate(BaseModel):
    from_role: str
    type: str
    subject: str
    body: Optional[str] = None
    to_role: Optional[str] = None
    priority: str = "normal"
    segment_id: Optional[str] = None

class ChatSend(BaseModel):
    content: str
    to_role: str = "executive_director"


# --- Chat context builder ---

def _build_chat_agent_context(
    db: Session, corps_id: str, to_role: str, content: str, session_id: str
) -> tuple[str, Optional[str]]:
    """Build task_description with chat history and load context snapshot for an agent.

    Returns (task_description, context_snapshot).
    """
    from backend.models.show import Show as ShowModel
    from backend.models.message import Message
    from backend.models.agent_session import AgentSession

    # Load recent chat history (last 20 messages)
    recent_msgs = (
        db.query(Message)
        .filter(Message.corps_id == corps_id)
        .order_by(Message.created_at.desc())
        .limit(20)
        .all()
    )
    recent_msgs.reverse()  # chronological order

    # Build conversation context
    context_parts = []

    # Show context
    show = db.query(ShowModel).filter(ShowModel.corps_id == corps_id).first()
    if show:
        context_parts.append(f"Show: '{show.title}', Corps ID: {corps_id}")
        if show.segment_root_id:
            context_parts.append(f"Root segment ID: {show.segment_root_id}")
        if show.description:
            context_parts.append(f"Show description: {show.description}")

    # Chat history
    if len(recent_msgs) > 1:  # more than just the current message
        context_parts.append("\n--- Recent conversation ---")
        for m in recent_msgs[:-1]:  # exclude current message (already the latest)
            sender = "User" if m.from_role == "user" else m.from_role
            msg_text = m.body or m.subject
            if len(msg_text) > 300:
                msg_text = msg_text[:300] + "..."
            context_parts.append(f"{sender}: {msg_text}")
        context_parts.append("--- End conversation ---\n")

    # Current message
    context_parts.append(f"User message to {to_role}: {content}")
    context_parts.append(
        "Respond to the user's message. You have the conversation history above for context. "
        "Continue the conversation naturally. Use your tools to take action when requested. "
        "If the user is asking you to do work, create segments and reps under the root segment."
    )

    # Load context snapshot from session
    snapshot = None
    session = db.get(AgentSession, session_id)
    if session and session.context_snapshot:
        snapshot = session.context_snapshot

    return "\n".join(context_parts), snapshot


# --- Message endpoints ---

@router.post("/api/corps/{corps_id}/messages")
def api_send_message(corps_id: str, data: MessageCreate, db: Session = Depends(get_db)):
    from backend.models.message import MessageType, MessagePriority
    from backend.services.message_service import send_message, InvalidMessagePath, InvalidMessageType
    try:
        msg = send_message(
            db, corps_id=corps_id, from_role=data.from_role,
            type=MessageType(data.type), subject=data.subject, body=data.body,
            to_role=data.to_role, priority=MessagePriority(data.priority),
            segment_id=data.segment_id,
        )
        return {"id": msg.id, "type": msg.type.value, "subject": msg.subject}
    except (ValueError, InvalidMessagePath, InvalidMessageType) as e:
        raise HTTPException(400, str(e))


@router.get("/api/corps/{corps_id}/messages")
def api_poll_messages(corps_id: str, role: Optional[str] = None, db: Session = Depends(get_db)):
    from backend.services.message_service import poll_messages
    msgs = poll_messages(db, corps_id=corps_id, role=role)
    return [{"id": m.id, "type": m.type.value, "from_role": m.from_role,
             "to_role": m.to_role, "subject": m.subject, "priority": m.priority.value,
             "acknowledged_at": m.acknowledged_at.isoformat() if m.acknowledged_at else None
             } for m in msgs]


# --- Chat endpoints ---

@router.post("/api/corps/{corps_id}/chat")
async def api_send_chat(corps_id: str, data: ChatSend, db: Session = Depends(get_db)):
    """Send a user message to an agent role. Creates a message record and wakes the target agent."""
    from backend.models.message import MessageType, MessagePriority
    from backend.services.message_service import send_message

    # Record the message
    msg = send_message(
        db, corps_id=corps_id, from_role="user",
        to_role=data.to_role, type=MessageType.DIRECTIVE,
        subject=data.content[:100], body=data.content,
        priority=MessagePriority.NORMAL,
    )

    # Broadcast to WebSocket
    await manager.broadcast(corps_id, {
        "type": "chat",
        "from_role": "user",
        "to_role": data.to_role,
        "content": data.content,
        "message_id": msg.id,
    })

    # Wake target agent via task_manager — include chat history so agent has context
    tm = get_task_manager()
    if tm:
        session_id = tm.get_session_for_role(db, corps_id, data.to_role)
        if session_id and not tm.is_active(session_id):
            task_desc, snapshot = _build_chat_agent_context(
                db, corps_id, data.to_role, data.content, session_id
            )
            tm.start_agent(
                session_id=session_id,
                task_description=task_desc,
                corps_id=corps_id,
                context_snapshot=snapshot,
                reply_to_user=True,
            )

    return {"id": msg.id, "status": "sent"}


@router.get("/api/corps/{corps_id}/chat")
def api_get_chat_history(corps_id: str, db: Session = Depends(get_db)):
    """Get chat history — all messages for a corps, ordered chronologically."""
    from backend.models.message import Message
    msgs = (
        db.query(Message)
        .filter(Message.corps_id == corps_id)
        .order_by(Message.created_at)
        .all()
    )
    return [{
        "id": m.id,
        "type": m.type.value,
        "from_role": m.from_role,
        "to_role": m.to_role,
        "subject": m.subject,
        "body": m.body,
        "priority": m.priority.value,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "acknowledged_at": m.acknowledged_at.isoformat() if m.acknowledged_at else None,
    } for m in msgs]


# --- SSE Chat Stream ---

@router.post("/api/corps/{corps_id}/chat-stream")
async def api_chat_stream(corps_id: str, data: ChatSend, db: Session = Depends(get_db)):
    """Send a user message and stream agent responses via Server-Sent Events."""
    import asyncio

    from backend.models.message import Message, MessageType, MessagePriority
    from backend.services.message_service import send_message

    # Record the user message
    msg = send_message(
        db, corps_id=corps_id, from_role="user",
        to_role=data.to_role, type=MessageType.DIRECTIVE,
        subject=data.content[:100], body=data.content,
        priority=MessagePriority.NORMAL,
    )

    # Broadcast user message
    await manager.broadcast(corps_id, {
        "type": "chat", "from_role": "user", "to_role": data.to_role,
        "content": data.content, "message_id": msg.id,
    })

    # Wake target agent
    tm = get_task_manager()
    if tm:
        session_id = tm.get_session_for_role(db, corps_id, data.to_role)
        if session_id and not tm.is_active(session_id):
            task_desc, snapshot = _build_chat_agent_context(
                db, corps_id, data.to_role, data.content, session_id
            )
            tm.start_agent(
                session_id=session_id,
                task_description=task_desc,
                corps_id=corps_id,
                context_snapshot=snapshot,
                reply_to_user=True,
            )

    # Track messages we've already sent
    last_msg_count = db.query(Message).filter(Message.corps_id == corps_id).count()

    async def event_stream():
        """Poll for new messages and yield them as SSE events."""
        yield f"data: {json.dumps({'type': 'connected', 'message_id': msg.id})}\n\n"

        polls_without_new = 0
        max_polls = 120  # ~60 seconds at 500ms intervals
        nonlocal last_msg_count

        for _ in range(max_polls):
            await asyncio.sleep(0.5)
            poll_db = SessionFactory()
            try:
                current_count = poll_db.query(Message).filter(Message.corps_id == corps_id).count()
                if current_count > last_msg_count:
                    new_msgs = (
                        poll_db.query(Message)
                        .filter(Message.corps_id == corps_id)
                        .order_by(Message.created_at.desc())
                        .limit(current_count - last_msg_count)
                        .all()
                    )
                    new_msgs.reverse()
                    last_msg_count = current_count

                    for m in new_msgs:
                        event_data = {
                            "type": "message",
                            "id": m.id,
                            "from_role": m.from_role,
                            "to_role": m.to_role,
                            "content": m.body or m.subject,
                            "created_at": m.created_at.isoformat() if m.created_at else None,
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"
                    polls_without_new = 0
                else:
                    polls_without_new += 1

                # If the agent has been quiet for 10 seconds, check if it's still active
                if polls_without_new >= 20:
                    if tm:
                        session_id = tm.get_session_for_role(poll_db, corps_id, data.to_role)
                        if session_id and not tm.is_active(session_id):
                            yield f"data: {json.dumps({'type': 'done'})}\n\n"
                            return
            finally:
                poll_db.close()

        yield f"data: {json.dumps({'type': 'timeout'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
