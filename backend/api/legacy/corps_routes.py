"""Legacy corps endpoints extracted from app.py."""

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.app import get_db, get_task_manager, manager

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Pydantic Schemas ---

class RehearsalModeSet(BaseModel):
    mode: str  # basics, sectionals, full_ensemble, run_through

class CorpsModeSwitch(BaseModel):
    mode: str  # design_room, show_mode, rehearsal_mode, judging, offseason_review

class CorpsThemeUpdate(BaseModel):
    theme_id: Optional[str] = None
    mascot: Optional[str] = None
    uniform_concept: Optional[str] = None

class CorpsCommand(BaseModel):
    command: str

CORPS_COMMANDS = {
    "resume_hut": {"label": "Resume, Hut!", "description": "Wake all agents and begin/resume work", "category": "control"},
    "attention": {"label": "Attention!", "description": "All agents pause and report current status", "category": "control"},
    "at_ease": {"label": "At Ease", "description": "Finish current tasks then idle", "category": "control"},
    "dismissed": {"label": "Dismissed", "description": "Stop all agents, disband the corps", "category": "control"},
    "basics": {"label": "Basics", "description": "Switch to basics rehearsal mode (manual override)", "category": "rehearsal"},
    "sectionals": {"label": "Sectionals", "description": "Switch to sectionals rehearsal mode (manual override)", "category": "rehearsal"},
    "full_ensemble": {"label": "Full Ensemble", "description": "Switch to full ensemble rehearsal (manual override)", "category": "rehearsal"},
    "run_through": {"label": "Run Through", "description": "Full run-through rehearsal mode (manual override)", "category": "rehearsal"},
    "go_on_tour": {"label": "Go On Tour", "description": "Autonomous execution — agents work independently", "category": "execution"},
    "return_to_camps": {"label": "Return to Camps", "description": "Back to planning phase", "category": "execution"},
    "metronome_tick": {"label": "Metronome Tick", "description": "Manual metronome tick — reclaim stale work", "category": "system"},
    "merge_check": {"label": "Merge Check", "description": "Check and merge completed work", "category": "system"},
}


# --- Admin corps ("the bar") ---

@router.get("/api/admin-corps")
def api_get_admin_corps(db: Session = Depends(get_db)):
    """Get or create the singleton admin corps for DCI HQ chat."""
    from backend.services.corps_service import get_or_create_admin_corps
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.agent_definition import AgentDefinition
    corps = get_or_create_admin_corps(db)
    agents = (
        db.query(AgentSession)
        .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
        .filter(AgentSession.corps_id == corps.id)
        .all()
    )
    roster = []
    for a in agents:
        defn = db.get(AgentDefinition, a.definition_id)
        roster.append({
            "id": a.id, "role": defn.role if defn else "unknown",
            "nickname": defn.nickname if defn else None,
            "model_tier": defn.model_tier.value if defn else "unknown",
            "status": a.status.value,
        })
    return {
        "id": corps.id, "name": corps.name, "status": corps.status.value,
        "roster": roster,
    }


# --- Corps endpoints ---

@router.get("/api/corps/{corps_id}")
def api_get_corps(corps_id: str, db: Session = Depends(get_db)):
    from backend.models.corps import Corps
    corps = db.get(Corps, corps_id)
    if corps:
        return {"id": corps.id, "name": corps.name, "status": corps.status.value,
                "rehearsal_mode": corps.rehearsal_mode.value if corps.rehearsal_mode else None,
                "mode": corps.mode.value if corps.mode else None,
                "theme_id": corps.theme_id, "mascot": corps.mascot,
                "uniform_concept": corps.uniform_concept}
    # Fallback: check filesystem workspace
    root = Path(os.environ.get("DCI_PROJECT_ROOT", ".")).resolve()
    corps_path = root / "corps" / corps_id / "corps.yaml"
    if corps_path.is_file():
        import yaml
        data = yaml.safe_load(corps_path.read_text())
        return {"id": data.get("corps_id", corps_id),
                "name": data.get("display_name", corps_id),
                "status": data.get("state", "unknown"),
                "rehearsal_mode": None, "mode": None,
                "theme_id": None, "mascot": None, "uniform_concept": None}
    raise HTTPException(404, "Corps not found")


@router.get("/api/corps/{corps_id}/theme")
def api_get_corps_theme(corps_id: str, db: Session = Depends(get_db)):
    from backend.models.corps import Corps
    corps = db.get(Corps, corps_id)
    if not corps:
        raise HTTPException(404, "Corps not found")
    return {"corps_id": corps.id, "theme_id": corps.theme_id,
            "mascot": corps.mascot, "uniform_concept": corps.uniform_concept}


