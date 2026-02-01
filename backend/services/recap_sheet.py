"""Recap Sheet — DCI-style wide table of all corps scores for a competition."""

import csv
import io
from dataclasses import dataclass, field
from typing import Optional

from backend.models.score import JudgeType
from backend.services.scoring_service import DEFAULT_WEIGHTS


@dataclass
class RecapRow:
    """One row per corps with all caption rep/perf/tot scores, penalties, final, rank."""
    corps_id: str
    corps_name: str = ""
    rank: int = 0
    caption_scores: dict[str, dict[str, float]] = field(default_factory=dict)
    # caption_scores = {"brass": {"rep": 80, "perf": 85, "tot": 82.5}, ...}
    penalties_total: float = 0.0
    raw_total: float = 0.0
    final_score: float = 0.0


def generate_recap_sheet(
    season_id: str,
    show_slug: str,
    standings_data: Optional[dict] = None,
) -> list[RecapRow]:
    """Build recap rows from standings data.

    If standings_data not provided, loads from filesystem.
    """
    import os
    from pathlib import Path
    import yaml

    if standings_data is None:
        root = Path(os.environ.get("DCI_ROOT", "."))
        standings_path = root / "seasons" / season_id / "standings.yaml"
        if not standings_path.exists():
            return []
        standings_data = yaml.safe_load(standings_path.read_text())

    rows = []
    for result in standings_data.get("results", []):
        row = RecapRow(
            corps_id=result["corps_id"],
            corps_name=result.get("display_name", result["corps_id"][:8]),
            rank=result.get("rank", 0),
            raw_total=result.get("raw_score", 0.0),
            final_score=result.get("final_score", 0.0),
        )

        # Build per-caption breakdown from caption_scores
        caption_scores_raw = result.get("caption_scores", {})
        for caption, value in caption_scores_raw.items():
            # Value is the total_score (average of rep+perf)
            row.caption_scores[caption] = {
                "rep": value,  # Without separate data, use total for both
                "perf": value,
                "tot": value,
            }

        rows.append(row)

    # Sort by rank
    rows.sort(key=lambda r: r.rank)
    return rows


def export_recap_markdown(rows: list[RecapRow]) -> str:
    """Format recap as a wide markdown table like real DCI recap sheets."""
    if not rows:
        return "No results available."

    # Collect all captions across all rows
    all_captions = set()
    for row in rows:
        all_captions.update(row.caption_scores.keys())
    captions = sorted(all_captions)

    # Header
    header_parts = ["| Rank | Corps"]
    for cap in captions:
        title = cap.replace("_", " ").title()
        header_parts.append(f" {title} Rep | {title} Perf | {title} Tot")
    header_parts.append(" Penalties | Raw | Final |")
    header = "".join(header_parts)

    # Separator
    sep_parts = ["|---:|:---"]
    for _ in captions:
        sep_parts.append("|---:|---:|---:")
    sep_parts.append("|---:|---:|---:|")
    sep = "".join(sep_parts)

    # Rows
    lines = [header, sep]
    for row in rows:
        parts = [f"| {row.rank} | {row.corps_name}"]
        for cap in captions:
            cs = row.caption_scores.get(cap, {"rep": 0, "perf": 0, "tot": 0})
            parts.append(f" {cs['rep']:.1f} | {cs['perf']:.1f} | {cs['tot']:.1f}")
        parts.append(f" {row.penalties_total:.1f} | {row.raw_total:.1f} | {row.final_score:.1f} |")
        lines.append("".join(parts))

    return "\n".join(lines)


def export_recap_csv(rows: list[RecapRow]) -> str:
    """Export recap as CSV for download."""
    if not rows:
        return ""

    all_captions = set()
    for row in rows:
        all_captions.update(row.caption_scores.keys())
    captions = sorted(all_captions)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    header = ["Rank", "Corps ID", "Corps Name"]
    for cap in captions:
        title = cap.replace("_", " ").title()
        header.extend([f"{title} Rep", f"{title} Perf", f"{title} Tot"])
    header.extend(["Penalties", "Raw Total", "Final Score"])
    writer.writerow(header)

    # Data
    for row in rows:
        data = [row.rank, row.corps_id, row.corps_name]
        for cap in captions:
            cs = row.caption_scores.get(cap, {"rep": 0, "perf": 0, "tot": 0})
            data.extend([cs["rep"], cs["perf"], cs["tot"]])
        data.extend([row.penalties_total, row.raw_total, row.final_score])
        writer.writerow(data)

    return output.getvalue()
