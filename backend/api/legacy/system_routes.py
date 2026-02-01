"""Legacy system/metronome/overview endpoints extracted from app.py."""

import json
import logging
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.app import get_db, get_task_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Pydantic Schemas ---

class SeasonCreate(BaseModel):
    name: str
    year: Optional[int] = None


# --- Work Log helper ---

def _nickname_lookup(db: Session, logs) -> dict[str, str]:
    """Build session_id->nickname lookup for a set of work log entries."""
    from backend.models.agent_session import AgentSession
    from backend.models.agent_definition import AgentDefinition
    session_ids = {log.session_id for log in logs if log.session_id}
    if not session_ids:
        return {}
    sessions = db.query(AgentSession).filter(AgentSession.id.in_(session_ids)).all()
    defn_ids = {s.definition_id for s in sessions if s.definition_id}
    defns = {d.id: d for d in db.query(AgentDefinition).filter(AgentDefinition.id.in_(defn_ids)).all()} if defn_ids else {}
    result = {}
    for s in sessions:
        defn = defns.get(s.definition_id)
        if defn and defn.nickname:
            result[s.id] = defn.nickname
    return result


# --- System Health ---

@router.get("/api/system-health")
def api_system_health(db: Session = Depends(get_db)):
    """Get swarm-wide health metrics for the overview dashboard."""
    from backend.services.system_health import get_swarm_health
    import dataclasses
    health = get_swarm_health(db)
    return dataclasses.asdict(health)


# --- Heartbeat ---

@router.post("/api/heartbeat")
async def api_heartbeat(db: Session = Depends(get_db)):
    """External heartbeat endpoint for cron-based wakeup."""
    import json
    from pathlib import Path
    from backend.services.metronome_heartbeat import heartbeat_tick
    from backend.tools.metronome_orchestrator import gather_corps_health, get_active_corps
    from datetime import datetime, timezone

    tick_timestamp = datetime.now(timezone.utc)

    # Execute brass section: command dispatch
    brass_result = heartbeat_tick(db)

    # Execute visual section: status gathering
    alerts = []
    try:
        active_corps = get_active_corps(db)
        corps_health_list = []

        for corps in active_corps:
            try:
                health = gather_corps_health(db, corps)

                # Check for RED FLAG: unresponsive corps
                if not health.ed_responding and not health.pc_responding:
                    alert = f"RED FLAG: Corps {health.corps_id[:8]} ({health.corps_name}) - No ED/PC response"
                    alerts.append(alert)
                    logger.warning(alert)

                corps_health_list.append({
                    "corps_id": health.corps_id,
                    "corps_name": health.corps_name,
                    "status": health.status,
                    "rehearsal_mode": health.rehearsal_mode,
                    "active_sessions": health.active_sessions,
                    "completed_sessions": health.completed_sessions,
                    "failed_sessions": health.failed_sessions,
                    "stalled_reps": len(health.stalled_reps),
                    "ed_responding": health.ed_responding,
                    "pc_responding": health.pc_responding,
                    "tick_duration_ms": health.tick_duration_ms,
                })
            except Exception as e:
                error_msg = f"Failed to gather health for corps {corps.id}: {e}"
                logger.error(error_msg)
                alerts.append(error_msg)

        visual_result = {
            "total_corps": len(active_corps),
            "corps_health": corps_health_list,
        }
    except Exception as e:
        error_msg = f"Failed to gather swarm status: {e}"
        logger.error(error_msg)
        visual_result = {
            "total_corps": 0,
            "corps_health": [],
            "error": str(e),
        }
        alerts.append(error_msg)

    # Build complete heartbeat result
    heartbeat_result = {
        "status": "ok",
        "timestamp": brass_result["timestamp"],
        "ten_hut_sent": brass_result["ten_hut"]["sent"],
        "resume_hut_sent": brass_result["resume_hut"]["sent"],
        "corps_pinged": brass_result["ten_hut"]["corps"],
        "stalled_corps": brass_result["resume_hut"]["stalled_corps"],
        "swarm_status": visual_result,
        "errors": brass_result["errors"] + alerts,
    }

    # Write structured logs
    try:
        log_dir = Path("logs/metronome")
        log_dir.mkdir(parents=True, exist_ok=True)

        # JSON log for machine readability
        timestamp_clean = tick_timestamp.isoformat().replace(":", "-").replace(".", "-")
        json_log_path = log_dir / f"{timestamp_clean}.json"

        with open(json_log_path, "w") as f:
            json.dump(heartbeat_result, f, indent=2)

        logger.info(f"Heartbeat tick logged to {json_log_path}")

        # Alert log for RED FLAGS
        if alerts:
            alert_log_path = log_dir / "alerts.log"
            with open(alert_log_path, "a") as f:
                for alert in alerts:
                    f.write(f"[{tick_timestamp.isoformat()}] {alert}\n")
            logger.warning(f"Wrote {len(alerts)} alerts to {alert_log_path}")

    except Exception as e:
        logger.error(f"Failed to write heartbeat logs: {e}")

    return heartbeat_result


