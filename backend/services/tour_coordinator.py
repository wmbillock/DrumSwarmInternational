"""Tour coordinator service — schedules competition rounds and advances tour status."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from pathlib import Path

from backend.services.season_persistence import load_season, save_season
from backend.services.yaml_util import atomic_write, safe_dump_yaml

logger = logging.getLogger(__name__)

CAPTIONS = ["brass", "percussion", "guard", "visual", "general_effect", "ensemble_technique"]


def assign_corps_shows(season_dir: Path) -> dict[str, str]:
    """Assign each corps ONE show for the entire season.

    Uses division-based assignments if available (corps already assigned to shows
    via assign_corps in season_persistence). Falls back to round-robin across
    available shows if no division assignments exist.

    Stores result in season.yaml under corps_show_assignments.
    Returns the assignment dict {corps_id: show_slug}.
    """
    data = load_season(season_dir)
    corps_ids = list(data.get("registered_corps", []))
    shows = list(data.get("shows") or [])
    divisions = data.get("divisions") or {}

    if not corps_ids or not shows:
        return {}

    assignments: dict[str, str] = {}

    # Check if corps are already assigned to shows via divisions
    for show_slug in shows:
        div_corps = divisions.get(show_slug, [])
        for cid in div_corps:
            if cid in corps_ids and cid not in assignments:
                assignments[cid] = show_slug

    # Round-robin remaining unassigned corps across shows
    unassigned = [cid for cid in corps_ids if cid not in assignments]
    for i, cid in enumerate(unassigned):
        assignments[cid] = shows[i % len(shows)]

    # Persist assignments
    data["corps_show_assignments"] = assignments
    save_season(season_dir, data)

    logger.info("Assigned %d corps to shows in %s", len(assignments), season_dir.name)
    return assignments


def _get_corps_show_assignments(season_dir: Path, data: dict) -> dict[str, str]:
    """Get or create per-corps show assignments."""
    assignments = data.get("corps_show_assignments")
    if assignments:
        return dict(assignments)
    return assign_corps_shows(season_dir)


def generate_schedule(season_dir: Path) -> list[dict]:
    """Create competition rounds where each corps performs THEIR assigned show.

    Creates exactly `required_scores` rounds. Every corps appears in every round,
    performing the same show they were assigned for the season.
    """
    data = load_season(season_dir)
    season_id = data.get("season_id", season_dir.name)
    corps_ids = list(data.get("registered_corps", []))
    if not corps_ids:
        return []

    config = data.get("config") or {}
    required_scores = int(config.get("required_scores", 1))

    # Get per-corps show assignments
    assignments = _get_corps_show_assignments(season_dir, data)

    schedule: list[dict] = []
    for round_num in range(1, required_scores + 1):
        # Build per-corps performance list
        corps_performances = []
        for cid in sorted(corps_ids):
            show_slug = assignments.get(cid, "tour")
            corps_performances.append({
                "corps_id": cid,
                "show_slug": show_slug,
            })

        schedule.append({
            "round": round_num,
            "competition_id": f"{season_id}-round-{round_num}",
            "corps_performances": corps_performances,
            "corps_ids": sorted(corps_ids),  # Backward compat
            "status": "pending",
        })

    return schedule


def run_competition_round(season_dir: Path) -> dict:
    """Score the next scheduled round and trigger improvement cycles."""
    data = load_season(season_dir)
    schedule = list(data.get("schedule") or [])
    if not schedule:
        schedule = generate_schedule(season_dir)
        data["schedule"] = schedule

    # Backfill missing round/status fields for legacy schedule entries
    for idx, entry in enumerate(schedule):
        entry.setdefault("round", idx + 1)
        entry.setdefault("status", "pending")

    next_round = next((entry for entry in schedule if entry.get("status") != "completed"), None)
    if not next_round:
        return {"status": "complete", "message": "All rounds completed", "schedule": schedule}

    corps_ids = list(next_round.get("corps_ids") or [])
    if not corps_ids:
        next_round["status"] = "completed"
        save_season(season_dir, data)
        return {"status": "skipped", "round": next_round.get("round"), "schedule": schedule}

    # Dispatch agents before scoring
    dispatch_result = {}
    try:
        dispatch_result = dispatch_round_agents(next_round, season_dir)
    except Exception:
        logger.warning("Agent dispatch failed for round %s, continuing with scoring", next_round.get("round"), exc_info=True)

    standings = _score_round(season_dir, next_round)
    next_round["status"] = "completed"
    next_round["completed_at"] = datetime.now(timezone.utc).isoformat()
    next_round["standings"] = standings.get("results", [])
    save_season(season_dir, data)

    improvement_summary = _trigger_improvements(corps_ids, standings)
    return {
        "status": "completed",
        "round": next_round.get("round"),
        "competition_id": next_round.get("competition_id"),
        "standings": standings.get("results", []),
        "dispatch": dispatch_result,
        "improvements": improvement_summary,
        "schedule": schedule,
    }


def get_tour_status(season_dir: Path) -> dict:
    """Summarize tour schedule progress."""
    data = load_season(season_dir)
    schedule = list(data.get("schedule") or [])
    if not schedule:
        schedule = generate_schedule(season_dir)
        data["schedule"] = schedule
        save_season(season_dir, data)

    # Backfill missing round/status fields for legacy schedule entries
    for idx, entry in enumerate(schedule):
        entry.setdefault("round", idx + 1)
        entry.setdefault("status", "pending")

    history = [entry for entry in schedule if entry.get("status") == "completed"]
    current = next((entry for entry in schedule if entry.get("status") != "completed"), None)
    upcoming = [entry for entry in schedule if entry.get("status") == "pending"]

    return {
        "season_id": data.get("season_id", season_dir.name),
        "status": data.get("metadata", {}).get("status", "planning"),
        "auto_advance": bool((data.get("config") or {}).get("auto_advance", False)),
        "current_round": current,
        "history": history,
        "upcoming": upcoming,
        "schedule": schedule,
    }


def _pick_show_slug(season_data: dict, corps_ids: list[str], round_num: int = 1) -> str:
    """Legacy fallback — pick a show slug for a round.

    Kept for backward compatibility with old schedule formats.
    New schedules use per-corps assignments via corps_performances.
    """
    shows = list(season_data.get("shows") or [])
    if shows:
        return shows[(round_num - 1) % len(shows)]
    divisions = season_data.get("divisions") or {}
    div_slugs = list(divisions.keys())
    if div_slugs:
        return div_slugs[(round_num - 1) % len(div_slugs)]
    return "tour"


def _score_round(season_dir: Path, round_entry: dict) -> dict:
    """Score a round — handles both per-corps shows and legacy single-show format."""
    from backend.api.app import get_task_manager
    from backend.api.v1.helpers import _get_db_session
    from backend.services.competition_executor import execute_competition

    season_id = season_dir.name
    competition_id = round_entry.get("competition_id") or f"{season_id}-round"

    tm = get_task_manager()
    llm_client = tm.llm_client if tm else None

    corps_performances = round_entry.get("corps_performances")

    if corps_performances:
        # New format: per-corps show assignments
        # Group corps by show_slug to minimize executor calls
        show_groups: dict[str, list[str]] = {}
        for perf in corps_performances:
            slug = perf.get("show_slug", "tour")
            show_groups.setdefault(slug, []).append(perf["corps_id"])

        all_results: list[dict] = []
        all_errors: list[str] = []

        for show_slug, corps_ids in show_groups.items():
            db = _get_db_session()
            try:
                result = execute_competition(
                    db=db,
                    competition_id=competition_id,
                    season_id=season_id,
                    show_slug=show_slug,
                    corps_ids=corps_ids,
                    season_dir=season_dir,
                    llm_client=llm_client,
                )
                standings = result["standings_data"]
                all_results.extend(standings.get("results", []))
                all_errors.extend(result.get("scoring_errors", []))
            finally:
                db.close()

        # Re-rank all results together by final_score
        all_results.sort(key=lambda r: r.get("final_score", 0), reverse=True)
        for rank, r in enumerate(all_results, 1):
            r["rank"] = rank

        return {
            "season_id": season_id,
            "competition_id": competition_id,
            "results": all_results,
            "scoring_errors": all_errors,
        }
    else:
        # Legacy format: single show_slug for whole round
        show_slug = round_entry.get("show_slug") or "tour"
        corps_ids = list(round_entry.get("corps_ids") or [])

        db = _get_db_session()
        try:
            result = execute_competition(
                db=db,
                competition_id=competition_id,
                season_id=season_id,
                show_slug=show_slug,
                corps_ids=corps_ids,
                season_dir=season_dir,
                llm_client=llm_client,
            )
            return result["standings_data"]
        finally:
            db.close()


def set_auto_advance(season_dir: Path, enabled: bool) -> dict:
    """Enable or disable metronome-driven auto-advance for a touring season."""
    data = load_season(season_dir)
    data.setdefault("config", {})["auto_advance"] = enabled
    save_season(season_dir, data)
    return {"auto_advance": enabled}


def get_auto_advance(season_dir: Path) -> bool:
    """Check if auto_advance is enabled for a season."""
    data = load_season(season_dir)
    return bool((data.get("config") or {}).get("auto_advance", False))


def find_touring_seasons() -> list[Path]:
    """Find all season directories with status=touring and pending rounds."""
    from backend.api.v1.helpers import _get_root
    root = _get_root()
    seasons_dir = root / "seasons"
    if not seasons_dir.exists():
        return []
    touring = []
    for season_dir in seasons_dir.iterdir():
        if not season_dir.is_dir():
            continue
        yaml_path = season_dir / "season.yaml"
        if not yaml_path.is_file():
            continue
        try:
            data = load_season(season_dir)
            status = (data.get("metadata") or {}).get("status", "")
            if status == "touring" and get_auto_advance(season_dir):
                schedule = data.get("schedule") or []
                has_pending = any(e.get("status") != "completed" for e in schedule)
                if has_pending:
                    touring.append(season_dir)
        except Exception:
            continue
    return touring


def dispatch_round_agents(round_entry: dict, season_dir: Path) -> dict:
    """Dispatch executive_directors for each corps — using their assigned show."""
    from backend.api.app import get_task_manager
    from backend.api.v1.helpers import _get_root, _get_db_session

    root = _get_root()
    tm = get_task_manager()
    if not tm:
        return {"dispatched": [], "skipped": [], "error": "Task manager not running"}

    competition_id = round_entry.get("competition_id", "")
    corps_performances = round_entry.get("corps_performances")

    # Build corps_id -> show_slug mapping
    corps_shows: dict[str, str] = {}
    if corps_performances:
        for perf in corps_performances:
            corps_shows[perf["corps_id"]] = perf.get("show_slug", "tour")
    else:
        # Legacy: all corps get the same show
        show_slug = round_entry.get("show_slug", "tour")
        for cid in round_entry.get("corps_ids", []):
            corps_shows[cid] = show_slug

    dispatched, skipped = [], []
    for cid, show_slug in corps_shows.items():
        show_dir = root / "shows" / show_slug
        prompt_path = show_dir / "show_prompt.md"

        if not prompt_path.exists() or prompt_path.stat().st_size == 0:
            skipped.append({"corps_id": cid, "reason": f"No show_prompt.md for {show_slug}"})
            continue

        show_prompt = prompt_path.read_text(encoding="utf-8")

        db = _get_db_session()
        try:
            session_id = tm.get_session_for_role(db, cid, "executive_director")
            if not session_id:
                skipped.append({"corps_id": cid, "reason": "no ED session"})
                continue
            if tm.is_active(session_id):
                skipped.append({"corps_id": cid, "reason": "ED already active"})
                continue
            task_desc = (
                f"COMPETITION DISPATCH — Execute show for {competition_id}.\n\n"
                f"Implement the following show prompt:\n\n---\n\n{show_prompt}"
            )
            tm.start_agent(session_id=session_id, task_description=task_desc, corps_id=cid)
            dispatched.append({"corps_id": cid, "session_id": session_id})
        except Exception:
            logger.warning("Failed to dispatch ED for corps %s", cid, exc_info=True)
            skipped.append({"corps_id": cid, "reason": "dispatch error"})
        finally:
            db.close()

    logger.info(
        "Round dispatch: %d dispatched, %d skipped for %s",
        len(dispatched), len(skipped), competition_id,
    )
    return {"dispatched": dispatched, "skipped": skipped}


def _trigger_improvements(corps_ids: list[str], standings: dict) -> dict:
    from backend.api.v1.helpers import _get_db_session
    from backend.services.improvement import run_basics

    results = list(standings.get("results") or [])
    if not results:
        return {}

    leader_cutoff = max(1, len(results) // 4)
    leaders = {row["corps_id"] for row in results if row.get("rank", 999) <= leader_cutoff}

    summary: dict[str, dict[str, int]] = {}
    db = _get_db_session()
    try:
        for cid in corps_ids:
            captions = ["general_effect"] if cid in leaders else CAPTIONS
            summary[cid] = {"captions": len(captions)}
            for caption in captions:
                run_basics(db, cid, caption)
    finally:
        db.close()
    return summary
