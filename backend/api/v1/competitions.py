"""V1 API router — Competition endpoints.

Extracted from the monolithic router.py. All business logic lives in
backend/services/. These routes only translate HTTP <-> service calls.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _get_root, _validate_id, _get_db_session, _parse_competition_id
from backend.api.v1.schemas import CreateCompetitionRequest, StartCritiqueRequest, ContestEvaluateRequest
from backend.services.yaml_util import safe_load_yaml_dict

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


def _next_critique_round(perf_dir: Path) -> int:
    max_round = 0
    for path in perf_dir.glob("critique_round_*.md"):
        stem = path.stem.replace("critique_round_", "")
        if stem.isdigit():
            max_round = max(max_round, int(stem))
    return max_round + 1


# =========================================================================
# COMPETITIONS
# =========================================================================


@router.get("/competitions")
def v1_list_competitions():
    """List all competitions (season-show pairs with registered corps)."""
    root = _get_root()
    seasons_dir = root / "seasons"
    if not seasons_dir.exists():
        return []
    results = []
    seen_ids: set[str] = set()
    for season_dir in sorted(seasons_dir.iterdir()):
        if not season_dir.is_dir():
            continue
        season_yaml = season_dir / "season.yaml"
        if not season_yaml.is_file():
            continue
        season_data = safe_load_yaml_dict(season_yaml.read_text(encoding="utf-8"))
        season_id = season_data.get("season_id", season_dir.name)
        from backend.services.season_persistence import list_registered_corps
        corps_ids = list_registered_corps(season_dir)

        # Collect competitions from schedule (tour coordinator creates these)
        schedule = season_data.get("schedule") or []
        for entry in schedule:
            cid = entry.get("competition_id")
            slug = entry.get("show_slug", "")
            if cid and cid not in seen_ids:
                entry_corps = entry.get("corps_ids", corps_ids)
                status = entry.get("status", "pending")
                if status == "completed":
                    status = "completed"
                elif status in ("running", "in_progress"):
                    status = "active"
                else:
                    status = "pending"
                results.append({
                    "competition_id": cid,
                    "season_id": season_id,
                    "show_slug": slug,
                    "corps_ids": entry_corps,
                    "status": status,
                })
                seen_ids.add(cid)

        # Find shows used in this season by scanning performances
        show_slugs: set[str] = set()
        perf_root = season_dir / "performances"
        if perf_root.exists():
            for corps_dir in perf_root.iterdir():
                if not corps_dir.is_dir():
                    continue
                for run_dir in corps_dir.iterdir():
                    manifest_path = run_dir / "manifest.yaml"
                    if manifest_path.is_file():
                        try:
                            m = safe_load_yaml_dict(manifest_path.read_text(encoding="utf-8"))
                            if isinstance(m, dict) and m.get("show_slug"):
                                show_slugs.add(m["show_slug"])
                        except Exception:
                            pass
        # Also check standings for show_slug
        standings_path = season_dir / "standings.yaml"
        if standings_path.exists():
            try:
                st = safe_load_yaml_dict(standings_path.read_text(encoding="utf-8"))
                if isinstance(st, dict) and st.get("show_slug"):
                    show_slugs.add(st["show_slug"])
            except Exception:
                pass
        # Also check per-corps scores.yaml for show_slug
        if perf_root.exists():
            for corps_dir in perf_root.iterdir():
                if not corps_dir.is_dir():
                    continue
                scores_path = corps_dir / "scores.yaml"
                if scores_path.is_file():
                    try:
                        sc = safe_load_yaml_dict(scores_path.read_text(encoding="utf-8"))
                        if isinstance(sc, dict) and sc.get("show_slug"):
                            show_slugs.add(sc["show_slug"])
                    except Exception:
                        pass
        for show_slug in show_slugs:
            competition_id = f"{season_id}-{show_slug}"
            if competition_id in seen_ids:
                continue
            results.append({
                "competition_id": competition_id,
                "season_id": season_id,
                "show_slug": show_slug,
                "corps_ids": corps_ids,
                "status": "completed" if standings_path.exists() else "ready",
            })
            seen_ids.add(competition_id)
    return results


@router.get("/competitions/recent-activity")
def v1_recent_activity():
    """Return the most recent completed competition rounds across all seasons."""
    root = _get_root()
    seasons_dir = root / "seasons"
    if not seasons_dir.exists():
        return []

    completed_rounds: list[dict] = []
    for season_dir in seasons_dir.iterdir():
        if not season_dir.is_dir():
            continue
        season_yaml = season_dir / "season.yaml"
        if not season_yaml.is_file():
            continue
        data = safe_load_yaml_dict(season_yaml.read_text(encoding="utf-8"))
        season_id = data.get("season_id", season_dir.name)
        for entry in (data.get("schedule") or []):
            if entry.get("status") != "completed":
                continue
            standings = entry.get("standings") or []
            top3 = standings[:3] if isinstance(standings, list) else []
            completed_rounds.append({
                "round": entry.get("round"),
                "competition_id": entry.get("competition_id", ""),
                "season_id": season_id,
                "show_slug": entry.get("show_slug", ""),
                "completed_at": entry.get("completed_at", ""),
                "top_standings": top3,
            })

    completed_rounds.sort(key=lambda r: r.get("completed_at") or "", reverse=True)
    result = completed_rounds[:10]

    # Enrich standings with corps names from DB
    all_corps_ids = set()
    for rnd in result:
        for s in rnd.get("top_standings", []):
            cid = s.get("corps_id")
            if cid:
                all_corps_ids.add(cid)
    if all_corps_ids:
        try:
            from backend.api.v1.helpers import _get_db_session
            from backend.models.corps import Corps
            db = _get_db_session()
            try:
                corps_rows = db.query(Corps.id, Corps.name).filter(Corps.id.in_(all_corps_ids)).all()
                name_map = {c.id: c.name for c in corps_rows}
            finally:
                db.close()
            for rnd in result:
                for s in rnd.get("top_standings", []):
                    cid = s.get("corps_id")
                    if cid and cid in name_map:
                        s["corps_name"] = name_map[cid]
        except Exception:
            pass  # Graceful degradation — UUIDs still shown

    return result


@router.post("/competitions")
def v1_create_competition(req: CreateCompetitionRequest):
    """Create a competition — validates and registers corps in season."""
    root = _get_root()

    season_dir = root / "seasons" / req.season_id
    if not (season_dir / "season.yaml").exists():
        raise HTTPException(404, f"Season '{req.season_id}' not found")

    show_dir = root / "shows" / req.show_slug
    if not (show_dir / "status.yaml").exists():
        raise HTTPException(404, f"Show '{req.show_slug}' not found")
    from backend.services.show_persistence import check_field_ready
    if not check_field_ready(show_dir):
        raise HTTPException(400, f"Show '{req.show_slug}' is not approved")

    # Validate corps exist (filesystem or DB) and register in season
    for cid in req.corps_ids:
        corps_dir = root / "corps" / cid
        if (corps_dir / "corps.yaml").exists():
            from backend.services.season_persistence import register_corps
            register_corps(season_dir, cid, root / "corps")
        else:
            # Check DB for this corps
            try:
                from backend.models.corps import Corps
                db = _get_db_session()
                try:
                    corps = db.get(Corps, cid)
                    if not corps:
                        raise HTTPException(404, f"Corps '{cid}' not found")
                    # Create performance directory directly (skip filesystem corps check)
                    perf_dir = season_dir / "performances" / cid
                    perf_dir.mkdir(parents=True, exist_ok=True)
                finally:
                    db.close()
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(404, f"Corps '{cid}' not found")

    competition_id = f"{req.season_id}-{req.show_slug}"
    return {
        "competition_id": competition_id,
        "season_id": req.season_id,
        "show_slug": req.show_slug,
        "corps_ids": req.corps_ids,
        "status": "ready",
    }


@router.post("/competitions/{competition_id}/run")
def v1_run_competition(competition_id: str):
    """Run a competition heat — deterministic stub scoring + standings."""
    root = _get_root()
    season_id, show_slug = _parse_competition_id(competition_id, root)

    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").exists():
        raise HTTPException(404, f"Season '{season_id}' not found")

    show_dir = root / "shows" / show_slug
    if not (show_dir / "status.yaml").exists():
        raise HTTPException(404, f"Show '{show_slug}' not found")

    from backend.services.season_persistence import list_registered_corps
    corps_ids = list_registered_corps(season_dir)
    if not corps_ids:
        raise HTTPException(400, "No corps registered for this season")

    # Filter to corps that still exist (filesystem or DB), skip stale entries
    valid_corps_ids = []
    for cid in corps_ids:
        if (root / "corps" / cid / "corps.yaml").exists():
            valid_corps_ids.append(cid)
        else:
            try:
                from backend.models.corps import Corps as CorpsModel
                db = _get_db_session()
                try:
                    if db.get(CorpsModel, cid):
                        valid_corps_ids.append(cid)
                finally:
                    db.close()
            except Exception:
                pass  # Skip corps that can't be found
    corps_ids = valid_corps_ids
    if not corps_ids:
        raise HTTPException(400, "No valid corps remaining for this competition")

    from backend.models.score import JudgeType
    from backend.services.scoring_service import CompositeScore, DEFAULT_WEIGHTS
    from backend.services.scoring_engine import compute_standings
    from backend.services.yaml_util import atomic_write, safe_dump_yaml

    from backend.services.judge_service import judge_corps_performance

    # Get LLM client for real judging
    from backend.api.app import get_task_manager
    tm = get_task_manager()
    llm_client = tm.llm_client if tm else None

    composites = {}
    judge_results_all = {}
    db = None
    try:
        db = _get_db_session()
        for cid in corps_ids:
            judge_results = judge_corps_performance(db, cid, show_slug, llm_client)
            judge_results_all[cid] = judge_results
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

            # Store scores in DB with rep/perf split
            from backend.services.scoring_service import record_score
            for jt, jr in judge_results.items():
                record_score(
                    db, corps_id=cid, judge_type=jt,
                    value=jr.total_score, box=max(1, min(5, int(jr.total_score / 20))),
                    feedback=jr.feedback,
                    rep_score=jr.rep_score, perf_score=jr.perf_score,
                )
    finally:
        if db:
            db.close()

    standings = compute_standings(season_id, DEFAULT_WEIGHTS, composites)

    standings_data = {
        "season_id": standings.season_id,
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

    for cid in corps_ids:
        composite = composites[cid]
        scores_data = {
            "corps_id": cid,
            "show_slug": show_slug,
            "caption_scores": {jt.value: v for jt, v in composite.caption_scores.items()},
            "raw_total": composite.raw_total,
            "final_score": composite.final_score,
        }
        perf_dir = season_dir / "performances" / cid
        atomic_write(perf_dir / "scores.yaml", safe_dump_yaml(scores_data))

    from backend.services.reputation import record_corps_placement
    for r in standings.results:
        corps_dir = root / "corps" / r.corps_id
        if corps_dir.exists():
            record_corps_placement(corps_dir, season_id, r.rank, r.final_score,
                                   notes=f"show:{show_slug}")

    # Persist critique markdown per corps
    from backend.services.judge_service import generate_judges_tape, export_tape_markdown
    critique_db = _get_db_session()
    try:
        for cid in corps_ids:
            perf_dir = season_dir / "performances" / cid
            perf_dir.mkdir(parents=True, exist_ok=True)
            round_num = _next_critique_round(perf_dir)
            tape = generate_judges_tape(critique_db, competition_id, cid, llm_client)
            critique_md = export_tape_markdown(tape)
            atomic_write(perf_dir / f"critique_round_{round_num}.md", critique_md)
    finally:
        critique_db.close()

    # Auto-critique bottom 75% corps
    auto_critique_summary = {}
    try:
        from backend.services.auto_critique import run_auto_critique
        critique_db = _get_db_session()
        try:
            auto_critique_summary = run_auto_critique(
                critique_db, competition_id, standings_data["results"], llm_client
            )
        finally:
            critique_db.close()
    except Exception as e:
        logger.warning("Auto-critique failed: %s", e)

    return {
        "competition_id": competition_id,
        "status": "completed",
        "standings": standings_data["results"],
        "auto_critique_summary": auto_critique_summary,
    }


@router.post("/competitions/{competition_id}/dispatch")
async def v1_dispatch_competition(competition_id: str):
    """Dispatch agents to execute the show prompt for a competition.

    For each registered corps, finds the executive_director session and dispatches
    it with the show_prompt.md as the task. This is the step that turns a competition
    from "scored" to "actually executed by agents writing code."
    """
    root = _get_root()
    season_id, show_slug = _parse_competition_id(competition_id, root)

    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").exists():
        raise HTTPException(404, f"Season '{season_id}' not found")

    show_dir = root / "shows" / show_slug
    prompt_path = show_dir / "show_prompt.md"
    if not prompt_path.exists() or prompt_path.stat().st_size == 0:
        raise HTTPException(400, f"Show '{show_slug}' has no show_prompt.md — run Design Room first")

    show_prompt = prompt_path.read_text(encoding="utf-8")

    from backend.services.season_persistence import list_registered_corps
    corps_ids = list_registered_corps(season_dir)
    if not corps_ids:
        raise HTTPException(400, "No corps registered for this season")

    from backend.api.app import get_task_manager
    tm = get_task_manager()
    if not tm:
        raise HTTPException(503, "Task manager not initialized")

    dispatched = []
    skipped = []
    for cid in corps_ids:
        db = _get_db_session()
        try:
            ed_session = tm.get_session_for_role(db, cid, "executive_director")
            if not ed_session:
                skipped.append({"corps_id": cid, "reason": "no ED session found"})
                continue
            if tm.is_active(ed_session):
                skipped.append({"corps_id": cid, "reason": "ED already active"})
                continue

            task_desc = (
                f"COMPETITION DISPATCH — Execute this show for competition {competition_id}.\n\n"
                f"Your corps has been assigned to implement the following show. "
                f"Read the prompt carefully and coordinate your corps to write the code.\n\n"
                f"---\n\n{show_prompt}"
            )
            tm.start_agent(
                session_id=ed_session,
                task_description=task_desc,
                corps_id=cid,
            )
            dispatched.append({"corps_id": cid, "session_id": ed_session})
        finally:
            db.close()

    return {
        "competition_id": competition_id,
        "show_slug": show_slug,
        "dispatched": dispatched,
        "skipped": skipped,
        "total_dispatched": len(dispatched),
        "total_skipped": len(skipped),
    }


@router.get("/competitions/{competition_id}/scores")
def v1_get_competition_scores(competition_id: str):
    """Retrieve scores/standings for a completed competition."""
    root = _get_root()
    season_id, _show_slug = _parse_competition_id(competition_id, root)
    season_dir = root / "seasons" / season_id

    standings = None

    # 1. Try per-round standings file (written by tour_coordinator)
    per_round_path = season_dir / f"standings_{competition_id}.yaml"
    if per_round_path.is_file():
        standings = safe_load_yaml_dict(per_round_path.read_text(encoding="utf-8"))

    # 2. Try schedule entry embedded standings (tour_coordinator saves here)
    if not standings or not standings.get("results"):
        season_yaml = season_dir / "season.yaml"
        if season_yaml.is_file():
            season_data = safe_load_yaml_dict(season_yaml.read_text(encoding="utf-8"))
            for entry in (season_data.get("schedule") or []):
                if entry.get("competition_id") == competition_id and entry.get("standings"):
                    standings = {
                        "season_id": season_id,
                        "show_slug": entry.get("show_slug", _show_slug),
                        "generated_at": entry.get("completed_at", ""),
                        "results": entry["standings"],
                    }
                    break

    # 3. Fall back to global standings.yaml (legacy / non-round competitions)
    if not standings or not standings.get("results"):
        standings_path = season_dir / "standings.yaml"
        if standings_path.is_file():
            standings = safe_load_yaml_dict(standings_path.read_text(encoding="utf-8"))

    if not standings or not standings.get("results"):
        raise HTTPException(404, "Standings not found — competition may not have run yet")

    standings["competition_id"] = competition_id
    standings["show_slug"] = standings.get("show_slug", _show_slug)

    # Resolve corps_id → display_name for each result
    if "results" in standings:
        corps_name_cache: dict[str, str] = {}
        for result in standings["results"]:
            cid = result.get("corps_id", "")
            if cid not in corps_name_cache:
                # Try filesystem
                corps_yaml = root / "corps" / cid / "corps.yaml"
                if corps_yaml.is_file():
                    try:
                        data = safe_load_yaml_dict(corps_yaml.read_text(encoding="utf-8"))
                        corps_name_cache[cid] = data.get("display_name", cid)
                    except Exception:
                        corps_name_cache[cid] = cid
                else:
                    # Try DB
                    try:
                        from backend.models.corps import Corps as CorpsModel
                        db = _get_db_session()
                        try:
                            corps = db.get(CorpsModel, cid)
                            corps_name_cache[cid] = corps.name if corps else cid
                        finally:
                            db.close()
                    except Exception:
                        corps_name_cache[cid] = cid
            result["display_name"] = corps_name_cache[cid]

    return standings


@router.get("/competitions/{competition_id}/corps/{corps_id}/breakdown")
def v1_get_corps_breakdown(competition_id: str, corps_id: str):
    """Per-caption score breakdown with weights and synthetic commentary."""
    _validate_id(corps_id, "corps_id")
    root = _get_root()
    season_id, show_slug = _parse_competition_id(competition_id, root)

    scores_path = root / "seasons" / season_id / "performances" / corps_id / "scores.yaml"
    if not scores_path.exists():
        raise HTTPException(404, "Scores not found for this corps in this competition")

    data = safe_load_yaml_dict(scores_path.read_text(encoding="utf-8"))
    caption_scores_raw = data.get("caption_scores", {})

    from backend.services.scoring_service import DEFAULT_WEIGHTS
    from backend.models.score import JudgeType

    weight_map = {jt.value: w for jt, w in DEFAULT_WEIGHTS.items()}

    caption_detail: dict = {}
    commentary: dict = {}
    for caption, score in caption_scores_raw.items():
        w = weight_map.get(caption, 0.0)
        caption_detail[caption] = {
            "score": score,
            "weight": w,
            "weighted": round(score * w, 2),
        }
        if score >= 85:
            commentary[caption] = f"Excellent {caption} performance — top-tier execution."
        elif score >= 70:
            commentary[caption] = f"Solid {caption} showing with room for refinement."
        elif score >= 60:
            commentary[caption] = f"{caption.capitalize()} section needs focused reps — approaching rework threshold."
        else:
            commentary[caption] = f"{caption.capitalize()} section below standards — rework recommended."

    return {
        "corps_id": corps_id,
        "caption_scores": caption_detail,
        "penalties_total": data.get("penalties_total", 0.0),
        "final_score": data.get("final_score", 0.0),
        "commentary": commentary,
    }


@router.get("/competitions/{competition_id}/reports/{corps_id}")
def v1_get_judge_report(competition_id: str, corps_id: str):
    """Get automated judge report for a corps in a competition."""
    _validate_id(corps_id, "corps_id")
    from backend.services.scoring_service import generate_judge_report
    db = _get_db_session()
    try:
        report = generate_judge_report(db, corps_id, competition_id)
        return report
    finally:
        db.close()


@router.post("/competitions/{competition_id}/reports/generate-all")
def v1_generate_all_reports(competition_id: str):
    """Generate judge reports for all corps in a competition."""
    root = _get_root()
    season_id, show_slug = _parse_competition_id(competition_id, root)
    perf_dir = root / "seasons" / season_id / "performances"

    if not perf_dir.exists():
        return {"reports": [], "count": 0}

    from backend.services.scoring_service import generate_judge_report
    db = _get_db_session()
    try:
        reports = []
        for corps_dir in perf_dir.iterdir():
            if corps_dir.is_dir():
                corps_id = corps_dir.name
                report = generate_judge_report(db, corps_id, competition_id)
                reports.append(report)
        return {"reports": reports, "count": len(reports)}
    finally:
        db.close()


# =========================================================================
# JUDGES TAPES & RECAP
# =========================================================================


@router.get("/competitions/{competition_id}/tapes")
def v1_list_tapes(competition_id: str):
    """List all judges tapes for a competition."""
    from backend.models.judges_tape import JudgesTape
    db = _get_db_session()
    try:
        tapes = db.query(JudgesTape).filter(
            JudgesTape.competition_id == competition_id
        ).all()
        return [
            {
                "id": t.id,
                "competition_id": t.competition_id,
                "corps_id": t.corps_id,
                "overall_assessment": t.overall_assessment,
                "caption_count": len(t.caption_feedbacks or {}),
                "created_at": str(t.created_at),
            }
            for t in tapes
        ]
    finally:
        db.close()


@router.get("/competitions/{competition_id}/tapes/{corps_id}")
def v1_get_tape(competition_id: str, corps_id: str):
    """Get detailed judges tape for a corps in a competition."""
    _validate_id(corps_id, "corps_id")
    from backend.models.judges_tape import JudgesTape
    db = _get_db_session()
    try:
        tape = db.query(JudgesTape).filter(
            JudgesTape.competition_id == competition_id,
            JudgesTape.corps_id == corps_id,
        ).order_by(JudgesTape.created_at.desc()).first()

        if not tape:
            # Generate on-demand
            from backend.services.judge_service import generate_judges_tape
            from backend.api.app import get_task_manager
            tm = get_task_manager()
            llm_client = tm.llm_client if tm else None
            tape = generate_judges_tape(db, competition_id, corps_id, llm_client)

        return {
            "id": tape.id,
            "competition_id": tape.competition_id,
            "corps_id": tape.corps_id,
            "caption_feedbacks": tape.caption_feedbacks,
            "overall_assessment": tape.overall_assessment,
            "created_at": str(tape.created_at),
        }
    finally:
        db.close()


@router.get("/competitions/{competition_id}/tapes/{corps_id}/export")
def v1_export_tape(competition_id: str, corps_id: str):
    """Export judges tape as markdown."""
    _validate_id(corps_id, "corps_id")
    from backend.models.judges_tape import JudgesTape
    from backend.services.judge_service import export_tape_markdown, generate_judges_tape
    db = _get_db_session()
    try:
        tape = db.query(JudgesTape).filter(
            JudgesTape.competition_id == competition_id,
            JudgesTape.corps_id == corps_id,
        ).order_by(JudgesTape.created_at.desc()).first()

        if not tape:
            from backend.api.app import get_task_manager
            tm = get_task_manager()
            llm_client = tm.llm_client if tm else None
            tape = generate_judges_tape(db, competition_id, corps_id, llm_client)

        return {"markdown": export_tape_markdown(tape), "corps_id": corps_id}
    finally:
        db.close()


@router.get("/competitions/{competition_id}/recap")
def v1_get_recap(competition_id: str, format: str = "json"):
    """Get recap sheet for a competition. format: json, markdown, csv."""
    root = _get_root()
    season_id, show_slug = _parse_competition_id(competition_id, root)

    from backend.services.recap_sheet import (
        generate_recap_sheet, export_recap_markdown, export_recap_csv,
    )

    rows = generate_recap_sheet(season_id, show_slug)
    if not rows:
        if format == "json":
            return []
        rows = []

    if format == "markdown":
        return {"markdown": export_recap_markdown(rows)}
    elif format == "csv":
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            content=export_recap_csv(rows),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=recap_{competition_id}.csv"},
        )
    else:
        return [
            {
                "rank": r.rank,
                "corps_id": r.corps_id,
                "corps_name": r.corps_name,
                "caption_scores": r.caption_scores,
                "penalties_total": r.penalties_total,
                "raw_total": r.raw_total,
                "final_score": r.final_score,
            }
            for r in rows
        ]


# =========================================================================
# CRITIQUE SESSIONS
# =========================================================================


@router.post("/competitions/{competition_id}/critique")
def v1_start_critique(competition_id: str, req: StartCritiqueRequest):
    """Start a critique session between a judge and staff member."""
    _validate_id(req.corps_id, "corps_id")
    from backend.services.critique_service import start_critique
    from backend.api.app import get_task_manager
    tm = get_task_manager()
    llm_client = tm.llm_client if tm else None

    db = _get_db_session()
    try:
        session = start_critique(db, competition_id, req.corps_id, req.judge_type, llm_client)
        return {
            "id": session.id,
            "competition_id": session.competition_id,
            "corps_id": session.corps_id,
            "judge_type": session.judge_type,
            "staff_role": session.staff_role,
            "status": session.status.value,
            "conversation": session.conversation,
            "action_items": session.action_items,
            "created_at": str(session.created_at),
            "is_automated": getattr(session, "is_automated", False),
        }
    finally:
        db.close()


@router.post("/contest/evaluate")
def v1_contest_evaluate(req: ContestEvaluateRequest):
    """Find all READY_FOR_CONTEST corps and run a competition between them.

    After scoring, transitions each participating corps to COMPLETED.
    """
    from backend.models.corps import Corps, CorpsStatus
    from backend.models.score import JudgeType
    from backend.services.scoring_service import CompositeScore, DEFAULT_WEIGHTS
    from backend.services.scoring_engine import compute_standings
    from backend.services.yaml_util import atomic_write, safe_dump_yaml

    root = _get_root()

    season_dir = root / "seasons" / req.season_id
    if not (season_dir / "season.yaml").exists():
        raise HTTPException(404, f"Season '{req.season_id}' not found")

    show_dir = root / "shows" / req.show_slug
    if not (show_dir / "status.yaml").exists():
        raise HTTPException(404, f"Show '{req.show_slug}' not found")

    db = _get_db_session()
    try:
        ready_corps = db.query(Corps).filter(
            Corps.status == CorpsStatus.READY_FOR_CONTEST
        ).all()
        if not ready_corps:
            raise HTTPException(400, "No corps in READY_FOR_CONTEST state")

        corps_ids = [c.id for c in ready_corps]

        # Ensure performance directories exist
        for cid in corps_ids:
            perf_dir = season_dir / "performances" / cid
            perf_dir.mkdir(parents=True, exist_ok=True)

        # Score using real LLM judging (falls back to stubs if unavailable)
        from backend.services.judge_service import judge_corps_performance
        from backend.api.app import get_task_manager
        tm = get_task_manager()
        llm_client = tm.llm_client if tm else None

        composites = {}
        for cid in corps_ids:
            judge_results = judge_corps_performance(db, cid, req.show_slug, llm_client)
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

            # Persist individual judge scores
            from backend.services.scoring_service import record_score
            for jt, jr in judge_results.items():
                record_score(
                    db, corps_id=cid, judge_type=jt,
                    value=jr.total_score, box=max(1, min(5, int(jr.total_score / 20))),
                    feedback=jr.feedback,
                    rep_score=jr.rep_score, perf_score=jr.perf_score,
                )

        standings = compute_standings(req.season_id, DEFAULT_WEIGHTS, composites)

        standings_data = {
            "season_id": standings.season_id,
            "generated_at": standings.generated_at,
            "show_slug": req.show_slug,
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

        # Write per-corps scores
        for cid in corps_ids:
            composite = composites[cid]
            scores_data = {
                "corps_id": cid,
                "show_slug": req.show_slug,
                "caption_scores": {jt.value: v for jt, v in composite.caption_scores.items()},
                "raw_total": composite.raw_total,
                "final_score": composite.final_score,
            }
            perf_dir = season_dir / "performances" / cid
            atomic_write(perf_dir / "scores.yaml", safe_dump_yaml(scores_data))

        # Transition all participating corps to COMPLETED
        for c in ready_corps:
            c.status = CorpsStatus.COMPLETED
        db.commit()

        # Record reputation for filesystem corps
        from backend.services.reputation import record_corps_placement
        for r in standings.results:
            corps_dir = root / "corps" / r.corps_id
            if corps_dir.exists():
                record_corps_placement(
                    corps_dir, req.season_id, r.rank, r.final_score,
                    notes=f"show:{req.show_slug}",
                )

        return {
            "status": "completed",
            "corps_evaluated": len(corps_ids),
            "standings": standings_data["results"],
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Contest evaluation failed: {e}")
    finally:
        db.close()


def _stub_caption_scores(corps_id: str, show_slug: str) -> dict:
    """Deterministic fallback scores. Delegates to shared utility."""
    from backend.services.scoring_utils import stub_caption_scores
    return stub_caption_scores(corps_id, show_slug)