@router.put("/api/corps/{corps_id}/theme")
def api_update_corps_theme(corps_id: str, data: CorpsThemeUpdate, db: Session = Depends(get_db)):
    from backend.services.corps_service import update_corps_theme, CorpsError
    try:
        corps = update_corps_theme(db, corps_id, theme_id=data.theme_id,
                                   mascot=data.mascot, uniform_concept=data.uniform_concept)
        return {"corps_id": corps.id, "theme_id": corps.theme_id,
                "mascot": corps.mascot, "uniform_concept": corps.uniform_concept}
    except CorpsError as e:
        raise HTTPException(404, str(e))


@router.get("/api/corps/{corps_id}/progression")
def api_get_progression(corps_id: str, db: Session = Depends(get_db)):
    """Current rehearsal mode, milestones, and what's needed to advance."""
    from backend.models.corps import Corps, RehearsalMode
    from backend.services.rehearsal_progression import (
        _basics_met, _sectionals_met, _full_ensemble_met, _next_mode,
    )
    corps = db.get(Corps, corps_id)
    if not corps:
        raise HTTPException(404, "Corps not found")

    current = corps.rehearsal_mode
    checks = {
        RehearsalMode.BASICS: ("basics_met", _basics_met),
        RehearsalMode.SECTIONALS: ("sectionals_met", _sectionals_met),
        RehearsalMode.FULL_ENSEMBLE: ("full_ensemble_met", _full_ensemble_met),
    }
    milestones = {}
    for mode, (key, fn) in checks.items():
        milestones[key] = fn(db, corps_id)

    return {
        "corps_id": corps_id,
        "status": corps.status.value,
        "current_mode": current.value if current else None,
        "next_mode": _next_mode(current).value if current and _next_mode(current) else None,
        "milestones": milestones,
    }


@router.post("/api/corps/{corps_id}/rehearsal-mode")
def api_set_rehearsal_mode(corps_id: str, data: RehearsalModeSet, db: Session = Depends(get_db)):
    from backend.models.corps import RehearsalMode
    from backend.services.corps_service import set_rehearsal_mode, CorpsError
    try:
        mode = RehearsalMode(data.mode)
        corps = set_rehearsal_mode(db, corps_id, mode)
        return {"id": corps.id, "rehearsal_mode": corps.rehearsal_mode.value}
    except (ValueError, CorpsError) as e:
        raise HTTPException(400, str(e))


# --- Roster (agent sessions) ---

@router.get("/api/corps/{corps_id}/roster")
def api_get_roster(corps_id: str, db: Session = Depends(get_db)):
    from backend.models.agent_session import AgentSession
    from backend.models.agent_definition import AgentDefinition
    sessions = (
        db.query(AgentSession)
        .filter(AgentSession.corps_id == corps_id)
        .all()
    )
    if sessions:
        result = []
        for s in sessions:
            defn = db.get(AgentDefinition, s.definition_id)
            result.append({
                "id": s.id,
                "role": defn.role if defn else "unknown",
                "nickname": defn.nickname if defn else None,
                "model_tier": defn.model_tier.value if defn else "unknown",
                "classification": defn.classification.value if defn and defn.classification else None,
                "status": s.status.value,
                "corps_id": s.corps_id,
                "parent_session_id": s.parent_session_id,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            })
        return result
    # Fallback: check filesystem roster
    root = Path(os.environ.get("DCI_PROJECT_ROOT", ".")).resolve()
    roster_path = root / "corps" / corps_id / "roster.yaml"
    if roster_path.is_file():
        import yaml
        roster = yaml.safe_load(roster_path.read_text())
        return [
            {
                "id": f"{corps_id}-{a.get('role', 'unknown')}-{i}",
                "role": a.get("role", "unknown"),
                "nickname": a.get("nickname"),
                "model_tier": a.get("model_tier", "unknown"),
                "classification": a.get("classification"),
                "status": a.get("status", "stopped"),
                "corps_id": corps_id,
                "parent_session_id": None,
                "started_at": None,
                "ended_at": None,
            }
            for i, a in enumerate(roster.get("assignments", []))
        ]
    return []