# --- Metronome ---

@router.post("/api/corps/{corps_id}/metronome/tick")
def api_metronome_tick(corps_id: str, db: Session = Depends(get_db)):
    from backend.tools.metronome import tick
    result = tick(db, corps_id)
    return {
        "checked": result.checked,
        "reclaimed": result.reclaimed,
        "reclaimed_rep_ids": result.reclaimed_rep_ids,
    }


@router.post("/api/metronome/tick")
def api_metronome_system_tick(db: Session = Depends(get_db)):
    """System-wide metronome tick."""
    from backend.tools.metronome import tick
    from backend.services.corps_service import merge_monitor_check
    from backend.models.corps import Corps, CorpsStatus
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.agent_definition import AgentDefinition
    from backend.models.rep import Rep, RepStatus
    from datetime import datetime, timezone, timedelta

    STALLED_THRESHOLD_SECONDS = 300  # 5 minutes

    active_corps = (
        db.query(Corps)
        .filter(Corps.status.in_([CorpsStatus.WINTER_CAMPS, CorpsStatus.ON_TOUR]))
        .all()
    )

    corps_results = []
    for corps in active_corps:
        # Run the core metronome tick (reclaim, GUPP, watchdog)
        met_result = tick(db, corps.id)
        merge_result = merge_monitor_check(db, corps.id)

        # Gather session counts
        sessions = db.query(AgentSession).filter(AgentSession.corps_id == corps.id).all()
        active_sessions = sum(1 for s in sessions if s.status == SessionStatus.ACTIVE)
        completed_sessions = sum(1 for s in sessions if s.status == SessionStatus.COMPLETED)
        failed_sessions = sum(1 for s in sessions if s.status == SessionStatus.FAILED)

        # Gather rep counts
        from backend.models.show import Show
        from backend.models.segment import Segment
        show = db.query(Show).filter(Show.corps_id == corps.id).first()
        reps: list = []
        if show and show.segment_root_id:
            def _collect_segment_ids(seg_id):
                ids = [seg_id]
                children = db.query(Segment).filter(Segment.parent_id == seg_id).all()
                for c in children:
                    ids.extend(_collect_segment_ids(c.id))
                return ids
            seg_ids = _collect_segment_ids(show.segment_root_id)
            reps = db.query(Rep).filter(Rep.segment_id.in_(seg_ids)).all() if seg_ids else []
        rep_counts = {
            "pending": sum(1 for r in reps if r.status == RepStatus.PENDING),
            "assigned": sum(1 for r in reps if r.status == RepStatus.ASSIGNED),
            "in_progress": sum(1 for r in reps if r.status == RepStatus.IN_PROGRESS),
            "completed": sum(1 for r in reps if r.status == RepStatus.COMPLETED),
            "failed": sum(1 for r in reps if r.status == RepStatus.FAILED),
        }

        # Detect stalled work
        now = datetime.now(timezone.utc)
        stalled_reps = []
        for r in reps:
            if r.status in (RepStatus.PENDING, RepStatus.ASSIGNED) and r.updated_at:
                idle_secs = (now - r.updated_at.replace(tzinfo=timezone.utc)).total_seconds()
                if idle_secs > STALLED_THRESHOLD_SECONDS:
                    stalled_reps.append({
                        "rep_id": r.id,
                        "status": r.status.value,
                        "idle_seconds": round(idle_secs),
                        "last_updated": r.updated_at.isoformat(),
                    })

        # Agent liveness
        staff_roles = ["executive_director", "program_coordinator", "brass_caption_head",
                       "percussion_caption_head", "guard_caption_head", "visual_caption_head"]
        liveness = {}
        for role in staff_roles:
            role_sessions = (
                db.query(AgentSession)
                .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
                .filter(
                    AgentSession.corps_id == corps.id,
                    AgentDefinition.role == role,
                )
                .all()
            )
            liveness[role] = any(s.status == SessionStatus.ACTIVE for s in role_sessions)

        corps_results.append({
            "corps_id": corps.id,
            "corps_name": corps.name,
            "corps_status": corps.status.value,
            "rehearsal_mode": corps.rehearsal_mode.value if corps.rehearsal_mode else None,
            "metronome": {
                "checked": met_result.checked,
                "reclaimed": met_result.reclaimed,
                "reclaimed_rep_ids": met_result.reclaimed_rep_ids,
                "idle_kicked": met_result.idle_kicked,
                "idle_kicked_rep_ids": met_result.idle_kicked_rep_ids,
                "watchdog_respawned": met_result.watchdog_respawned,
            },
            "merge": {
                "checked": merge_result.checked,
                "merged": merge_result.merged,
                "conflicts": merge_result.conflicts,
            },
            "sessions": {
                "active": active_sessions,
                "completed": completed_sessions,
                "failed": failed_sessions,
            },
            "reps": rep_counts,
            "stalled_reps": stalled_reps,
            "is_stalled": len(stalled_reps) > 0,
            "liveness": liveness,
        })

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_corps": len(active_corps),
        "corps": corps_results,
        "summary": {
            "total_active_sessions": sum(r["sessions"]["active"] for r in corps_results),
            "total_stalled_corps": sum(1 for r in corps_results if r["is_stalled"]),
            "total_reclaimed": sum(r["metronome"]["reclaimed"] for r in corps_results),
            "total_idle_kicked": sum(r["metronome"]["idle_kicked"] for r in corps_results),
        },
    }


