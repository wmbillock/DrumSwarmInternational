"""V1 API — Miscellaneous routes (heartbeat, metronome, theme, seance query, sessions)."""

import json as _json
from datetime import datetime as _dt, timezone as _tz
from pathlib import Path as _Path

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _get_db_session

router = APIRouter(prefix="/api/v1")


@router.post("/heartbeat")
async def v1_heartbeat():
    """External heartbeat endpoint for cron-based wakeup."""
    from backend.services.metronome_heartbeat import heartbeat_tick
    from backend.tools.metronome_orchestrator import gather_corps_health, get_active_corps

    db = _get_db_session()
    try:
        tick_timestamp = _dt.now(_tz.utc)
        brass_result = heartbeat_tick(db)

        alerts = []
        try:
            active_corps = get_active_corps(db)
            corps_health_list = []
            for corps in active_corps:
                try:
                    health = gather_corps_health(db, corps)
                    if not health.ed_responding and not health.pc_responding:
                        alert = f"RED FLAG: Corps {health.corps_id[:8]} ({health.corps_name}) - No ED/PC response"
                        alerts.append(alert)
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
                    alerts.append(f"Failed to gather health for corps {corps.id}: {e}")

            visual_result = {"total_corps": len(active_corps), "corps_health": corps_health_list}
        except Exception as e:
            visual_result = {"total_corps": 0, "corps_health": [], "error": str(e)}
            alerts.append(f"Failed to gather swarm status: {e}")

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

        try:
            log_dir = _Path("logs/metronome")
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp_clean = tick_timestamp.isoformat().replace(":", "-").replace(".", "-")
            json_log_path = log_dir / f"{timestamp_clean}.json"
            with open(json_log_path, "w") as f:
                _json.dump(heartbeat_result, f, indent=2)
            if alerts:
                alert_log_path = log_dir / "alerts.log"
                with open(alert_log_path, "a") as f:
                    for alert in alerts:
                        f.write(f"[{tick_timestamp.isoformat()}] {alert}\n")
        except Exception:
            pass

        return heartbeat_result
    finally:
        db.close()


