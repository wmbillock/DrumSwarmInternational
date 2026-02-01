"""Chat agent context builder — extracted from legacy communication routes."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def build_chat_agent_context(
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