@router.get("/api/corps/{corps_id}/scoresheet")
def api_get_scoresheet(corps_id: str, db: Session = Depends(get_db)):
    """Competition-style scoresheet for a corps — caption scores, penalties, operational metrics."""
    from backend.models.corps import Corps
    from backend.models.score import Score, JudgeType
    from backend.models.penalty import Penalty
    from backend.models.rep import Rep, RepStatus
    from backend.models.segment import Segment
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.agent_definition import AgentDefinition
    from backend.models.work_log import WorkLog
    from backend.services.scoring_service import DEFAULT_WEIGHTS

    corps = db.get(Corps, corps_id)
    if not corps:
        raise HTTPException(404, "Corps not found")

    # --- Caption scores (per judge type) ---
    scores = db.query(Score).filter(Score.corps_id == corps_id).all()
    caption_data: dict[str, dict] = {}
    for jt in JudgeType:
        jt_scores = [s for s in scores if s.judge_type == jt]
        if jt_scores:
            values = [s.value for s in jt_scores]
            boxes = [s.box for s in jt_scores]
            caption_data[jt.value] = {
                "count": len(jt_scores),
                "average": round(sum(values) / len(values), 2),
                "min": min(values),
                "max": max(values),
                "avg_box": round(sum(boxes) / len(boxes), 2),
                "weight": DEFAULT_WEIGHTS.get(jt, 0.0),
                "latest_feedback": jt_scores[-1].feedback,
            }
        else:
            caption_data[jt.value] = {
                "count": 0, "average": 0, "min": 0, "max": 0,
                "avg_box": 0, "weight": DEFAULT_WEIGHTS.get(jt, 0.0),
                "latest_feedback": None,
            }

    # --- Composite score ---
    weighted_sum = 0.0
    total_weight = 0.0
    for jt in JudgeType:
        cd = caption_data[jt.value]
        if cd["count"] > 0:
            w = cd["weight"]
            weighted_sum += cd["average"] * w
            total_weight += w
    raw_total = round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.0

    # --- Penalties ---
    penalties = db.query(Penalty).filter(Penalty.corps_id == corps_id).all()
    penalties_total = sum(p.amount for p in penalties)
    penalty_breakdown = {}
    for p in penalties:
        pt = p.type.value
        penalty_breakdown.setdefault(pt, {"count": 0, "total": 0.0, "reasons": []})
        penalty_breakdown[pt]["count"] += 1
        penalty_breakdown[pt]["total"] += p.amount
        if p.reason and len(penalty_breakdown[pt]["reasons"]) < 5:
            penalty_breakdown[pt]["reasons"].append(p.reason)

    final_score = round(max(0.0, raw_total - penalties_total), 2)

    # --- Rep metrics ---
    from backend.models.show import Show
    show = db.query(Show).filter(Show.corps_id == corps_id).first()
    reps_total = 0
    reps_completed = 0
    reps_failed = 0
    reps_in_progress = 0
    segments_total = 0
    if show and show.segment_root_id:
        coords = db.query(Segment).all()  # TODO: filter by tree
        coord_ids = {c.id for c in coords}
        segments_total = len(coord_ids)
        reps = db.query(Rep).filter(Rep.segment_id.in_(coord_ids)).all() if coord_ids else []
        reps_total = len(reps)
        reps_completed = sum(1 for r in reps if r.status == RepStatus.COMPLETED)
        reps_failed = sum(1 for r in reps if r.status == RepStatus.FAILED)
        reps_in_progress = sum(1 for r in reps if r.status == RepStatus.IN_PROGRESS)

    completion_rate = round(reps_completed / reps_total * 100, 1) if reps_total > 0 else 0.0
    failure_rate = round(reps_failed / reps_total * 100, 1) if reps_total > 0 else 0.0

    # --- Agent metrics (per role) ---
    sessions = db.query(AgentSession).filter(AgentSession.corps_id == corps_id).all()
    role_metrics: dict[str, dict] = {}
    for s in sessions:
        defn = db.get(AgentDefinition, s.definition_id)
        if not defn:
            continue
        role = defn.role
        role_metrics.setdefault(role, {
            "nickname": defn.nickname,
            "model_tier": defn.model_tier.value,
            "status": s.status.value,
            "session_id": s.id,
        })

    # --- Work log stats ---
    log_count = db.query(WorkLog).filter(WorkLog.corps_id == corps_id).count()
    tool_calls = db.query(WorkLog).filter(
        WorkLog.corps_id == corps_id, WorkLog.event_type == "tool_call"
    ).count()
    handoffs = db.query(WorkLog).filter(
        WorkLog.corps_id == corps_id, WorkLog.event_type == "handoff"
    ).count()
    failures = db.query(WorkLog).filter(
        WorkLog.corps_id == corps_id, WorkLog.event_type == "failure"
    ).count()

    return {
        "corps_id": corps_id,
        "corps_name": corps.name,
        "caption_scores": caption_data,
        "composite": {
            "raw_total": raw_total,
            "penalties_total": round(penalties_total, 2),
            "final_score": final_score,
            "needs_rework": final_score < 60.0,
            "needs_escalation": final_score < 40.0,
        },
        "penalties": penalty_breakdown,
        "execution": {
            "reps_total": reps_total,
            "reps_completed": reps_completed,
            "reps_failed": reps_failed,
            "reps_in_progress": reps_in_progress,
            "completion_rate": completion_rate,
            "failure_rate": failure_rate,
            "segments_total": segments_total,
        },
        "roster": role_metrics,
        "activity": {
            "total_events": log_count,
            "tool_calls": tool_calls,
            "handoffs": handoffs,
            "failures": failures,
        },
    }


