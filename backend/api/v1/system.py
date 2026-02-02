"""V1 API — System routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _get_db_session, _get_llm_client

router = APIRouter(prefix="/api/v1")


@router.get("/system/health")
def v1_system_health():
    """Get swarm-wide health metrics."""
    from backend.services.system_health import get_swarm_health
    import dataclasses
    import logging
    db = _get_db_session()
    try:
        health = get_swarm_health(db)
        return dataclasses.asdict(health)
    except Exception as e:
        logging.getLogger(__name__).warning("Health check failed: %s", e)
        return {"status": "degraded", "error": str(e), "active_corps": 0, "total_agents": 0}
    finally:
        db.close()


@router.get("/system/llm-usage")
def v1_llm_usage():
    """Get LLM provider usage statistics from the SmartRouter."""
    from backend.services.llm_client import SmartRouter

    llm_client = _get_llm_client()
    if llm_client is None:
        raise HTTPException(503, "LLM client not available")

    if isinstance(llm_client, SmartRouter):
        return llm_client.get_usage_stats()

    return {
        "active_provider": type(llm_client).__name__,
        "started_at": None,
        "providers": [{
            "name": type(llm_client).__name__,
            "capabilities": {
                "supports_images": llm_client.supports_images,
                "supports_native_tools": llm_client.supports_native_tools,
                "supports_caching": llm_client.supports_caching,
            },
            "stats": {"requests": 0, "successes": 0, "failures": 0,
                      "total_input_tokens": 0, "total_output_tokens": 0, "total_cached_tokens": 0},
        }],
        "failover_events": [],
        "total_requests": 0,
        "total_failures": 0,
    }


@router.get("/system/agents")
def v1_agents_overview():
    """Get all active agent sessions across all corps."""
    from sqlalchemy.orm import joinedload
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.agent_definition import AgentDefinition
    from backend.models.corps import Corps

    db = _get_db_session()
    try:
        sessions = (
            db.query(AgentSession)
            .options(joinedload(AgentSession.definition))
            .filter(AgentSession.status == SessionStatus.ACTIVE)
            .all()
        )

        corps_ids = {s.corps_id for s in sessions if s.corps_id}
        corps_map = {}
        if corps_ids:
            corps_records = db.query(Corps).filter(Corps.id.in_(corps_ids)).all()
            corps_map = {c.id: c for c in corps_records}

        return [{
            "id": s.id,
            "definition_id": s.definition_id,
            "role": s.definition.role if s.definition else "unknown",
            "nickname": s.definition.nickname if s.definition else None,
            "classification": s.definition.classification.value if s.definition and s.definition.classification else None,
            "model_tier": s.definition.model_tier.value if s.definition else "unknown",
            "status": s.status.value,
            "corps_id": s.corps_id,
            "corps_name": corps_map[s.corps_id].name if s.corps_id and s.corps_id in corps_map else None,
            "started_at": s.started_at.isoformat() if s.started_at else None,
        } for s in sessions]
    finally:
        db.close()


@router.get("/system/work-log")
def v1_global_work_log(limit: int = 100, event_type: Optional[str] = None):
    """Get work log across all corps."""
    from backend.models.work_log import WorkLog
    from backend.models.agent_session import AgentSession
    from backend.models.agent_definition import AgentDefinition

    db = _get_db_session()
    try:
        query = db.query(WorkLog)
        if event_type:
            query = query.filter(WorkLog.event_type == event_type)
        logs = query.order_by(WorkLog.timestamp.desc()).limit(limit).all()

        session_ids = {log.session_id for log in logs if log.session_id}
        nicknames = {}
        if session_ids:
            sessions = db.query(AgentSession).filter(AgentSession.id.in_(session_ids)).all()
            defn_ids = {s.definition_id for s in sessions if s.definition_id}
            defns = {d.id: d for d in db.query(AgentDefinition).filter(AgentDefinition.id.in_(defn_ids)).all()} if defn_ids else {}
            for s in sessions:
                defn = defns.get(s.definition_id)
                if defn and defn.nickname:
                    nicknames[s.id] = defn.nickname

        return [{
            "id": log.id,
            "session_id": log.session_id,
            "corps_id": log.corps_id,
            "role": log.role,
            "nickname": nicknames.get(log.session_id),
            "event_type": log.event_type,
            "phase": log.phase,
            "details": log.details,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        } for log in logs]
    finally:
        db.close()


@router.get("/system/budget")
def get_budget():
    """Return budget tracking stats and configuration."""
    from backend.services.budget_manager import get_budget_manager
    return get_budget_manager().get_stats()


@router.get("/system/processes")
def get_processes():
    """Return process registry stats."""
    from backend.services.process_registry import get_process_registry
    return get_process_registry().get_stats()