# --- Work Log ---

@router.get("/api/work-log")
def api_get_global_work_log(limit: int = 100, event_type: Optional[str] = None, db: Session = Depends(get_db)):
    """Get work log across all corps."""
    from backend.models.work_log import WorkLog
    query = db.query(WorkLog)
    if event_type:
        query = query.filter(WorkLog.event_type == event_type)
    logs = query.order_by(WorkLog.timestamp.desc()).limit(limit).all()
    nicknames = _nickname_lookup(db, logs)
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


@router.get("/api/corps/{corps_id}/work-log")
def api_get_work_log(corps_id: str, limit: int = 100, event_type: Optional[str] = None, db: Session = Depends(get_db)):
    """Get structured work log for a corps."""
    from backend.models.work_log import WorkLog
    query = db.query(WorkLog).filter(WorkLog.corps_id == corps_id)
    if event_type:
        query = query.filter(WorkLog.event_type == event_type)
    logs = query.order_by(WorkLog.timestamp.desc()).limit(limit).all()
    nicknames = _nickname_lookup(db, logs)
    return [{
        "id": log.id,
        "session_id": log.session_id,
        "role": log.role,
        "nickname": nicknames.get(log.session_id),
        "event_type": log.event_type,
        "phase": log.phase,
        "details": log.details,
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
    } for log in logs]


# --- Agents Overview ---

