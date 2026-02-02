"""Shared scoring utilities — deterministic stub scores and score computation.

Consolidates the repeated _stub_caption_scores() pattern used across
router.py, tour_demo.py, season.py, and judge_service.py.
"""

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.models.score import JudgeType


def stub_caption_scores(corps_id: str, show_slug: str, seed_offset: int = 0) -> dict:
    """Generate deterministic scores per caption, seeded from corps_id + show_slug.

    Returns dict mapping JudgeType -> score (60-89 range).
    This is a fallback for when real LLM judging isn't available.
    """
    from backend.models.score import JudgeType

    scores = {}
    for jtype in [JudgeType.BRASS, JudgeType.PERCUSSION, JudgeType.GUARD,
                  JudgeType.VISUAL, JudgeType.GENERAL_EFFECT]:
        seed = hashlib.sha256(
            f"{corps_id}:{show_slug}:{jtype.value}:{seed_offset}".encode()
        ).hexdigest()
        scores[jtype] = (int(seed[:8], 16) % 30) + 60
    return scores


def compute_total_score(caption_scores: dict) -> float:
    """Sum caption scores into a total. Max possible = 100 (5 captions x 20 each)."""
    return sum(caption_scores.values())