@router.post("/metronome/tick")
def v1_metronome_system_tick():
    """System-wide metronome tick."""
    from backend.tools.metronome import tick
    from backend.services.corps_service import merge_monitor_check
    from backend.models.corps import Corps, CorpsStatus
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.agent_definition import AgentDefinition
    from backend.models.rep import Rep, RepStatus
    from backend.models.show import Show
    from backend.models.segment import Segment

    STALLED_THRESHOLD_SECONDS = 300

    db = _get_db_session()
    try:
        active_corps = (
            db.query(Corps)
            .filter(Corps.status.in_([CorpsStatus.WINTER_CAMPS, CorpsStatus.ON_TOUR]))
            .all()
        )
        corps_results = []
        for corps in active_corps:
            met_result = tick(db, corps.id)
            merge_result = merge_monitor_check(db, corps.id)

            sessions = db.query(AgentSession).filter(AgentSession.corps_id == corps.id).all()
            active_sessions = sum(1 for s in sessions if s.status == SessionStatus.ACTIVE)
            completed_sessions = sum(1 for s in sessions if s.status == SessionStatus.COMPLETED)
            failed_sessions = sum(1 for s in sessions if s.status == SessionStatus.FAILED)

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

            now = _dt.now(_tz.utc)
            stalled_reps = []
            for r in reps:
                if r.status in (RepStatus.PENDING, RepStatus.ASSIGNED) and r.updated_at:
                    idle_secs = (now - r.updated_at.replace(tzinfo=_tz.utc)).total_seconds()
                    if idle_secs > STALLED_THRESHOLD_SECONDS:
                        stalled_reps.append({
                            "rep_id": r.id, "status": r.status.value,
                            "idle_seconds": round(idle_secs),
                            "last_updated": r.updated_at.isoformat(),
                        })

            staff_roles = ["executive_director", "program_coordinator", "brass_caption_head",
                           "percussion_caption_head", "guard_caption_head", "visual_caption_head"]
            liveness = {}
            for role in staff_roles:
                role_sessions = (
                    db.query(AgentSession)
                    .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
                    .filter(AgentSession.corps_id == corps.id, AgentDefinition.role == role)
                    .all()
                )
                liveness[role] = any(s.status == SessionStatus.ACTIVE for s in role_sessions)

            corps_results.append({
                "corps_id": corps.id, "corps_name": corps.name,
                "corps_status": corps.status.value,
                "rehearsal_mode": corps.rehearsal_mode.value if corps.rehearsal_mode else None,
                "metronome": {
                    "checked": met_result.checked, "reclaimed": met_result.reclaimed,
                    "reclaimed_rep_ids": met_result.reclaimed_rep_ids,
                    "idle_kicked": met_result.idle_kicked,
                    "idle_kicked_rep_ids": met_result.idle_kicked_rep_ids,
                    "watchdog_respawned": met_result.watchdog_respawned,
                },
                "merge": {"checked": merge_result.checked, "merged": merge_result.merged, "conflicts": merge_result.conflicts},
                "sessions": {"active": active_sessions, "completed": completed_sessions, "failed": failed_sessions},
                "reps": rep_counts, "stalled_reps": stalled_reps, "is_stalled": len(stalled_reps) > 0,
                "liveness": liveness,
            })

        return {
            "timestamp": _dt.now(_tz.utc).isoformat(),
            "total_corps": len(active_corps),
            "corps": corps_results,
            "summary": {
                "total_active_sessions": sum(r["sessions"]["active"] for r in corps_results),
                "total_stalled_corps": sum(1 for r in corps_results if r["is_stalled"]),
                "total_reclaimed": sum(r["metronome"]["reclaimed"] for r in corps_results),
                "total_idle_kicked": sum(r["metronome"]["idle_kicked"] for r in corps_results),
            },
        }
    finally:
        db.close()


@router.get("/theme")
def v1_get_theme():
    from backend.config.theme import get_theme
    theme = get_theme()
    return {
        "name": theme.name, "display_name": theme.display_name,
        "org_unit": theme.org_unit, "org_unit_plural": theme.org_unit_plural,
        "project": theme.project, "project_plural": theme.project_plural,
        "work_levels": theme.work_levels, "work_item": theme.work_item,
        "work_item_plural": theme.work_item_plural,
        "execution_modes": theme.execution_modes, "admin_name": theme.admin_name,
        "color_palette": theme.color_palette,
        "commands": {
            k: {"label": v.label, "description": v.description, "category": v.category}
            for k, v in theme.commands.items()
        },
    }


@router.get("/themes")
def v1_list_themes():
    from backend.config.theme import list_themes
    return list_themes()


@router.post("/seance/query")
def v1_seance_query(payload: dict):
    """Query the seance system (ED retrospective chat)."""
    from backend.services.ed_chat import query_ed
    corps_id = payload.get("corps_id")
    question = payload.get("question", "")
    if not corps_id or not question:
        raise HTTPException(400, "corps_id and question required")
    db = _get_db_session()
    try:
        result = query_ed(db, corps_id, question)
        return result
    finally:
        db.close()


@router.get("/sessions/{session_id}/activity")
def v1_session_activity(session_id: str):
    """Get activity log for a session."""
    from backend.models.agent_session import AgentSession
    from backend.models.work_log import WorkLog
    db = _get_db_session()
    try:
        session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
        if not session:
            raise HTTPException(404, "Session not found")
        logs = (
            db.query(WorkLog)
            .filter(WorkLog.session_id == session_id)
            .order_by(WorkLog.created_at.asc())
            .all()
        )
        return {
            "session_id": session_id,
            "status": session.status.value if session.status else None,
            "entries": [{
                "id": w.id,
                "action": w.action,
                "details": w.details,
                "created_at": w.created_at.isoformat() if w.created_at else None,
            } for w in logs],
        }
    finally:
        db.close()