@router.get("/api/agents-overview")
def api_agents_overview(db: Session = Depends(get_db)):
    """Get all active agent sessions across all corps with their definitions."""
    from sqlalchemy.orm import joinedload
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.agent_definition import AgentDefinition
    from backend.models.corps import Corps

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

    by_defn: dict[str, AgentSession] = {}
    for s in sessions:
        if s.definition_id not in by_defn or (s.started_at and (
            not by_defn[s.definition_id].started_at or s.started_at > by_defn[s.definition_id].started_at
        )):
            by_defn[s.definition_id] = s

    all_defn_ids = {s.definition_id for s in sessions}
    dormant_defns = (
        db.query(AgentDefinition)
        .filter(
            AgentDefinition.corps_id.in_(corps_ids),
            ~AgentDefinition.id.in_(all_defn_ids) if all_defn_ids else AgentDefinition.id.isnot(None),
        )
        .all()
    ) if corps_ids else []

    results = []
    for s in by_defn.values():
        defn = s.definition
        corps = corps_map.get(s.corps_id) if s.corps_id else None
        session_count = sum(1 for sess in sessions if sess.definition_id == s.definition_id)
        results.append({
            "id": s.id,
            "definition_id": s.definition_id,
            "role": defn.role if defn else "unknown",
            "nickname": defn.nickname if defn else None,
            "classification": defn.classification.value if defn and defn.classification else None,
            "model_tier": defn.model_tier.value if defn else "unknown",
            "status": s.status.value,
            "corps_id": s.corps_id,
            "corps_name": corps.name if corps else None,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "session_count": session_count,
        })

    for defn in dormant_defns:
        corps = corps_map.get(defn.corps_id) if defn.corps_id else None
        results.append({
            "id": defn.id,
            "definition_id": defn.id,
            "role": defn.role,
            "nickname": defn.nickname,
            "classification": defn.classification.value if defn.classification else None,
            "model_tier": defn.model_tier.value,
            "status": "dormant",
            "corps_id": defn.corps_id,
            "corps_name": corps.name if corps else None,
            "started_at": None,
            "session_count": 0,
        })

    return results


# --- Session Activity ---

@router.get("/api/sessions/{session_id}/activity")
def api_get_session_activity(session_id: str, db: Session = Depends(get_db)):
    """Get activity log for an agent session."""
    from backend.models.agent_session import AgentSession
    from backend.models.agent_definition import AgentDefinition
    from backend.models.message import Message

    session = db.get(AgentSession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    defn = db.get(AgentDefinition, session.definition_id)

    messages = (
        db.query(Message)
        .filter(
            (Message.from_session_id == session_id) | (Message.to_session_id == session_id)
        )
        .order_by(Message.created_at)
        .all()
    )

    snapshot = None
    if session.context_snapshot:
        try:
            snapshot = json.loads(session.context_snapshot)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "session_id": session_id,
        "role": defn.role if defn else "unknown",
        "status": session.status.value,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "tool_calls": snapshot.get("tool_calls", []) if snapshot else [],
        "final_response": snapshot.get("final_response", "") if snapshot else "",
        "iterations": snapshot.get("iterations", 0) if snapshot else 0,
        "messages": [{
            "id": m.id,
            "type": m.type.value,
            "from_role": m.from_role,
            "to_role": m.to_role,
            "subject": m.subject,
            "body": m.body,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        } for m in messages],
    }


# --- Seasons ---

@router.post("/api/seasons")
def api_create_season(data: SeasonCreate):
    """Create a new season workspace."""
    from pathlib import Path
    from backend.services.season_persistence import create_season
    season_id = data.name.lower().replace(" ", "_")
    if data.year:
        season_id = f"{season_id}_{data.year}"
    try:
        base_dir = Path(".")
        season_dir = create_season(base_dir, season_id, metadata={"name": data.name, "year": data.year})
        return {"season_id": season_id, "path": str(season_dir), "name": data.name, "year": data.year}
    except ValueError as e:
        raise HTTPException(400, str(e))


# --- Theme API ---

@router.get("/api/theme")
def api_get_theme():
    from backend.config.theme import get_theme
    theme = get_theme()
    return {
        "name": theme.name,
        "display_name": theme.display_name,
        "org_unit": theme.org_unit,
        "org_unit_plural": theme.org_unit_plural,
        "project": theme.project,
        "project_plural": theme.project_plural,
        "work_levels": theme.work_levels,
        "work_item": theme.work_item,
        "work_item_plural": theme.work_item_plural,
        "execution_modes": theme.execution_modes,
        "admin_name": theme.admin_name,
        "color_palette": theme.color_palette,
        "commands": {
            k: {"label": v.label, "description": v.description, "category": v.category}
            for k, v in theme.commands.items()
        },
    }


@router.get("/api/themes")
def api_list_themes():
    from backend.config.theme import list_themes
    return list_themes()


# --- Seance ---

class SeanceRequest(BaseModel):
    query: str
    role: Optional[str] = None
    k: int = 5


@router.post("/api/seance")
def api_seance(req: SeanceRequest):
    """Query previous sessions for context (seance)."""
    from backend.services.seance import query_previous_sessions
    import dataclasses
    result = query_previous_sessions(req.query, role=req.role, k=req.k)
    return dataclasses.asdict(result)