@router.post("/api/corps/{corps_id}/mode")
async def api_switch_corps_mode(corps_id: str, data: CorpsModeSwitch, db: Session = Depends(get_db)):
    """Switch a corps to a new operational mode."""
    from backend.models.corps import CorpsMode
    from backend.services.mode_manager import switch_mode, ModeError
    try:
        new_mode = CorpsMode(data.mode)
        corps = switch_mode(db, corps_id, new_mode)
        await manager.broadcast(corps_id, {
            "type": "mode_switch",
            "corps_id": corps_id,
            "mode": new_mode.value,
        })
        return {"id": corps.id, "mode": corps.mode.value}
    except ValueError:
        raise HTTPException(400, f"Invalid mode: {data.mode}")
    except ModeError as e:
        raise HTTPException(400, str(e))


@router.get("/api/corps/{corps_id}/metrics")
def api_corps_metrics(corps_id: str, db: Session = Depends(get_db)):
    """Get aggregate metrics for a corps."""
    from backend.services.metrics_collector import collect_corps_metrics
    import dataclasses
    metrics = collect_corps_metrics(db, corps_id)
    return dataclasses.asdict(metrics)


@router.post("/api/corps/{corps_id}/evaluate")
def api_evaluate_corps(corps_id: str, db: Session = Depends(get_db)):
    """Run post-show evaluation on all performers in a corps."""
    from backend.services.evaluation_service import evaluate_corps
    return evaluate_corps(db, corps_id)


@router.post("/api/corps/{corps_id}/season-transition")
def api_season_transition(corps_id: str, db: Session = Depends(get_db)):
    """Run end-of-season lifecycle: age performers, check ageouts."""
    from backend.services.lifecycle_manager import conduct_season_transition
    return conduct_season_transition(db, corps_id)


@router.get("/api/corps/{corps_id}/ageouts")
def api_get_ageouts(corps_id: str, db: Session = Depends(get_db)):
    """Get performers approaching ageout for this corps."""
    from backend.services.lifecycle_manager import check_ageouts
    ageouts = check_ageouts(db)
    return [{"id": p.id, "name": p.name, "age": p.age, "role_type": p.role_type} for p in ageouts]


# --- Corps Commands ---

@router.get("/api/corps-commands")
def api_list_corps_commands():
    """List all available corps commands."""
    return CORPS_COMMANDS


