"""Unified competition execution pipeline.

Extracts the full scoring pipeline (judge → tapes → critique → reputation → standings)
into a reusable service that both the /run endpoint and tour_coordinator share.
"""

import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.judging_tape import JudgingTape
from backend.models.score import Score
from backend.models.score import JudgeType
from backend.services.scoring_service import CompositeScore, DEFAULT_WEIGHTS, record_score
from backend.services.scoring_engine import compute_standings
from backend.services.judge_service import judge_corps_performance, generate_judges_tape, export_tape_markdown
from backend.services.yaml_util import atomic_write, safe_dump_yaml
from backend.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CompetitionResult:
    score: Score
    tape: JudgingTape


def record_competition_result(
    db: Session,
    *,
    season_event_id: str,
    corps_id: str,
    rep_id: str | None,
    artifact_id: str | None,
    score_payload: dict,
    tape_text: str,
) -> CompetitionResult:
    if rep_id is None and artifact_id is None:
        raise ValueError("Competition result must link to rep_id or artifact_id.")

    caption = str(score_payload["caption"])
    value = float(score_payload["value"])
    judge_type = JudgeType(caption)
    score = Score(
        corps_id=corps_id,
        rep_id=rep_id,
        season_event_id=season_event_id,
        artifact_id=artifact_id,
        judge_type=judge_type,
        value=value,
        box=max(1, min(5, int(value / 20))),
    )
    tape = JudgingTape(
        season_event_id=season_event_id,
        corps_id=corps_id,
        rep_id=rep_id,
        artifact_id=artifact_id,
        caption=caption,
        tape_text=tape_text,
    )
    db.add(score)
    db.add(tape)
    db.commit()
    db.refresh(score)
    db.refresh(tape)
    return CompetitionResult(score=score, tape=tape)


