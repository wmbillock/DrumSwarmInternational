"""Judging & Critique API routes — judge tapes, critique-to-actions, export."""

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import create_db_engine, create_session_factory

router = APIRouter()

# Tag-to-role routing for critique action items
CAPTION_TO_ROLE = {
    "brass": "brass_caption_head",
    "percussion": "percussion_caption_head",
    "guard": "guard_caption_head",
    "visual": "visual_caption_head",
    "general_effect": "program_coordinator",
    "ensemble_technique": "program_coordinator",
    "timing": "timing_judge",
}


def _get_db():
    from backend.api.app import get_db
    return get_db()


@router.get("/api/judging/corps/{corps_id}/tapes")
def api_get_judge_tapes(corps_id: str, db: Session = Depends(_get_db)):
    """Get all judge tapes (per-rep critique summaries) for a corps."""
    from backend.models.rep import Rep, RepStatus
    from backend.models.score import Score
    from backend.models.segment import Segment
    from backend.services.scoring_service import compute_composite

    # Find all scored reps for this corps
    scores = db.query(Score).filter(Score.corps_id == corps_id).all()

    # Group scores by rep
    rep_scores: dict[str, list] = {}
    for s in scores:
        if s.rep_id:
            rep_scores.setdefault(s.rep_id, []).append(s)

    tapes = []
    for rep_id, rep_score_list in rep_scores.items():
        rep = db.get(Rep, rep_id)
        segment = db.get(Segment, rep.segment_id) if rep else None

        # Build caption breakdown
        captions = {}
        for s in rep_score_list:
            jt = s.judge_type.value
            captions.setdefault(jt, []).append({
                "value": s.value,
                "box": s.box,
                "feedback": s.feedback,
            })

        # Compute composite
        try:
            composite = compute_composite(db, corps_id=corps_id, rep_id=rep_id)
            composite_data = {
                "final_score": composite.final_score,
                "needs_rework": composite.needs_rework,
                "needs_escalation": composite.needs_escalation,
            }
        except Exception:
            composite_data = {"final_score": 0, "needs_rework": False, "needs_escalation": False}

        tapes.append({
            "rep_id": rep_id,
            "segment_id": rep.segment_id if rep else None,
            "segment_title": segment.title if segment else None,
            "segment_type": segment.type.value if segment else None,
            "rep_status": rep.status.value if rep else "unknown",
            "captions": captions,
            "composite": composite_data,
            "score_count": len(rep_score_list),
        })

    # Sort by rep_id for deterministic output
    tapes.sort(key=lambda t: t["rep_id"])
    return tapes


@router.get("/api/judging/corps/{corps_id}/tapes/{rep_id}")
def api_get_judge_tape(corps_id: str, rep_id: str, db: Session = Depends(_get_db)):
    """Get detailed judge tape for a specific rep."""
    from backend.services.improvement import run_critique

    try:
        critique = run_critique(db, rep_id, corps_id)
    except Exception as e:
        raise HTTPException(400, str(e))

    return {
        "rep_id": critique.rep_id,
        "overall_assessment": critique.overall_assessment,
        "needs_rework": critique.needs_rework,
        "feedbacks": [
            {
                "judge_type": f.judge_type.value,
                "score_value": f.score_value,
                "box": f.box,
                "feedback": f.feedback,
                "strengths": f.strengths,
                "weaknesses": f.weaknesses,
                "action_items": f.action_items,
            }
            for f in critique.feedbacks
        ],
    }


@router.get("/api/judging/corps/{corps_id}/actions")
def api_get_critique_actions(corps_id: str, db: Session = Depends(_get_db)):
    """Extract actionable notes from all critiques and route to caption heads.

    Scans all scored reps, extracts weaknesses + action items from each judge type,
    and maps them to the responsible staff role.
    """
    from backend.models.score import Score
    from backend.services.improvement import run_critique

    scores = db.query(Score).filter(Score.corps_id == corps_id).all()
    rep_ids = list({s.rep_id for s in scores if s.rep_id})

    routed_actions: list[dict] = []

    for rep_id in rep_ids:
        try:
            critique = run_critique(db, rep_id, corps_id)
        except Exception:
            continue

        for fb in critique.feedbacks:
            if not fb.action_items and not fb.weaknesses:
                continue

            jt = fb.judge_type.value
            target_role = CAPTION_TO_ROLE.get(jt, "program_coordinator")

            routed_actions.append({
                "rep_id": rep_id,
                "judge_type": jt,
                "target_role": target_role,
                "score": fb.score_value,
                "weaknesses": fb.weaknesses,
                "action_items": fb.action_items,
                "strengths": fb.strengths,
            })

    # Group by target_role
    by_role: dict[str, list] = {}
    for action in routed_actions:
        by_role.setdefault(action["target_role"], []).append(action)

    return {
        "total_actions": len(routed_actions),
        "by_role": by_role,
        "actions": routed_actions,
    }


@router.get("/api/judging/corps/{corps_id}/tapes/{rep_id}/export")
def api_export_judge_tape(corps_id: str, rep_id: str, db: Session = Depends(_get_db)):
    """Export a consolidated markdown artifact for a judge tape."""
    from backend.models.rep import Rep
    from backend.models.segment import Segment
    from backend.services.improvement import run_critique
    from backend.services.scoring_service import compute_composite

    rep = db.get(Rep, rep_id)
    if not rep:
        raise HTTPException(404, "Rep not found")

    segment = db.get(Segment, rep.segment_id) if rep else None

    try:
        critique = run_critique(db, rep_id, corps_id)
    except Exception as e:
        raise HTTPException(400, str(e))

    try:
        composite = compute_composite(db, corps_id=corps_id, rep_id=rep_id)
    except Exception:
        composite = None

    now = datetime.now(timezone.utc).isoformat()

    lines = [
        f"# Judge Tape — {segment.title if segment else rep_id}",
        "",
        f"**Corps:** {corps_id}  ",
        f"**Rep:** {rep_id}  ",
        f"**Segment:** {segment.title if segment else 'N/A'} ({segment.type.value if segment else 'N/A'})  ",
        f"**Status:** {rep.status.value}  ",
        f"**Generated:** {now}  ",
        "",
    ]

    if composite:
        lines.extend([
            f"## Composite Score: {composite.final_score}",
            "",
            f"- Raw Total: {composite.raw_total}",
            f"- Penalties: {composite.penalties_total}",
            f"- Needs Rework: {'Yes' if composite.needs_rework else 'No'}",
            f"- Needs Escalation: {'Yes' if composite.needs_escalation else 'No'}",
            "",
        ])

    lines.extend([
        f"## Overall Assessment",
        "",
        critique.overall_assessment or "No assessment available.",
        "",
        "## Caption Scores",
        "",
    ])

    for fb in critique.feedbacks:
        lines.extend([
            f"### {fb.judge_type.value.replace('_', ' ').title()}",
            "",
            f"**Score:** {fb.score_value} (Box {fb.box})  ",
            "",
        ])
        if fb.feedback:
            lines.append(f"> {fb.feedback}")
            lines.append("")
        if fb.strengths:
            lines.append("**Strengths:**")
            for s in fb.strengths:
                lines.append(f"- {s}")
            lines.append("")
        if fb.weaknesses:
            lines.append("**Weaknesses:**")
            for w in fb.weaknesses:
                lines.append(f"- {w}")
            lines.append("")
        if fb.action_items:
            lines.append("**Action Items:**")
            for a in fb.action_items:
                lines.append(f"- [ ] {a}")
            lines.append("")

    return {"markdown": "\n".join(lines), "rep_id": rep_id, "corps_id": corps_id}
