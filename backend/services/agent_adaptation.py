"""Agent adaptation — prompt modification and retirement based on critique feedback."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.agent_definition import AgentDefinition, ModelTier
from backend.models.critique_session import CritiqueSession, CritiqueStatus
from backend.services.llm_client import LLMClient, LLMMessage

logger = logging.getLogger(__name__)

# Trust thresholds
ADAPTATION_TRIGGER_TRUST = 40
ADAPTATION_MIN_SESSIONS = 5
RETIREMENT_MAX_ATTEMPTS = 3


def adapt_agent(
    db: Session,
    agent_id: str,
    critique_summary: str,
    llm_client: Optional[LLMClient] = None,
) -> Optional[AgentDefinition]:
    """Analyze critique + current system_prompt, propose prompt modifications.

    Creates a new AgentDefinition version with improved prompt.
    Returns the new definition, or None if adaptation not possible.
    """
    current = db.query(AgentDefinition).filter(
        AgentDefinition.id == agent_id
    ).first()
    if not current:
        logger.warning("Agent %s not found for adaptation", agent_id)
        return None

    current_prompt = current.system_prompt or ""
    role = current.role or "unknown"

    if not llm_client:
        logger.info("No LLM client — skipping adaptation for agent %s", agent_id)
        return None

    try:
        messages = [
            LLMMessage(role="system", content="""You are an AI system prompt engineer. Given an agent's current system prompt and critique feedback, produce an improved system prompt that addresses the weaknesses while maintaining strengths.

Output ONLY the new system prompt text, nothing else."""),
            LLMMessage(role="user", content=f"""Agent role: {role}
Corps: {current.corps_id}

Current system prompt:
{current_prompt[:3000]}

Critique feedback:
{critique_summary[:2000]}

Generate an improved system prompt that addresses the critique."""),
        ]
        resp = llm_client.chat(messages, model_tier=ModelTier.HAIKU)
        new_prompt = resp.content.strip()
    except Exception as e:
        logger.error("Adaptation LLM call failed: %s", e)
        return None

    if not new_prompt or len(new_prompt) < 50:
        return None

    # Create new version
    new_version = (current.version or 0) + 1
    new_def = AgentDefinition(
        id=str(uuid.uuid4()),
        corps_id=current.corps_id,
        role=current.role,
        system_prompt=new_prompt,
        version=new_version,
        model_tier=current.model_tier,
    )
    db.add(new_def)
    db.commit()
    db.refresh(new_def)

    logger.info("Created adapted definition %s (v%d) for agent %s", new_def.id, new_version, agent_id)
    return new_def


def check_adaptation_triggers(db: Session, llm_client: Optional[LLMClient] = None) -> list[dict]:
    """Scan for agents that need adaptation based on critique outcomes.

    Returns list of adaptation attempts with results.
    """
    # Find agents with completed critique sessions that have action items
    completed_critiques = db.query(CritiqueSession).filter(
        CritiqueSession.status == CritiqueStatus.COMPLETED,
        CritiqueSession.action_items.isnot(None),
    ).all()

    results = []
    seen_corps = set()

    for critique in completed_critiques:
        key = f"{critique.corps_id}:{critique.judge_type}"
        if key in seen_corps:
            continue
        seen_corps.add(key)

        # Find the relevant agent definition
        definitions = db.query(AgentDefinition).filter(
            AgentDefinition.corps_id == critique.corps_id,
            AgentDefinition.role.contains(critique.staff_role),
        ).all()

        for defn in definitions:
            new_def = adapt_agent(db, defn.id, critique.action_items or "", llm_client)
            results.append({
                "agent_id": defn.id,
                "corps_id": critique.corps_id,
                "role": defn.role,
                "adapted": new_def is not None,
                "new_definition_id": new_def.id if new_def else None,
            })

    return results


def retire_agent(db: Session, agent_id: str, reason: str) -> bool:
    """Set agent version = -1 (existing retirement pattern)."""
    defn = db.query(AgentDefinition).filter(AgentDefinition.id == agent_id).first()
    if not defn:
        return False

    defn.version = -1
    db.commit()
    logger.info("Retired agent %s: %s", agent_id, reason)
    return True


def get_adaptation_history(db: Session, corps_id: str) -> list[dict]:
    """Get all agent definitions for a corps, showing version history."""
    definitions = db.query(AgentDefinition).filter(
        AgentDefinition.corps_id == corps_id
    ).order_by(AgentDefinition.role, AgentDefinition.version.desc()).all()

    history = []
    for d in definitions:
        history.append({
            "id": d.id,
            "role": d.role,
            "version": d.version,
            "retired": d.version == -1,
            "prompt_preview": (d.system_prompt or "")[:200],
        })

    return history
