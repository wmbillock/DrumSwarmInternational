"""Spec completion checker.

Parses deliverables from a show's spec.md, then cross-references with
completed reps and written artifacts to measure how much of the spec has
been implemented.
"""

import logging
import re
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _extract_deliverables(spec_text: str) -> list[str]:
    """Extract deliverable items from spec markdown.

    Looks for:
    - Items under a ## Deliverables heading
    - Checkbox items (- [ ] or - [x])
    - Numbered list items under Deliverables
    """
    deliverables: list[str] = []
    if not spec_text.strip():
        return deliverables

    # Find the Deliverables section
    deliv_match = re.search(
        r"##\s+Deliverables?\s*\n(.*?)(?=\n##|\Z)", spec_text, re.DOTALL
    )
    if deliv_match:
        section = deliv_match.group(1)
        for line in section.splitlines():
            line = line.strip()
            # Markdown list items: - item, * item, 1. item
            m = re.match(r"^[-*]\s+\[?[xX ]?\]?\s*(.+)$", line)
            if not m:
                m = re.match(r"^\d+\.\s+(.+)$", line)
            if m:
                text = m.group(1).strip()
                if text:
                    deliverables.append(text)

    # Also scan for checkbox items anywhere in the spec
    for line in spec_text.splitlines():
        m = re.match(r"^[-*]\s+\[[xX]\]\s+(.+)$", line.strip())
        if m:
            text = m.group(1).strip()
            if text and text not in deliverables:
                deliverables.append(text)

    # If no explicit deliverables found, extract from H2/H3 headings as goals
    if not deliverables:
        for line in spec_text.splitlines():
            m = re.match(r"^#{2,3}\s+(.+)$", line.strip())
            if m:
                heading = m.group(1).strip()
                # Skip meta-sections
                if heading.lower() not in {
                    "deliverables", "constraints", "evaluation rubric",
                    "overview", "summary", "references",
                }:
                    deliverables.append(heading)

    return deliverables


def _check_deliverable_against_reps(
    deliverable: str, completed_results: list[str]
) -> tuple[bool, str]:
    """Check if a deliverable is evidenced by any completed rep result.

    Simple keyword overlap heuristic — checks if key words from the
    deliverable appear in any rep result text.
    """
    # Extract meaningful words (3+ chars, lowered)
    keywords = {
        w.lower()
        for w in re.findall(r"\w+", deliverable)
        if len(w) >= 3
    }
    if not keywords:
        return False, ""

    best_match = ""
    best_overlap = 0
    for result in completed_results:
        if not result:
            continue
        result_words = {w.lower() for w in re.findall(r"\w+", result)}
        overlap = len(keywords & result_words)
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = result[:200]

    # Require at least 30% keyword overlap
    threshold = max(1, len(keywords) * 0.3)
    met = best_overlap >= threshold
    return met, best_match if met else ""


def check_spec_completion(
    show_dir: Path,
    db: Optional[Session] = None,
    corps_ids: Optional[list[str]] = None,
    segment_root_id: Optional[str] = None,
) -> dict:
    """Check how much of a show's spec has been implemented.

    Returns:
        {
            "deliverables_total": int,
            "deliverables_met": int,
            "completion_pct": float,
            "details": [{"deliverable": str, "status": "met"|"unmet", "evidence": str}],
        }
    """
    show_dir = Path(show_dir)
    spec_path = show_dir / "spec.md"

    if not spec_path.exists():
        return {
            "deliverables_total": 0,
            "deliverables_met": 0,
            "completion_pct": 0.0,
            "details": [],
        }

    spec_text = spec_path.read_text(encoding="utf-8")
    deliverables = _extract_deliverables(spec_text)

    if not deliverables:
        return {
            "deliverables_total": 0,
            "deliverables_met": 0,
            "completion_pct": 0.0,
            "details": [],
        }

    # Gather evidence: completed rep results
    completed_results: list[str] = []
    if db and segment_root_id:
        from backend.models.rep import Rep, RepStatus
        from backend.models.segment import Segment

        # Collect segment IDs under root
        seen: set[str] = set()
        stack = [segment_root_id]
        seg_ids: list[str] = []
        while stack:
            sid = stack.pop()
            if sid in seen:
                continue
            seen.add(sid)
            seg_ids.append(sid)
            children = db.query(Segment.id).filter(Segment.parent_id == sid).all()
            stack.extend(row[0] for row in children)

        if seg_ids:
            reps = (
                db.query(Rep)
                .filter(
                    Rep.segment_id.in_(seg_ids),
                    Rep.status == RepStatus.COMPLETED,
                )
                .all()
            )
            completed_results = [r.result for r in reps if r.result]

    # Also gather artifact labels
    if db and corps_ids:
        from backend.models.artifact import Artifact
        artifacts = (
            db.query(Artifact)
            .filter(Artifact.corps_id.in_(corps_ids))
            .all()
        )
        for a in artifacts:
            if a.label:
                completed_results.append(a.label)

    # Check files in show directory as additional evidence
    for f in show_dir.iterdir():
        if f.is_file() and f.suffix in (".md", ".yaml", ".json", ".txt"):
            completed_results.append(f.name)

    # Check each deliverable
    details: list[dict] = []
    met_count = 0
    for d in deliverables:
        is_met, evidence = _check_deliverable_against_reps(d, completed_results)
        if is_met:
            met_count += 1
        details.append({
            "deliverable": d,
            "status": "met" if is_met else "unmet",
            "evidence": evidence,
        })

    total = len(deliverables)
    return {
        "deliverables_total": total,
        "deliverables_met": met_count,
        "completion_pct": round((met_count / total) * 100, 1) if total > 0 else 0.0,
        "details": details,
    }