def execute_competition(
    db: Session,
    competition_id: str,
    season_id: str,
    show_slug: str,
    corps_ids: list[str],
    season_dir: Path,
    llm_client: Optional[LLMClient] = None,
    *,
    generate_tapes: bool = True,
    run_critique: bool = True,
    record_reputation: bool = True,
) -> dict:
    """Full scoring pipeline: judge → tapes → critique → reputation → standings.

    Returns a dict with standings_data, auto_critique_summary, and scoring_errors.
    """
    from backend.api.v1.helpers import _get_root

    root = _get_root()

    # --- Pre-filter: skip corps that already have enough scores ---
    required_scores = 1
    season_yaml = season_dir / "season.yaml"
    if season_yaml.is_file():
        try:
            from backend.services.yaml_util import safe_load_yaml_dict
            season_data = safe_load_yaml_dict(season_yaml.read_text(encoding="utf-8"))
            required_scores = int((season_data.get("config") or {}).get("required_scores", 1))
        except Exception:
            pass

    eligible_corps = []
    for cid in corps_ids:
        perf_dir = season_dir / "performances" / cid
        existing_count = len(list(perf_dir.glob("critique_round_*.md"))) if perf_dir.exists() else 0
        if existing_count >= required_scores:
            logger.info("Corps %s already has %d/%d scores, skipping", cid, existing_count, required_scores)
        else:
            eligible_corps.append(cid)

    corps_ids = eligible_corps

    # --- Phase 1: Judge each corps ---
    composites: dict[str, CompositeScore] = {}
    judge_results_all: dict[str, dict] = {}
    scoring_errors: list[str] = []

    for cid in corps_ids:
        try:
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
            # Persist individual judge scores
            for jt, jr in judge_results.items():
                record_score(
                    db, corps_id=cid, judge_type=jt,
                    value=jr.total_score, box=max(1, min(5, int(jr.total_score / 20))),
                    feedback=jr.feedback,
                    rep_score=jr.rep_score, perf_score=jr.perf_score,
                )
        except Exception:
            logger.warning("Scoring failed for corps %s in %s, skipping", cid, show_slug, exc_info=True)
            scoring_errors.append(cid)

    # --- Phase 2: Compute standings ---
    standings = compute_standings(season_id, DEFAULT_WEIGHTS, composites)

    # Build per-corps caption detail (rep/perf/tot) for recap sheets
    corps_caption_details: dict[str, dict[str, dict[str, float]]] = {}
    for cid, jr_map in judge_results_all.items():
        details: dict[str, dict[str, float]] = {}
        for jt, jr in jr_map.items():
            details[jt.value] = {
                "rep": jr.rep_score,
                "perf": jr.perf_score,
                "tot": jr.total_score,
            }
        corps_caption_details[cid] = details

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
                "caption_details": corps_caption_details.get(r.corps_id, {}),
            }
            for r in standings.results
        ],
    }
    if scoring_errors:
        standings_data["scoring_errors"] = scoring_errors

    # Write standings files
    atomic_write(season_dir / "standings.yaml", safe_dump_yaml(standings_data))
    if competition_id:
        atomic_write(season_dir / f"standings_{competition_id}.yaml", safe_dump_yaml(standings_data))

    # Write per-corps score files
    for cid in corps_ids:
        if cid in composites:
            composite = composites[cid]
            scores_data = {
                "corps_id": cid,
                "show_slug": show_slug,
                "caption_scores": {jt.value: v for jt, v in composite.caption_scores.items()},
                "raw_total": composite.raw_total,
                "final_score": composite.final_score,
            }
            perf_dir = season_dir / "performances" / cid
            perf_dir.mkdir(parents=True, exist_ok=True)
            atomic_write(perf_dir / "scores.yaml", safe_dump_yaml(scores_data))

    # --- Record durable performance records ---
    try:
        from backend.services.artifact_tracker import record_standings as _record_standings
        import re
        round_match = re.search(r"round-(\d+)$", competition_id or "")
        round_num_val = int(round_match.group(1)) if round_match else 0
        _record_standings(
            db,
            season_id=season_id,
            competition_id=competition_id or f"{season_id}-unset",
            show_slug=show_slug,
            round_number=round_num_val,
            standings=standings_data.get("results", []),
            completed_at=standings_data.get("generated_at"),
        )
    except Exception:
        logger.warning("Failed to record durable performance records", exc_info=True)

    # --- Phase 3: Reputation ---
    if record_reputation:
        try:
            from backend.services.reputation import record_corps_placement
            for r in standings.results:
                corps_dir = root / "corps" / r.corps_id
                if corps_dir.exists():
                    record_corps_placement(corps_dir, season_id, r.rank, r.final_score,
                                           notes=f"show:{show_slug}")
        except Exception:
            logger.warning("Reputation recording failed", exc_info=True)

    # --- Phase 4: Judge tapes ---
    if generate_tapes:
        for cid in corps_ids:
            if cid in scoring_errors:
                continue
            try:
                perf_dir = season_dir / "performances" / cid
                perf_dir.mkdir(parents=True, exist_ok=True)
                # Find next critique round number
                max_round = 0
                for path in perf_dir.glob("critique_round_*.md"):
                    stem = path.stem.replace("critique_round_", "")
                    if stem.isdigit():
                        max_round = max(max_round, int(stem))
                round_num = max_round + 1
                tape = generate_judges_tape(db, competition_id, cid, llm_client)
                critique_md = export_tape_markdown(tape)
                atomic_write(perf_dir / f"critique_round_{round_num}.md", critique_md)
            except Exception:
                logger.warning("Tape generation failed for corps %s", cid, exc_info=True)

    # --- Phase 4b: Evaluate performer trust ---
    for cid in corps_ids:
        if cid in scoring_errors:
            continue
        try:
            from backend.services.evaluation_service import evaluate_corps
            evaluate_corps(db, cid)
        except Exception:
            logger.warning("Performer evaluation failed for corps %s", cid, exc_info=True)

    # --- Phase 5: Auto-critique bottom 75% ---
    auto_critique_summary = {}
    if run_critique:
        try:
            from backend.services.auto_critique import run_auto_critique
            auto_critique_summary = run_auto_critique(
                db, competition_id, standings_data["results"], llm_client
            )
        except Exception:
            logger.warning("Auto-critique failed", exc_info=True)

    return {
        "competition_id": competition_id,
        "standings_data": standings_data,
        "auto_critique_summary": auto_critique_summary,
        "scoring_errors": scoring_errors,
    }
