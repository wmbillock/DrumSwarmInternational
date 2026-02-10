"""Show Draft Service — automated show assignment by score ranking and affinity.

Corps pick shows in draft order (best score first). Affinity scoring uses
caption_affinity and founding_definition to match corps to show themes.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Keywords associated with each show style / caption area
CAPTION_KEYWORDS = {
    "brass": ["brass", "horn", "trumpet", "mellophone", "baritone", "tuba", "fanfare", "bold", "power"],
    "percussion": ["percussion", "drum", "battery", "pit", "rhythm", "groove", "mallet", "timpani"],
    "guard": ["guard", "flag", "rifle", "sabre", "dance", "visual", "color", "movement", "choreography"],
    "visual": ["visual", "design", "form", "drill", "spatial", "geometric", "artistic", "aesthetic"],
    "general_effect": ["effect", "emotional", "narrative", "story", "theme", "journey", "impact", "drama"],
}


def compute_draft_order(db: Session, corps_ids: list[str]) -> list[dict]:
    """Rank corps by their best Score.value, defaulting to 50.0 for unscored.

    Returns list of {corps_id, best_score, rank} sorted by score descending.
    """
    from backend.models.score import Score
    from sqlalchemy import func

    # Get best score per corps
    best_scores: dict[str, float] = {}
    if corps_ids:
        rows = (
            db.query(Score.corps_id, func.max(Score.value))
            .filter(Score.corps_id.in_(corps_ids))
            .group_by(Score.corps_id)
            .all()
        )
        for corps_id, max_val in rows:
            best_scores[corps_id] = float(max_val) if max_val is not None else 50.0

    # Build ordered list
    order = []
    for cid in corps_ids:
        order.append({
            "corps_id": cid,
            "best_score": best_scores.get(cid, 50.0),
        })
    order.sort(key=lambda x: x["best_score"], reverse=True)
    for i, entry in enumerate(order):
        entry["rank"] = i + 1

    return order


def score_show_affinity(db: Session, corps_id: str, show_slug: str, show_summary: str = "") -> dict:
    """Score how well a corps matches a show based on keyword affinity.

    Uses Corps.caption_affinity (e.g. "brass") and Corps.founding_definition
    (JSON with philosophy, category, etc.) to compute a match score.

    Returns {score: float, reason: str, keywords_matched: list}.
    """
    from backend.models.corps import Corps

    corps = db.get(Corps, corps_id)
    if not corps:
        return {"score": 0.0, "reason": "Corps not found", "keywords_matched": []}

    # Build a search text from the show
    search_text = (show_slug.replace("-", " ") + " " + show_summary).lower()

    # Get corps profile
    affinity = (corps.caption_affinity or "").lower()
    founding_text = ""
    if corps.founding_definition:
        try:
            fd = json.loads(corps.founding_definition) if isinstance(corps.founding_definition, str) else corps.founding_definition
            founding_text = " ".join(str(v) for v in fd.values() if isinstance(v, str)).lower()
        except (json.JSONDecodeError, AttributeError):
            founding_text = str(corps.founding_definition).lower()

    corps_text = f"{affinity} {founding_text} {(corps.mascot or '').lower()}"

    # Score by keyword matching
    score = 0.0
    matched = []

    # Direct caption affinity match
    if affinity:
        keywords = CAPTION_KEYWORDS.get(affinity, [])
        for kw in keywords:
            if kw in search_text:
                score += 10.0
                matched.append(f"caption:{kw}")

    # Cross-match corps keywords against show text
    corps_words = set(corps_text.split())
    show_words = set(search_text.split())
    overlap = corps_words & show_words - {"the", "a", "an", "and", "or", "of", "in", "to", "for", "is"}
    score += len(overlap) * 5.0
    matched.extend(list(overlap)[:5])

    # Bonus for show slug matching corps name
    corps_name_words = set(corps.name.lower().split())
    slug_words = set(show_slug.replace("-", " ").lower().split())
    name_overlap = corps_name_words & slug_words - {"the", "a", "an"}
    if name_overlap:
        score += 15.0
        matched.extend([f"name:{w}" for w in name_overlap])

    reason = f"Matched {len(matched)} keywords" if matched else "No strong affinity detected"

    return {
        "score": round(score, 1),
        "reason": reason,
        "keywords_matched": matched,
    }


def _get_show_summary(root: Path, show_slug: str) -> str:
    """Load show summary from its workspace if available."""
    show_dir = root / "shows" / show_slug
    for fname in ["spec.md", "design_notes.md", "show_prompt.md"]:
        fpath = show_dir / fname
        if fpath.is_file():
            try:
                text = fpath.read_text(encoding="utf-8")
                return text[:500]  # First 500 chars for keyword matching
            except Exception:
                pass
    return ""


def run_show_draft(
    db: Session,
    season_dir: Path,
    show_slugs: list[str],
    corps_ids: list[str],
    corps_per_contest: int = 0,
    required_scores: int = 0,
) -> dict:
    """Run the show draft: corps pick shows balanced by affinity and capacity.

    Each corps needs `required_scores` appearances total. Each show slot holds
    at most `corps_per_contest` corps. Corps are assigned to their highest-
    affinity show that still has room, cycling through rounds until every corps
    has enough appearances.

    If corps_per_contest / required_scores are 0 they are read from the season
    config on disk.

    Returns {
        draft_order: [{corps_id, best_score, rank}],
        picks: [{pick, corps_id, corps_name, show_slug, affinity_score, reason}],
        assignments: {show_slug: [corps_id, ...]},
    }
    """
    import math
    from backend.models.corps import Corps

    if not show_slugs or not corps_ids:
        return {"draft_order": [], "picks": [], "assignments": {}}

    # Read config from season if not provided
    if corps_per_contest <= 0 or required_scores <= 0:
        from backend.services.season_persistence import load_season
        data = load_season(season_dir)
        cfg = data.get("config") or {}
        if corps_per_contest <= 0:
            corps_per_contest = int(cfg.get("corps_per_contest", max(2, len(corps_ids))))
        if required_scores <= 0:
            required_scores = int(cfg.get("required_scores", 1))
    corps_per_contest = max(2, min(corps_per_contest, len(corps_ids)))

    root = season_dir.parent
    draft_order = compute_draft_order(db, corps_ids)

    # Precompute show summaries and affinity scores
    show_summaries = {slug: _get_show_summary(root, slug) for slug in show_slugs}

    affinity_cache: dict[str, list[tuple[str, dict]]] = {}
    for entry in draft_order:
        cid = entry["corps_id"]
        affinities = []
        for slug in show_slugs:
            aff = score_show_affinity(db, cid, slug, show_summaries.get(slug, ""))
            affinities.append((slug, aff))
        affinities.sort(key=lambda x: x[1]["score"], reverse=True)
        affinity_cache[cid] = affinities

    # Calculate how many total round-slots we need
    # Each corps needs required_scores appearances, each round fits corps_per_contest
    total_appearances = len(corps_ids) * required_scores
    num_rounds = math.ceil(total_appearances / corps_per_contest)

    # Build round slots: each round is assigned a show via round-robin
    rounds: list[dict] = []
    for r in range(num_rounds):
        show_slug = show_slugs[r % len(show_slugs)]
        rounds.append({"show_slug": show_slug, "corps": [], "capacity": corps_per_contest})

    # Track remaining appearances needed per corps
    remaining = {cid: required_scores for cid in corps_ids}

    # Assign corps to rounds: draft order, prefer rounds with matching show affinity
    picks = []
    pick_num = 0

    # Iterate until everyone has enough appearances
    while any(r > 0 for r in remaining.values()):
        placed_any = False
        for entry in draft_order:
            cid = entry["corps_id"]
            if remaining[cid] <= 0:
                continue

            corps = db.get(Corps, cid)
            corps_name = corps.name if corps else f"Corps {cid[:8]}"

            # Get this corps' show preferences
            affinities = affinity_cache[cid]

            # Find the best round that has capacity and matches a preferred show
            best_round_idx = None
            best_aff = None
            for slug, aff in affinities:
                # Find rounds for this show that have capacity and don't already have this corps
                for ri, rd in enumerate(rounds):
                    if rd["show_slug"] == slug and len(rd["corps"]) < rd["capacity"] and cid not in rd["corps"]:
                        if best_round_idx is None or aff["score"] > best_aff["score"]:
                            best_round_idx = ri
                            best_aff = aff
                        break  # Take the first available round for this show

            if best_round_idx is not None:
                rounds[best_round_idx]["corps"].append(cid)
                remaining[cid] -= 1
                placed_any = True
                pick_num += 1
                picks.append({
                    "pick": pick_num,
                    "corps_id": cid,
                    "corps_name": corps_name,
                    "show_slug": rounds[best_round_idx]["show_slug"],
                    "round": best_round_idx + 1,
                    "affinity_score": best_aff["score"],
                    "reason": best_aff["reason"],
                })

        if not placed_any:
            # All remaining corps can't fit — add overflow rounds
            for cid, rem in remaining.items():
                while rem > 0:
                    show_slug = show_slugs[len(rounds) % len(show_slugs)]
                    rounds.append({"show_slug": show_slug, "corps": [cid], "capacity": corps_per_contest})
                    rem -= 1
                    remaining[cid] = rem
                    pick_num += 1
                    corps = db.get(Corps, cid)
                    corps_name = corps.name if corps else f"Corps {cid[:8]}"
                    picks.append({
                        "pick": pick_num,
                        "corps_id": cid,
                        "corps_name": corps_name,
                        "show_slug": show_slug,
                        "round": len(rounds),
                        "affinity_score": 0.0,
                        "reason": "Overflow placement",
                    })
            break

    # Build assignments: flatten round corps lists per show
    assignments: dict[str, list[str]] = {slug: [] for slug in show_slugs}
    for rd in rounds:
        slug = rd["show_slug"]
        for cid in rd["corps"]:
            if cid not in assignments[slug]:
                assignments[slug].append(cid)

    return {
        "draft_order": draft_order,
        "picks": picks,
        "assignments": assignments,
        "rounds": [
            {
                "round": i + 1,
                "show_slug": rd["show_slug"],
                "corps_ids": rd["corps"],
            }
            for i, rd in enumerate(rounds)
            if rd["corps"]  # skip empty rounds
        ],
    }
