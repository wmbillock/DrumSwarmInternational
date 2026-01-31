"""Improvement lifecycle engines:
- Basics: per-caption self-improvement cycle
- Critique: post-performance judge-to-staff feedback
- Banquet: end-of-project retrospective
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.agent_definition import AgentDefinition
from backend.models.segment import Segment, SegmentStatus
from backend.models.rep import Rep, RepStatus
from backend.models.score import JudgeType, Score
from backend.services.scoring_service import get_scores_for_rep, compute_composite


@dataclass
class BasicsResult:
    """Result of a basics (self-improvement) cycle for a caption."""
    caption: str
    definitions_reviewed: int = 0
    improvements_suggested: int = 0
    suggestions: list[str] = field(default_factory=list)


@dataclass
class CritiqueFeedback:
    """Structured feedback from a judge to instructional staff."""
    judge_type: JudgeType
    score_value: float
    box: int
    feedback: str
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)


@dataclass
class CritiqueResult:
    """Result of a critique session after a performance."""
    rep_id: str
    feedbacks: list[CritiqueFeedback] = field(default_factory=list)
    overall_assessment: str = ""
    needs_rework: bool = False


@dataclass
class BanquetReport:
    """End-of-project retrospective report."""
    corps_id: str
    total_reps: int = 0
    completed_reps: int = 0
    failed_reps: int = 0
    average_score: float = 0.0
    top_caption: Optional[str] = None
    what_worked: list[str] = field(default_factory=list)
    what_failed: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    generated_at: Optional[datetime] = None


def run_basics(
    db: Session, corps_id: str, caption: str
) -> BasicsResult:
    """Run a basics (self-improvement) cycle for a caption.

    Reviews agent definitions assigned to this caption and suggests
    improvements based on recent performance data.
    """
    result = BasicsResult(caption=caption)

    # Find definitions for this caption
    definitions = (
        db.query(AgentDefinition)
        .filter(AgentDefinition.corps_id == corps_id)
        .filter(AgentDefinition.role.contains(caption))
        .all()
    )
    result.definitions_reviewed = len(definitions)

    # Find recent failed reps to learn from
    failed_reps = (
        db.query(Rep)
        .join(Segment)
        .filter(Segment.caption == caption)
        .filter(Rep.status == RepStatus.FAILED)
        .all()
    )

    if failed_reps:
        result.improvements_suggested += 1
        result.suggestions.append(
            f"Review {len(failed_reps)} failed reps for {caption} to identify patterns"
        )

    # Check for low-scoring completed reps
    completed_reps = (
        db.query(Rep)
        .join(Segment)
        .filter(Segment.caption == caption)
        .filter(Rep.status == RepStatus.COMPLETED)
        .all()
    )

    for rep in completed_reps:
        scores = get_scores_for_rep(db, rep.id)
        low_scores = [s for s in scores if s.value < 60]
        if low_scores:
            result.improvements_suggested += 1
            result.suggestions.append(
                f"Rep {rep.id[:8]} scored below 60 — review technique"
            )

    return result


def run_critique(db: Session, rep_id: str, corps_id: str) -> CritiqueResult:
    """Run a critique session for a completed rep.

    Collects judge scores and generates structured feedback for staff.
    """
    result = CritiqueResult(rep_id=rep_id)
    scores = get_scores_for_rep(db, rep_id)

    for score in scores:
        feedback = CritiqueFeedback(
            judge_type=score.judge_type,
            score_value=score.value,
            box=score.box,
            feedback=score.feedback or "",
        )

        if score.value >= 80:
            feedback.strengths.append("Strong execution")
        if score.value < 60:
            feedback.weaknesses.append("Needs significant improvement")
            feedback.action_items.append("Schedule additional reps")

        result.feedbacks.append(feedback)

    composite = compute_composite(db, corps_id=corps_id, rep_id=rep_id)
    result.needs_rework = composite.needs_rework

    if result.feedbacks:
        avg = sum(f.score_value for f in result.feedbacks) / len(result.feedbacks)
        if avg >= 80:
            result.overall_assessment = "Strong performance"
        elif avg >= 60:
            result.overall_assessment = "Acceptable with room for improvement"
        else:
            result.overall_assessment = "Below standards — rework required"

    return result


def run_banquet(db: Session, corps_id: str) -> BanquetReport:
    """Generate an end-of-project retrospective report.

    Blameless post-mortem: what worked, what failed, improvements.
    """
    report = BanquetReport(
        corps_id=corps_id,
        generated_at=datetime.now(timezone.utc),
    )

    # Get all reps for this corps (via segments with matching definitions)
    all_definitions = (
        db.query(AgentDefinition)
        .filter(AgentDefinition.corps_id == corps_id)
        .all()
    )

    # Count all reps in the system (simplified — in production would filter by corps)
    all_reps = db.query(Rep).all()
    report.total_reps = len(all_reps)
    report.completed_reps = sum(1 for r in all_reps if r.status == RepStatus.COMPLETED)
    report.failed_reps = sum(1 for r in all_reps if r.status == RepStatus.FAILED)

    # Compute average score from all scored reps
    all_scores = db.query(Score).all()
    if all_scores:
        report.average_score = sum(s.value for s in all_scores) / len(all_scores)

        # Find top caption by average score
        caption_scores: dict[str, list[float]] = {}
        for s in all_scores:
            jtype = s.judge_type.value
            caption_scores.setdefault(jtype, []).append(s.value)

        if caption_scores:
            report.top_caption = max(
                caption_scores, key=lambda k: sum(caption_scores[k]) / len(caption_scores[k])
            )

    # Generate insights
    if report.total_reps > 0:
        completion_rate = report.completed_reps / report.total_reps
        if completion_rate >= 0.8:
            report.what_worked.append(f"High completion rate: {completion_rate:.0%}")
        if report.failed_reps > 0:
            report.what_failed.append(
                f"{report.failed_reps} reps failed out of {report.total_reps}"
            )
        if completion_rate < 0.5:
            report.improvements.append("Improve rep success rate — consider definition refinement")

    if report.average_score > 0:
        if report.average_score >= 80:
            report.what_worked.append(f"Strong average score: {report.average_score:.1f}")
        elif report.average_score < 60:
            report.improvements.append("Average score below 60 — review training approach")

    return report
