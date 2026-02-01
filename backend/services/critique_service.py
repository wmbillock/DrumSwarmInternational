"""Critique service — multi-turn judge-to-staff conversations for post-competition feedback."""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.agent_definition import ModelTier
from backend.models.critique_session import CritiqueSession, CritiqueStatus
from backend.models.judges_tape import JudgesTape
from backend.services.llm_client import LLMClient, LLMMessage

logger = logging.getLogger(__name__)

# Judge type → staff role routing
JUDGE_TO_STAFF = {
    "brass": "brass_caption_head",
    "percussion": "percussion_caption_head",
    "guard": "guard_caption_head",
    "visual": "visual_caption_head",
    "general_effect": "program_coordinator",
    "ensemble_technique": "executive_director",
    "timing": "timing_judge",
}


def start_critique(
    db: Session,
    competition_id: str,
    corps_id: str,
    judge_type: str,
    llm_client: Optional[LLMClient] = None,
) -> CritiqueSession:
    """Initialize a critique session. Judge provides opening critique based on tape."""
    staff_role = JUDGE_TO_STAFF.get(judge_type, "program_coordinator")

    # Get tape context
    tape = db.query(JudgesTape).filter(
        JudgesTape.competition_id == competition_id,
        JudgesTape.corps_id == corps_id,
    ).order_by(JudgesTape.created_at.desc()).first()

    tape_context = ""
    if tape and tape.caption_feedbacks:
        feedback = tape.caption_feedbacks.get(judge_type, {})
        tape_context = f"Score: {feedback.get('value', 'N/A')}\nFeedback: {feedback.get('feedback', 'None')}\n"
        if tape.overall_assessment:
            tape_context += f"Overall: {tape.overall_assessment[:500]}\n"

    # Generate opening critique
    opening = f"Based on my evaluation of this corps' {judge_type} performance:\n{tape_context}\nWhat aspects would you like to discuss?"
    if llm_client and tape_context:
        try:
            messages = [
                LLMMessage(role="system", content=f"You are a DCI {judge_type} judge providing post-competition critique to the {staff_role}. Be specific, constructive, and reference the performance data. Start with your key observations and invite discussion."),
                LLMMessage(role="user", content=f"Competition: {competition_id}\nCorps: {corps_id}\n\nTape data:\n{tape_context}\n\nProvide your opening critique."),
            ]
            resp = llm_client.chat(messages, model_tier=ModelTier.HAIKU)
            opening = resp.content.strip()
        except Exception as e:
            logger.warning("Failed to generate opening critique: %s", e)

    conversation = [{"role": "judge", "content": opening}]

    session = CritiqueSession(
        competition_id=competition_id,
        corps_id=corps_id,
        judge_type=judge_type,
        staff_role=staff_role,
        conversation=conversation,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def send_message(
    db: Session,
    session_id: str,
    message: str,
    llm_client: Optional[LLMClient] = None,
) -> CritiqueSession:
    """Multi-turn: staff asks, judge responds (grounded in tape + scores)."""
    session = db.get(CritiqueSession, session_id)
    if not session:
        raise ValueError(f"Critique session {session_id} not found")
    if session.status == CritiqueStatus.COMPLETED:
        raise ValueError("Critique session already completed")

    conversation = list(session.conversation or [])
    conversation.append({"role": "staff", "content": message})

    # Generate judge response
    judge_response = "Thank you for that question. Let me address it based on my observations."
    if llm_client:
        try:
            llm_messages = [
                LLMMessage(role="system", content=f"You are a DCI {session.judge_type} judge in a post-competition critique session with the {session.staff_role}. Stay grounded in the performance data. Be constructive and specific."),
            ]
            for turn in conversation:
                role = "assistant" if turn["role"] == "judge" else "user"
                llm_messages.append(LLMMessage(role=role, content=turn["content"]))

            resp = llm_client.chat(llm_messages, model_tier=ModelTier.HAIKU)
            judge_response = resp.content.strip()
        except Exception as e:
            logger.warning("Failed to generate judge response: %s", e)

    conversation.append({"role": "judge", "content": judge_response})
    session.conversation = conversation
    db.commit()
    db.refresh(session)
    return session


def complete_critique(
    db: Session,
    session_id: str,
    llm_client: Optional[LLMClient] = None,
) -> CritiqueSession:
    """Complete critique session — extract action items."""
    session = db.get(CritiqueSession, session_id)
    if not session:
        raise ValueError(f"Critique session {session_id} not found")

    conversation = session.conversation or []

    # Extract action items via LLM
    action_items = ""
    if llm_client and conversation:
        conv_text = "\n".join(f"[{t['role']}] {t['content']}" for t in conversation)
        try:
            messages = [
                LLMMessage(role="system", content="Extract specific, actionable improvement items from this critique conversation. Output as a numbered list."),
                LLMMessage(role="user", content=conv_text),
            ]
            resp = llm_client.chat(messages, model_tier=ModelTier.HAIKU)
            action_items = resp.content.strip()
        except Exception as e:
            logger.warning("Failed to extract action items: %s", e)

    if not action_items:
        # Fallback: extract from judge messages
        items = []
        for turn in conversation:
            if turn["role"] == "judge" and "should" in turn["content"].lower():
                items.append(turn["content"][:200])
        action_items = "\n".join(f"- {item}" for item in items[:5]) if items else "No action items extracted."

    session.action_items = action_items
    session.status = CritiqueStatus.COMPLETED
    session.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    return session
