"""Auto-critique service — automatic post-competition critique for bottom-75% corps."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.services.critique_service import start_critique, complete_critique, JUDGE_TO_STAFF
from backend.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

# Only competition judge types — exclude ad-hoc user types
JUDGE_TYPES = [k for k in JUDGE_TO_STAFF.keys() if k not in ("user_feedback", "user")]


def run_auto_critique(
    db: Session,
    competition_id: str,
    standings_results: list[dict],
    llm_client: Optional[LLMClient] = None,
) -> dict:
    """Auto-critique bottom 75% corps after competition.

    For each corps below the 25th percentile rank:
      - For each of the judge types:
        - start_critique() with is_automated=True
        - complete_critique() immediately (extract action items)
    Returns summary dict: {corps_id: {judge_type: action_items}}
    """
    if not standings_results:
        return {}

    total = len(standings_results)
    if total <= 1:
        return {}

    # Top 25% cutoff: if 12 corps, top 3 are exempt. If <=3, exempt rank 1 only.
    if total <= 3:
        cutoff_rank = 1
    else:
        cutoff_rank = max(1, total // 4)

    # Corps to critique: all except top cutoff_rank
    corps_to_critique = [
        r["corps_id"] for r in standings_results
        if r.get("rank", 0) > cutoff_rank
    ]

    if not corps_to_critique:
        return {}

    summary: dict[str, dict[str, str]] = {}

    for corps_id in corps_to_critique:
        summary[corps_id] = {}
        for judge_type in JUDGE_TYPES:
            try:
                session = start_critique(
                    db, competition_id, corps_id, judge_type,
                    llm_client=llm_client, is_automated=True,
                )
                completed = complete_critique(db, session.id, llm_client=llm_client)
                summary[corps_id][judge_type] = completed.action_items or ""
                logger.info(
                    "Auto-critique %s/%s/%s complete",
                    competition_id, corps_id, judge_type,
                )
            except Exception as e:
                logger.warning(
                    "Auto-critique failed for %s/%s: %s",
                    corps_id, judge_type, e,
                )
                summary[corps_id][judge_type] = f"Error: {e}"

    return summary
