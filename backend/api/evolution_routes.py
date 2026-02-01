"""Evolution & Talent Pool API routes — selection events, genome metadata, mutation simulation."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session


router = APIRouter()


def _get_db():
    from backend.api.app import get_db
    return get_db()


@router.get("/api/evolution/performers/{performer_id}/genome")
def api_get_performer_genome(performer_id: str, db: Session = Depends(_get_db)):
    """Get the full agent genome — capabilities, tool access, prompt version, performance summary.

    The genome is the complete identity of an agent across its lifecycle.
    """
    from backend.models.performer import Performer
    from backend.models.agent_session import AgentSession
    from backend.models.agent_definition import AgentDefinition
    from backend.services.capability_ledger_service import get_performer_stats

    performer = db.get(Performer, performer_id)
    if not performer:
        raise HTTPException(404, "Performer not found")

    # Get stats from capability ledger
    stats = get_performer_stats(db, performer_id)

    # Find the most recent definition used by this performer
    latest_session = (
        db.query(AgentSession)
        .filter(AgentSession.performer_id == performer_id)
        .order_by(AgentSession.started_at.desc())
        .first()
    )

    definition_genome = None
    if latest_session and latest_session.definition_id:
        defn = db.get(AgentDefinition, latest_session.definition_id)
        if defn:
            definition_genome = {
                "definition_id": defn.id,
                "role": defn.role,
                "model_tier": defn.model_tier.value,
                "tools_allowed": defn.tools_allowed_list,
                "version": defn.version,
                "classification": defn.classification.value if defn.classification else None,
                "nickname": defn.nickname,
                "system_prompt_length": len(defn.system_prompt) if defn.system_prompt else 0,
                "corps_id": defn.corps_id,
            }

    success_rate = (
        performer.successful_sessions / performer.total_sessions
        if performer.total_sessions > 0 else 0
    )

    return {
        "performer_id": performer.id,
        "name": performer.name,
        "role_type": performer.role_type,
        "status": performer.status.value,
        "age": performer.age,
        "experience_seasons": performer.experience_seasons,
        "trust_score": round(performer.trust_score, 1),
        "specialties": performer.specialties,
        "performance": {
            "total_sessions": performer.total_sessions,
            "successful_sessions": performer.successful_sessions,
            "failed_sessions": performer.failed_sessions,
            "success_rate": round(success_rate, 3),
            "reps_completed": stats.get("reps_completed", 0),
            "reps_failed": stats.get("reps_failed", 0),
            "avg_score": stats.get("avg_score"),
            "gupp_violations": stats.get("gupp_violations", 0),
        },
        "definition": definition_genome,
    }


@router.get("/api/evolution/events")
def api_get_selection_events(
    event_type: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(_get_db),
):
    """Get selection events — promotions, retirements, mutations, trust changes.

    These are the capability ledger entries that represent evolutionary pressure.
    """
    from backend.models.capability_ledger import CapabilityLedgerEntry, LedgerEntryType

    q = db.query(CapabilityLedgerEntry)

    if event_type:
        try:
            et = LedgerEntryType(event_type)
            q = q.filter(CapabilityLedgerEntry.entry_type == et)
        except ValueError:
            raise HTTPException(400, f"Invalid event type: {event_type}")

    entries = q.order_by(CapabilityLedgerEntry.created_at.desc()).limit(limit).all()

    return [
        {
            "id": e.id,
            "performer_id": e.performer_id,
            "performer_name": e.performer_name,
            "role_type": e.role_type,
            "entry_type": e.entry_type.value,
            "corps_id": e.corps_id,
            "session_id": e.session_id,
            "rep_id": e.rep_id,
            "score": e.score,
            "trust_before": e.trust_before,
            "trust_after": e.trust_after,
            "details": e.details,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


@router.get("/api/evolution/mutations")
def api_get_mutations(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(_get_db),
):
    """Get self-improvement proposals (mutations) with their rationale."""
    from backend.models.self_improvement_log import SelfImprovementLog, ImprovementStatus
    from backend.models.agent_definition import AgentDefinition

    q = db.query(SelfImprovementLog)
    if status:
        try:
            st = ImprovementStatus(status)
            q = q.filter(SelfImprovementLog.status == st)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")

    logs = q.order_by(SelfImprovementLog.created_at.desc()).limit(limit).all()

    results = []
    for log in logs:
        defn = db.get(AgentDefinition, log.agent_definition_id)
        try:
            changes = json.loads(log.changes) if isinstance(log.changes, str) else log.changes
        except (json.JSONDecodeError, TypeError):
            changes = {}

        results.append({
            "id": log.id,
            "definition_id": log.agent_definition_id,
            "role": defn.role if defn else "unknown",
            "nickname": defn.nickname if defn else None,
            "old_version": log.old_version,
            "new_version": log.new_version,
            "changes": changes,
            "reason": log.reason,
            "status": log.status.value,
            "approved_by": log.approved_by,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return results


class MutationSimulation(BaseModel):
    definition_id: str
    changes: dict
    reason: str


@router.post("/api/evolution/simulate-mutation")
def api_simulate_mutation(data: MutationSimulation, db: Session = Depends(_get_db)):
    """Simulate a mutation (definition change) without applying it.

    Runs in sandbox mode: analyzes the proposed changes against the current definition
    and reports expected impact on the agent's capabilities. No state is modified.
    """
    from backend.models.agent_definition import AgentDefinition, MAJOR_CHANGE_FIELDS

    defn = db.get(AgentDefinition, data.definition_id)
    if not defn:
        raise HTTPException(404, "Agent definition not found")

    impacts = []
    risk_level = "low"
    requires_approval = False

    # Analyze each proposed change
    for field, new_value in data.changes.items():
        if field not in ("system_prompt", "tools_allowed", "model_tier", "nickname"):
            impacts.append({
                "field": field,
                "impact": "unknown_field",
                "description": f"Field '{field}' is not a mutable definition attribute.",
                "risk": "error",
            })
            continue

        current_value = getattr(defn, field, None)
        if field == "tools_allowed" and isinstance(current_value, str):
            current_value = [t.strip() for t in current_value.split(",") if t.strip()]

        if field in MAJOR_CHANGE_FIELDS:
            requires_approval = True
            risk_level = "high"

        if field == "model_tier":
            tier_order = {"haiku": 0, "sonnet": 1, "opus": 2}
            old_rank = tier_order.get(str(current_value), -1)
            new_rank = tier_order.get(str(new_value), -1)
            direction = "upgrade" if new_rank > old_rank else "downgrade" if new_rank < old_rank else "lateral"
            impacts.append({
                "field": field,
                "current": str(current_value),
                "proposed": str(new_value),
                "impact": f"Model tier {direction}",
                "description": f"{'Increased capability and cost' if direction == 'upgrade' else 'Reduced capability and cost' if direction == 'downgrade' else 'No change in capability'}.",
                "risk": "high" if direction == "upgrade" else "medium",
            })

        elif field == "tools_allowed":
            current_tools = set(defn.tools_allowed_list)
            new_tools = set(new_value) if isinstance(new_value, list) else set()
            added = new_tools - current_tools
            removed = current_tools - new_tools

            if added:
                impacts.append({
                    "field": field,
                    "impact": "tools_added",
                    "added": sorted(added),
                    "description": f"Agent gains access to {len(added)} new tool(s): {', '.join(sorted(added))}.",
                    "risk": "high",
                })
            if removed:
                impacts.append({
                    "field": field,
                    "impact": "tools_removed",
                    "removed": sorted(removed),
                    "description": f"Agent loses access to {len(removed)} tool(s): {', '.join(sorted(removed))}.",
                    "risk": "medium",
                })

        elif field == "system_prompt":
            old_len = len(defn.system_prompt or "")
            new_len = len(str(new_value))
            delta = new_len - old_len
            impacts.append({
                "field": field,
                "impact": "prompt_modified",
                "length_delta": delta,
                "old_length": old_len,
                "new_length": new_len,
                "description": f"System prompt {'expanded' if delta > 0 else 'reduced'} by {abs(delta)} characters.",
                "risk": "low",
            })

        elif field == "nickname":
            impacts.append({
                "field": field,
                "current": current_value,
                "proposed": new_value,
                "impact": "nickname_change",
                "description": "Cosmetic change only — no impact on capabilities.",
                "risk": "low",
            })

    return {
        "definition_id": data.definition_id,
        "role": defn.role,
        "current_version": defn.version,
        "proposed_version": defn.version + 1,
        "reason": data.reason,
        "risk_level": risk_level,
        "requires_approval": requires_approval,
        "impacts": impacts,
        "sandbox": True,
        "applied": False,
    }
