"""Recap Sheet — DCI-style wide table of all corps scores for a competition."""

import csv
import io
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.score import JudgeType, Score
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


def _load_db_caption_details(
    db: Session, corps_ids: list[str],
) -> dict[str, dict[str, dict[str, float]]]:
    """Query Score table for rep/perf breakdown per corps per caption.

    Returns {corps_id: {caption: {"rep": x, "perf": y, "tot": z}}}.
    Uses the latest score per (corps_id, judge_type).
    """
    from sqlalchemy import select, and_

    details: dict[str, dict[str, dict[str, float]]] = {}
    if not corps_ids:
        return details

    stmt = (
        select(Score)
        .where(Score.corps_id.in_(corps_ids))
        .order_by(Score.created_at.desc())
    )
    all_scores = db.execute(stmt).scalars().all()

    # Keep only the latest score per (corps_id, judge_type)
    latest: dict[tuple[str, str], Score] = {}
    for s in all_scores:
        key = (s.corps_id, s.judge_type.value if hasattr(s.judge_type, 'value') else str(s.judge_type))
        if key not in latest:
            latest[key] = s

    for (cid, caption), score in latest.items():
        if cid not in details:
            details[cid] = {}
        rep = score.rep_score if score.rep_score is not None else score.value
        perf = score.perf_score if score.perf_score is not None else score.value
        tot = (rep + perf) / 2 if (score.rep_score is not None and score.perf_score is not None) else score.value
        details[cid][caption] = {"rep": rep, "perf": perf, "tot": tot}

    return details


def generate_recap_sheet(
    season_id: str,
    show_slug: str,
    standings_data: Optional[dict] = None,
    competition_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> list[RecapRow]:
    """Build recap rows from standings data.

    If standings_data not provided, loads from filesystem.
    Tries per-competition file first, then global standings.yaml.
    """
    import os
    from pathlib import Path

    if standings_data is None:
        from backend.services.yaml_util import safe_load_yaml_dict
        root = Path(os.environ.get("DCI_ROOT", "."))
        season_dir = root / "seasons" / season_id

        # Try per-competition standings file first
        if competition_id:
            per_comp = season_dir / f"standings_{competition_id}.yaml"
            if per_comp.exists():
                standings_data = safe_load_yaml_dict(per_comp.read_text())

        # Try schedule entry in season.yaml
        if (not standings_data or not standings_data.get("results")) and competition_id:
            season_yaml = season_dir / "season.yaml"
            if season_yaml.is_file():
                season_data = safe_load_yaml_dict(season_yaml.read_text())
                for entry in (season_data.get("schedule") or []):
                    if entry.get("competition_id") == competition_id and entry.get("standings"):
                        standings_data = {
                            "season_id": season_id,
                            "results": entry["standings"],
                        }
                        break

        # Fall back to global standings.yaml
        if not standings_data or not standings_data.get("results"):
            standings_path = season_dir / "standings.yaml"
            if not standings_path.exists():
                return []
            standings_data = safe_load_yaml_dict(standings_path.read_text())

    # Check if any results lack caption_details — if so, try DB enrichment
    results = standings_data.get("results", [])
    needs_db = any(not r.get("caption_details") for r in results)
    db_details: dict[str, dict[str, dict[str, float]]] = {}
    if needs_db and db is not None:
        corps_ids = [r["corps_id"] for r in results]
        db_details = _load_db_caption_details(db, corps_ids)

    rows = []
    for result in results:
        row = RecapRow(
            corps_id=result["corps_id"],
            corps_name=result.get("display_name", result["corps_id"][:8]),
            rank=result.get("rank", 0),
            raw_total=result.get("raw_score", 0.0),
            final_score=result.get("final_score", 0.0),
        )

        # Build per-caption breakdown from caption_details (rep/perf/tot) if available
        caption_details = result.get("caption_details", {})
        # Fall back to DB-sourced details if standings data lacks them
        if not caption_details and result["corps_id"] in db_details:
            caption_details = db_details[result["corps_id"]]
        caption_scores_raw = result.get("caption_scores", {})
        for caption, value in caption_scores_raw.items():
            detail = caption_details.get(caption)
            if detail and "rep" in detail and "perf" in detail:
                row.caption_scores[caption] = {
                    "rep": detail["rep"],
                    "perf": detail["perf"],
                    "tot": detail.get("tot", value),
                }
            else:
                row.caption_scores[caption] = {
                    "rep": value,
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
