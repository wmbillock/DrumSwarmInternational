"""Scoring engine — pure computation layer for standings and rankings.

Takes CompositeScore inputs from scoring_service, applies difficulty coefficients,
ranks corps, and produces Standings.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from backend.models.score import JudgeType
from backend.services.scoring_service import CompositeScore


@dataclass
class CorpsResult:
    corps_id: str
    caption_scores: dict[JudgeType, float]
    penalties_total: float
    difficulty_coefficient: float
    raw_score: float        # weighted composite before difficulty
    final_score: float      # raw_score * difficulty_coefficient - penalties
    rank: int


@dataclass
class Standings:
    season_id: str
    results: list[CorpsResult]  # sorted by rank
    generated_at: str           # ISO timestamp


def score_corps(composite: CompositeScore, difficulty: float = 1.0) -> float:
    """Apply difficulty coefficient to a composite score.

    final = raw_total * difficulty - penalties
    """
    return max(0.0, composite.raw_total * difficulty - composite.penalties_total)


def rank_corps(corps_scores: dict[str, float]) -> list[tuple[str, int]]:
    """Sort corps by score descending, assign ranks (1-indexed, ties share rank)."""
    sorted_items = sorted(corps_scores.items(), key=lambda x: x[1], reverse=True)
    result: list[tuple[str, int]] = []
    for i, (corps_id, score) in enumerate(sorted_items):
        if i == 0:
            result.append((corps_id, 1))
        else:
            prev_corps, prev_rank = result[-1]
            prev_score = corps_scores[prev_corps]
            if score == prev_score:
                result.append((corps_id, prev_rank))
            else:
                result.append((corps_id, i + 1))
    return result


def compute_standings(
    season_id: str,
    scorecard_config: dict[JudgeType, float],
    corps_composites: dict[str, CompositeScore],
    difficulty_coefficients: dict[str, float] | None = None,
) -> Standings:
    """Aggregate scores, rank, return Standings."""
    if difficulty_coefficients is None:
        difficulty_coefficients = {}

    # Compute final scores
    final_scores: dict[str, float] = {}
    for corps_id, composite in corps_composites.items():
        diff = difficulty_coefficients.get(corps_id, 1.0)
        final_scores[corps_id] = score_corps(composite, diff)

    # Rank
    ranked = rank_corps(final_scores)
    rank_map = dict(ranked)

    # Build results
    results: list[CorpsResult] = []
    for corps_id, composite in corps_composites.items():
        diff = difficulty_coefficients.get(corps_id, 1.0)
        results.append(CorpsResult(
            corps_id=corps_id,
            caption_scores=dict(composite.caption_scores),
            penalties_total=composite.penalties_total,
            difficulty_coefficient=diff,
            raw_score=composite.raw_total,
            final_score=final_scores[corps_id],
            rank=rank_map[corps_id],
        ))

    results.sort(key=lambda r: r.rank)

    return Standings(
        season_id=season_id,
        results=results,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
