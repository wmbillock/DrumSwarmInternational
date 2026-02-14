"""Post-mortem generation for completed seasons.

When a season completes (winner declared), generates a markdown post-mortem
document for each participating corps summarizing their tour performance.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.corps import Corps
from backend.services.yaml_util import safe_load_yaml_dict

logger = logging.getLogger(__name__)


def _resolve_corps_name(db: Optional[Session], corps_id: str) -> str:
    """Resolve a corps ID to its display name."""
    if db:
        corps = db.query(Corps).filter(Corps.id == corps_id).first()
        if corps:
            return corps.name
    # Fallback: prettify the ID
    return corps_id.replace("-", " ").title()


def _ordinal(n: int) -> str:
    """Return ordinal string for an integer (1st, 2nd, 3rd, etc.)."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _slug_to_title(slug: str) -> str:
    """Convert a show slug to a readable title."""
    return slug.replace("-", " ").title()[:60]


def generate_corps_post_mortem(
    season_data: dict,
    corps_id: str,
    db: Optional[Session] = None,
) -> str:
    """Generate a markdown post-mortem for a single corps in a season.

    Args:
        season_data: Parsed season.yaml contents
        corps_id: The corps to generate the post-mortem for
        db: Optional DB session for resolving corps names

    Returns:
        Markdown string with the post-mortem content
    """
    season_id = season_data.get("season_id", "unknown")
    season_name = season_data.get("metadata", {}).get("name", season_id)
    corps_name = _resolve_corps_name(db, corps_id)
    winner_id = season_data.get("metadata", {}).get("winner")
    schedule = season_data.get("schedule", [])

    # Gather this corps' results across all rounds
    rounds_participated = []
    all_scores = []
    all_placements = []
    caption_totals: dict[str, list[float]] = {}
    wins = 0

    for entry in schedule:
        corps_ids = entry.get("corps_ids", [])
        if corps_id not in corps_ids:
            continue

        round_num = entry.get("round", 0)
        show_slug = entry.get("show_slug", "")
        status = entry.get("status", "pending")
        standings = entry.get("standings", [])

        round_info = {
            "round": round_num,
            "show_slug": show_slug,
            "show_title": _slug_to_title(show_slug),
            "status": status,
            "placement": None,
            "total_corps": len(corps_ids),
            "final_score": None,
            "caption_scores": {},
        }

        for s in standings:
            if s.get("corps_id") == corps_id:
                round_info["placement"] = s.get("rank")
                round_info["final_score"] = s.get("final_score")
                round_info["caption_scores"] = s.get("caption_scores", {})
                if round_info["final_score"] is not None:
                    all_scores.append(round_info["final_score"])
                if round_info["placement"] is not None:
                    all_placements.append(round_info["placement"])
                    if round_info["placement"] == 1:
                        wins += 1
                for cap, val in round_info["caption_scores"].items():
                    caption_totals.setdefault(cap, []).append(val)
                break

        rounds_participated.append(round_info)

    # Compute aggregates
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
    avg_placement = sum(all_placements) / len(all_placements) if all_placements else 0.0
    best_placement = min(all_placements) if all_placements else None
    worst_placement = max(all_placements) if all_placements else None
    best_score = max(all_scores) if all_scores else None
    worst_score = min(all_scores) if all_scores else None

    is_winner = (winner_id == corps_id) if winner_id else False

    # Build caption averages
    caption_avgs: dict[str, float] = {}
    for cap, vals in caption_totals.items():
        caption_avgs[cap] = sum(vals) / len(vals) if vals else 0.0

    best_caption = max(caption_avgs, key=caption_avgs.get) if caption_avgs else None
    worst_caption = min(caption_avgs, key=caption_avgs.get) if caption_avgs else None

    # Build the document
    lines = []
    lines.append(f"# Post-Mortem: {corps_name}")
    lines.append(f"**Season:** {season_name} (`{season_id}`)")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    if is_winner:
        lines.append("> **SEASON CHAMPION**")
        lines.append("")

    # Summary stats
    lines.append("## Season Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Rounds Competed | {len(rounds_participated)} |")
    lines.append(f"| Rounds Scored | {len(all_scores)} |")
    lines.append(f"| Round Wins | {wins} |")
    if avg_score > 0:
        lines.append(f"| Average Score | {avg_score:.2f} |")
    if best_score is not None:
        lines.append(f"| Best Score | {best_score:.2f} |")
    if worst_score is not None:
        lines.append(f"| Worst Score | {worst_score:.2f} |")
    if avg_placement > 0:
        lines.append(f"| Average Placement | {avg_placement:.1f} |")
    if best_placement is not None:
        lines.append(f"| Best Placement | {_ordinal(best_placement)} |")
    lines.append("")

    # Caption breakdown
    if caption_avgs:
        lines.append("## Caption Performance")
        lines.append("")
        lines.append("| Caption | Avg Score |")
        lines.append("|---------|-----------|")
        for cap in sorted(caption_avgs, key=caption_avgs.get, reverse=True):
            marker = ""
            if cap == best_caption:
                marker = " (best)"
            elif cap == worst_caption and len(caption_avgs) > 1:
                marker = " (weakest)"
            lines.append(f"| {cap.replace('_', ' ').title()} | {caption_avgs[cap]:.1f}{marker} |")
        lines.append("")

    # Round-by-round
    lines.append("## Round-by-Round Results")
    lines.append("")
    lines.append("| Round | Show | Placement | Score | Field Size |")
    lines.append("|-------|------|-----------|-------|------------|")
    for r in rounds_participated:
        placement_str = _ordinal(r["placement"]) if r["placement"] else "N/A"
        score_str = f"{r['final_score']:.2f}" if r["final_score"] is not None else "N/S"
        lines.append(
            f"| {r['round']} | {r['show_title'][:40]} | {placement_str} | {score_str} | {r['total_corps']} |"
        )
    lines.append("")

    # Analysis
    lines.append("## Analysis")
    lines.append("")
    if is_winner:
        lines.append(f"**{corps_name}** won the {season_name} season")
        if wins > 1:
            lines.append(f"with {wins} round victories across {len(rounds_participated)} competitions.")
        elif wins == 1:
            lines.append(f"with 1 round victory across {len(rounds_participated)} competitions.")
        else:
            lines.append(f"despite not winning any individual rounds, through consistent scoring.")
    else:
        if best_placement and best_placement <= 3:
            lines.append(
                f"**{corps_name}** showed strong competitive ability, achieving "
                f"a best placement of {_ordinal(best_placement)}."
            )
        elif len(all_scores) > 0:
            lines.append(
                f"**{corps_name}** competed in {len(rounds_participated)} rounds "
                f"with an average score of {avg_score:.1f}."
            )
        else:
            lines.append(
                f"**{corps_name}** participated in {len(rounds_participated)} rounds "
                f"during this season."
            )

    lines.append("")

    if best_caption and worst_caption and best_caption != worst_caption:
        lines.append(
            f"Strongest caption: **{best_caption.replace('_', ' ').title()}** "
            f"(avg {caption_avgs[best_caption]:.1f}). "
            f"Area for growth: **{worst_caption.replace('_', ' ').title()}** "
            f"(avg {caption_avgs[worst_caption]:.1f})."
        )
        lines.append("")

    # Score trend
    if len(all_scores) >= 3:
        first_half = all_scores[: len(all_scores) // 2]
        second_half = all_scores[len(all_scores) // 2 :]
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        delta = second_avg - first_avg
        if delta > 2:
            lines.append(
                f"Score trend: **Improving** (+{delta:.1f} average from "
                f"first half to second half of season)."
            )
        elif delta < -2:
            lines.append(
                f"Score trend: **Declining** ({delta:.1f} average from "
                f"first half to second half of season)."
            )
        else:
            lines.append("Score trend: **Stable** throughout the season.")
        lines.append("")

    return "\n".join(lines)


def generate_season_post_mortems(
    root: Path,
    season_id: str,
    db: Optional[Session] = None,
) -> dict[str, str]:
    """Generate post-mortem documents for all corps in a completed season.

    Args:
        root: Project root directory
        season_id: Season identifier
        db: Optional DB session for resolving corps names

    Returns:
        Dict mapping corps_id -> markdown content
    """
    season_dir = root / "seasons" / season_id
    season_yaml = season_dir / "season.yaml"
    if not season_yaml.is_file():
        logger.warning(f"Season YAML not found: {season_yaml}")
        return {}

    season_data = safe_load_yaml_dict(season_yaml.read_text(encoding="utf-8"))

    # Collect all corps that participated in at least one round
    all_corps_ids: set[str] = set()
    for entry in season_data.get("schedule", []):
        for cid in entry.get("corps_ids", []):
            all_corps_ids.add(cid)

    if not all_corps_ids:
        logger.info(f"No participating corps found in season {season_id}")
        return {}

    # Generate post-mortems
    results = {}
    post_mortem_dir = season_dir / "post_mortems"
    post_mortem_dir.mkdir(exist_ok=True)

    for corps_id in sorted(all_corps_ids):
        try:
            content = generate_corps_post_mortem(season_data, corps_id, db=db)
            # Write to disk
            safe_filename = corps_id.replace("/", "_").replace("\\", "_")
            output_path = post_mortem_dir / f"{safe_filename}.md"
            output_path.write_text(content, encoding="utf-8")
            results[corps_id] = content
            # Record artifact if DB available
            if db:
                try:
                    from backend.services.artifact_tracker import record_artifact
                    from backend.models.artifact import ArtifactType
                    rel_path = str(output_path.relative_to(root)).replace("\\", "/")
                    record_artifact(
                        db, rel_path, ArtifactType.POST_MORTEM,
                        label=f"Post-mortem for {corps_id}",
                        corps_id=corps_id,
                        season_id=season_id,
                    )
                except Exception:
                    pass
            logger.info(f"Generated post-mortem for {corps_id} in season {season_id}")
        except Exception as e:
            logger.error(f"Failed to generate post-mortem for {corps_id}: {e}")

    return results


def get_corps_post_mortem(
    root: Path,
    season_id: str,
    corps_id: str,
) -> Optional[str]:
    """Retrieve a previously generated post-mortem document.

    Returns None if no post-mortem exists for this corps/season combo.
    """
    safe_filename = corps_id.replace("/", "_").replace("\\", "_")
    path = root / "seasons" / season_id / "post_mortems" / f"{safe_filename}.md"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return None


def list_corps_post_mortems(
    root: Path,
    corps_id: str,
) -> list[dict]:
    """Find all post-mortem documents for a corps across all seasons.

    Returns a list of {season_id, path, generated_at} dicts.
    """
    seasons_dir = root / "seasons"
    if not seasons_dir.exists():
        return []

    results = []
    for season_dir in sorted(seasons_dir.iterdir()):
        if not season_dir.is_dir():
            continue
        safe_filename = corps_id.replace("/", "_").replace("\\", "_")
        pm_path = season_dir / "post_mortems" / f"{safe_filename}.md"
        if pm_path.is_file():
            stat = pm_path.stat()
            results.append({
                "season_id": season_dir.name,
                "generated_at": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
            })

    return results