@router.post("/api/corps/{corps_id}/command")
async def api_execute_corps_command(corps_id: str, data: CorpsCommand, db: Session = Depends(get_db)):
    """Execute a corps command."""
    from backend.models.corps import Corps, CorpsStatus, RehearsalMode
    from backend.services.corps_service import (
        go_on_tour, return_to_camps, set_rehearsal_mode, disband_corps, merge_monitor_check, CorpsError,
    )
    from backend.tools.metronome import tick

    corps = db.get(Corps, corps_id)
    if not corps:
        raise HTTPException(404, "Corps not found")

    cmd = data.command
    if cmd not in CORPS_COMMANDS:
        raise HTTPException(400, f"Unknown command: {cmd}")

    result = {"command": cmd, "corps_id": corps_id, "status": "ok", "detail": ""}
    tm = get_task_manager()

    if cmd == "resume_hut":
        if tm:
            from backend.models.agent_session import AgentSession, SessionStatus
            from backend.models.agent_definition import AgentDefinition
            unique_roles = (
                db.query(AgentDefinition.role)
                .join(AgentSession)
                .filter(AgentSession.corps_id == corps_id)
                .distinct()
                .all()
            )
            woken = 0
            for (role,) in unique_roles:
                sid = tm.get_session_for_role(db, corps_id, role)
                if sid and not tm.is_active(sid):
                    tm.start_agent(
                        session_id=sid,
                        task_description=(
                            f"RESUME HUT! The corps has been called to attention and work is resuming. "
                            f"Check your current assignments and continue working. Corps ID: {corps_id}"
                        ),
                        corps_id=corps_id,
                    )
                    woken += 1
            result["detail"] = f"Woke {woken} agents"
        await manager.broadcast(corps_id, {
            "type": "command", "command": "resume_hut",
            "content": "Resume, Hut! All agents resuming work.",
        })

    elif cmd == "attention":
        if tm:
            ed_session = tm.get_session_for_role(db, corps_id, "executive_director")
            if ed_session and not tm.is_active(ed_session):
                tm.start_agent(
                    session_id=ed_session,
                    task_description=(
                        f"ATTENTION! The director has called the corps to attention. "
                        f"Report the current status of all work in progress. Corps ID: {corps_id}. "
                        f"Check all segments and reps, then provide a full status report."
                    ),
                    corps_id=corps_id,
                )
        await manager.broadcast(corps_id, {
            "type": "command", "command": "attention",
            "content": "Attention! Status report requested.",
        })
        result["detail"] = "Status report requested from ED"

    elif cmd == "at_ease":
        corps.status = CorpsStatus.WINTER_CAMPS
        db.commit()
        await manager.broadcast(corps_id, {
            "type": "command", "command": "at_ease",
            "content": "At ease. Returning to Winter Camps. Finishing current tasks, then standing by.",
        })
        result["detail"] = "Corps returned to Winter Camps"

    elif cmd == "dismissed":
        try:
            disband_corps(db, corps_id)
            await manager.broadcast(corps_id, {
                "type": "command", "command": "dismissed",
                "content": "Corps dismissed. All agents standing down.",
            })
            result["detail"] = "Corps disbanded"
        except CorpsError as e:
            raise HTTPException(400, str(e))

    elif cmd in ("basics", "sectionals", "full_ensemble", "run_through"):
        try:
            mode = RehearsalMode(cmd)
            set_rehearsal_mode(db, corps_id, mode)
            await manager.broadcast(corps_id, {
                "type": "command", "command": cmd,
                "content": f"Rehearsal mode set to: {cmd.replace('_', ' ')}",
            })
            result["detail"] = f"Rehearsal mode: {cmd}"
        except (ValueError, CorpsError) as e:
            raise HTTPException(400, str(e))

    elif cmd == "go_on_tour":
        try:
            go_on_tour(db, corps_id)
            await manager.broadcast(corps_id, {
                "type": "command", "command": "go_on_tour",
                "content": "On Tour — autonomous execution active.",
            })
            result["detail"] = "On Tour"
        except CorpsError as e:
            raise HTTPException(400, str(e))

    elif cmd == "return_to_camps":
        try:
            return_to_camps(db, corps_id)
            await manager.broadcast(corps_id, {
                "type": "command", "command": "return_to_camps",
                "content": "Returned to Winter Camps — planning phase.",
            })
            result["detail"] = "Returned to Winter Camps"
        except CorpsError as e:
            raise HTTPException(400, str(e))

    elif cmd == "metronome_tick":
        tick_result = tick(db, corps_id)
        await manager.broadcast(corps_id, {
            "type": "metronome_tick", "corps_id": corps_id,
            "checked": tick_result.checked, "reclaimed": tick_result.reclaimed,
        })
        result["detail"] = f"Checked {tick_result.checked}, reclaimed {tick_result.reclaimed}"

    elif cmd == "merge_check":
        merge_result = merge_monitor_check(db, corps_id)
        await manager.broadcast(corps_id, {
            "type": "merge_check", "corps_id": corps_id,
            "merged": merge_result.merged, "conflicts": merge_result.conflicts,
        })
        result["detail"] = f"Merged {merge_result.merged}, conflicts {merge_result.conflicts}"

    return result


@router.post("/api/corps/{corps_id}/merge-check")
def api_merge_check(corps_id: str, db: Session = Depends(get_db)):
    from backend.services.corps_service import merge_monitor_check
    result = merge_monitor_check(db, corps_id)
    return {
        "checked": result.checked,
        "merged": result.merged,
        "conflicts": result.conflicts,
        "merged_segment_ids": result.merged_segment_ids,
        "conflict_segment_ids": result.conflict_segment_ids,
    }
