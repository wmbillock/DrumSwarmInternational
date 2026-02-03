"""Tour coordinator service — schedules competition rounds and advances tour status."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from pathlib import Path

from backend.services.season_persistence import load_season, save_season
from backend.services.yaml_util import atomic_write, safe_dump_yaml


CAPTIONS = ["brass", "percussion", "guard", "visual", "general_effect", "ensemble_technique"]


def generate_schedule(season_dir: Path) -> list[dict]:
    """Create cross-divisional competition slots ensuring required_scores per corps."""
    data = load_season(season_dir)
    season_id = data.get("season_id", season_dir.name)
    corps_ids = list(data.get("registered_corps", []))
    if not corps_ids:
        return []

    config = data.get("config") or {}
    required_scores = int(config.get("required_scores", 1))
    corps_per_contest = int(config.get("corps_per_contest", max(2, len(corps_ids))))
    corps_per_contest = max(2, min(corps_per_contest, len(corps_ids)))

    counts = {cid: required_scores for cid in corps_ids}
    schedule: list[dict] = []
    round_num = 1

    while any(c > 0 for c in counts.values()):
        available = [cid for cid, remaining in counts.items() if remaining > 0]
        random.shuffle(available)
        slot = available[:corps_per_contest]
        if not slot:
            break
        for cid in slot:
            counts[cid] -= 1

        show_slug = _pick_show_slug(data, slot)
        schedule.append({
            "round": round_num,
            "competition_id": f"{season_id}-round-{round_num}",
            "show_slug": show_slug,
            "corps_ids": slot,
            "status": "pending",
        })
        round_num += 1

    return schedule


def run_competition_round(season_dir: Path) -> dict:
    """Score the next scheduled round and trigger improvement cycles."""
    data = load_season(season_dir)
    schedule = list(data.get("schedule") or [])
    if not schedule:
        schedule = generate_schedule(season_dir)
        data["schedule"] = schedule

    next_round = next((entry for entry in schedule if entry.get("status") != "completed"), None)
    if not next_round:
        return {"status": "complete", "message": "All rounds completed", "schedule": schedule}

    corps_ids = list(next_round.get("corps_ids") or [])
    if not corps_ids:
        next_round["status"] = "completed"
        save_season(season_dir, data)
        return {"status": "skipped", "round": next_round.get("round"), "schedule": schedule}

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

    history = [entry for entry in schedule if entry.get("status") == "completed"]
    current = next((entry for entry in schedule if entry.get("status") != "completed"), None)
    upcoming = [entry for entry in schedule if entry.get("status") == "pending"]

    return {
        "season_id": data.get("season_id", season_dir.name),
        "status": data.get("metadata", {}).get("status", "planning"),
        "current_round": current,
        "history": history,
        "upcoming": upcoming,
        "schedule": schedule,
    }


def _pick_show_slug(season_data: dict, corps_ids: list[str]) -> str:
    shows = list(season_data.get("shows") or [])
    if shows:
        return random.choice(shows)
    divisions = season_data.get("divisions") or {}
    for show_slug, roster in divisions.items():
        if any(cid in roster for cid in corps_ids):
            return show_slug
    return "tour"


def _score_round(season_dir: Path, round_entry: dict) -> dict:
    from backend.api.app import get_task_manager
    from backend.services.judge_service import judge_corps_performance
    from backend.services.scoring_engine import compute_standings
    from backend.services.scoring_service import CompositeScore, DEFAULT_WEIGHTS, record_score
    from backend.services.yaml_util import safe_dump_yaml
    from backend.api.v1.helpers import _get_db_session

    season_id = season_dir.name
    show_slug = round_entry.get("show_slug") or "tour"
    competition_id = round_entry.get("competition_id") or f"{season_id}-{show_slug}"
    corps_ids = list(round_entry.get("corps_ids") or [])

    tm = get_task_manager()
    llm_client = tm.llm_client if tm else None

    composites = {}
    db = _get_db_session()
    try:
        for cid in corps_ids:
            judge_results = judge_corps_performance(db, cid, show_slug, llm_client)
            caption_scores = {jt: jr.total_score for jt, jr in judge_results.items()}
            raw_total = sum(caption_scores[jt] * DEFAULT_WEIGHTS.get(jt, 0) for jt in caption_scores)
            composites[cid] = CompositeScore(
                caption_scores=caption_scores,
                raw_total=raw_total,
                penalties_total=0.0,
                final_score=raw_total,
                needs_rework=False,
                needs_escalation=False,
            )
            for jt, jr in judge_results.items():
                record_score(
                    db, corps_id=cid, judge_type=jt,
                    value=jr.total_score, box=max(1, min(5, int(jr.total_score / 20))),
                    feedback=jr.feedback,
                    rep_score=jr.rep_score, perf_score=jr.perf_score,
                )
    finally:
        db.close()

    standings = compute_standings(season_id, DEFAULT_WEIGHTS, composites)

    standings_data = {
        "season_id": season_id,
        "competition_id": competition_id,
        "show_slug": show_slug,
        "generated_at": standings.generated_at,
        "results": [
            {
                "corps_id": r.corps_id,
                "rank": r.rank,
                "final_score": r.final_score,
                "raw_score": r.raw_score,
                "caption_scores": {jt.value: v for jt, v in r.caption_scores.items()},
            }
            for r in standings.results
        ],
    }
    atomic_write(season_dir / "standings.yaml", safe_dump_yaml(standings_data))
    return standings_data


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
