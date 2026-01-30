"""Scoring service — judge invocation, composite calculation, score-driven routing."""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.penalty import Penalty, PenaltyType
from backend.models.score import JudgeType, Score


class InvalidScore(Exception):
    pass


# Caption-to-judge-type mapping
CAPTION_JUDGE_MAP = {
    "brass": JudgeType.BRASS,
    "percussion": JudgeType.PERCUSSION,
    "guard": JudgeType.GUARD,
    "visual": JudgeType.VISUAL,
}

# Default weights for composite score calculation
DEFAULT_WEIGHTS: dict[JudgeType, float] = {
    JudgeType.BRASS: 0.20,
    JudgeType.PERCUSSION: 0.20,
    JudgeType.GUARD: 0.20,
    JudgeType.VISUAL: 0.15,
    JudgeType.GENERAL_EFFECT: 0.25,
}

# Thresholds for score-driven routing
REWORK_THRESHOLD = 60.0  # Below this: automatic rework (another rep)
ESCALATION_THRESHOLD = 40.0  # Below this: escalate to ED/user


@dataclass
class CompositeScore:
    """Weighted composite score with penalty deductions."""

    caption_scores: dict[JudgeType, float]
    raw_total: float
    penalties_total: float
    final_score: float
    needs_rework: bool
    needs_escalation: bool


def record_score(
    db: Session,
    corps_id: str,
    judge_type: JudgeType,
    value: float,
    box: int,
    rep_id: Optional[str] = None,
    coordinate_id: Optional[str] = None,
    feedback: Optional[str] = None,
) -> Score:
    if value < 0 or value > 100:
        raise InvalidScore(f"Score value must be 0-100, got {value}")
    if box < 1 or box > 5:
        raise InvalidScore(f"Box must be 1-5, got {box}")
    if rep_id is None and coordinate_id is None:
        raise InvalidScore("Score must reference a rep or coordinate")

    score = Score(
        corps_id=corps_id,
        judge_type=judge_type,
        value=value,
        box=box,
        rep_id=rep_id,
        coordinate_id=coordinate_id,
        feedback=feedback,
    )
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


def record_penalty(
    db: Session,
    corps_id: str,
    type: PenaltyType,
    amount: float,
    reason: str,
    rep_id: Optional[str] = None,
    coordinate_id: Optional[str] = None,
    issued_by: Optional[str] = None,
) -> Penalty:
    if amount <= 0:
        raise InvalidScore(f"Penalty amount must be positive, got {amount}")

    penalty = Penalty(
        corps_id=corps_id,
        type=type,
        amount=amount,
        reason=reason,
        rep_id=rep_id,
        coordinate_id=coordinate_id,
        issued_by=issued_by,
    )
    db.add(penalty)
    db.commit()
    db.refresh(penalty)
    return penalty


def get_scores_for_rep(db: Session, rep_id: str) -> list[Score]:
    return db.query(Score).filter(Score.rep_id == rep_id).all()


def get_scores_for_coordinate(db: Session, coordinate_id: str) -> list[Score]:
    return db.query(Score).filter(Score.coordinate_id == coordinate_id).all()


def get_penalties_for_corps(db: Session, corps_id: str) -> list[Penalty]:
    return db.query(Penalty).filter(Penalty.corps_id == corps_id).all()


def compute_composite(
    db: Session,
    corps_id: str,
    rep_id: Optional[str] = None,
    coordinate_id: Optional[str] = None,
    weights: Optional[dict[JudgeType, float]] = None,
) -> CompositeScore:
    """Compute weighted composite score with penalty deductions.

    Uses the latest score per judge type for the given rep or coordinate.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    # Get scores
    if rep_id:
        scores = get_scores_for_rep(db, rep_id)
    elif coordinate_id:
        scores = get_scores_for_coordinate(db, coordinate_id)
    else:
        scores = []

    # Take latest score per judge type
    latest: dict[JudgeType, Score] = {}
    for s in scores:
        if s.judge_type not in latest or s.created_at > latest[s.judge_type].created_at:
            latest[s.judge_type] = s

    caption_scores: dict[JudgeType, float] = {}
    raw_total = 0.0
    total_weight = 0.0

    for jtype, score in latest.items():
        caption_scores[jtype] = score.value
        w = weights.get(jtype, 0.0)
        raw_total += score.value * w
        total_weight += w

    # Normalize if not all captions scored
    if total_weight > 0 and total_weight < 1.0:
        raw_total = raw_total / total_weight

    # Get penalties
    penalty_query = db.query(Penalty).filter(Penalty.corps_id == corps_id)
    if rep_id:
        penalty_query = penalty_query.filter(Penalty.rep_id == rep_id)
    elif coordinate_id:
        penalty_query = penalty_query.filter(Penalty.coordinate_id == coordinate_id)
    penalties = penalty_query.all()
    penalties_total = sum(p.amount for p in penalties)

    final_score = max(0.0, raw_total - penalties_total)

    return CompositeScore(
        caption_scores=caption_scores,
        raw_total=raw_total,
        penalties_total=penalties_total,
        final_score=final_score,
        needs_rework=final_score < REWORK_THRESHOLD,
        needs_escalation=final_score < ESCALATION_THRESHOLD,
    )


def check_timing(
    db: Session,
    corps_id: str,
    rep_id: Optional[str] = None,
    coordinate_id: Optional[str] = None,
    budget_spent: float = 0.0,
    budget_limit: float = 0.0,
    deadline_exceeded: bool = False,
) -> Optional[Penalty]:
    """Timing official — checks budget and deadline, issues penalties if violated."""
    if deadline_exceeded:
        return record_penalty(
            db,
            corps_id=corps_id,
            type=PenaltyType.TIMING,
            amount=5.0,
            reason="Deadline exceeded",
            rep_id=rep_id,
            coordinate_id=coordinate_id,
            issued_by="timing_official",
        )

    if budget_limit > 0 and budget_spent > budget_limit:
        overage_pct = (budget_spent - budget_limit) / budget_limit * 100
        return record_penalty(
            db,
            corps_id=corps_id,
            type=PenaltyType.BUDGET,
            amount=min(overage_pct * 0.1, 10.0),  # Cap at 10 points
            reason=f"Budget exceeded by {overage_pct:.1f}%",
            rep_id=rep_id,
            coordinate_id=coordinate_id,
            issued_by="timing_official",
        )

    return None
