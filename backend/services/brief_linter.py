"""Brief linter — validates spec.md (the Brief) content.

The Brief is the structured design document with show concept, musical design,
visual design, guard design, general effect, constraints, and deliverables.
"""

import re
from dataclasses import dataclass, field
from typing import List

REQUIRED_SECTIONS = [
    "Show Concept",
    "Musical Design",
    "Visual Design",
    "Guard Design",
    "General Effect",
    "Constraints",
    "Deliverables",
]

PLACEHOLDER_PATTERNS = [
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r"\bTBD\b", re.IGNORECASE),
    re.compile(r"\[PLACEHOLDER\]", re.IGNORECASE),
    re.compile(r"___"),
    re.compile(r"\bXXX\b", re.IGNORECASE),
    re.compile(r"awaiting design input", re.IGNORECASE),
]


@dataclass
class LintFinding:
    section: str
    message: str


@dataclass
class LintReport:
    required_fix: List[LintFinding] = field(default_factory=list)
    nice_to_have: List[LintFinding] = field(default_factory=list)
    acceptable_risk: List[LintFinding] = field(default_factory=list)


def _parse_sections(content: str) -> dict[str, str]:
    """Parse markdown into {section_name: body} mapping."""
    sections: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for line in content.splitlines():
        m = re.match(r"^##\s+(.+)$", line)
        if m:
            if current is not None:
                sections[current] = "\n".join(lines).strip()
            current = m.group(1).strip()
            lines = []
        else:
            lines.append(line)
    if current is not None:
        sections[current] = "\n".join(lines).strip()
    return sections


def _count_list_items(text: str) -> int:
    """Count bullet points (- / *) and numbered list items (1. / 2.) etc."""
    bullets = len(re.findall(r"^\s*[-*]\s+", text, re.MULTILINE))
    numbered = len(re.findall(r"^\s*\d+[.)]\s+", text, re.MULTILINE))
    return bullets + numbered


def lint_brief(content: str) -> LintReport:
    """Lint spec.md (Brief) content and return findings."""
    report = LintReport()

    if not content or len(content.strip()) < 30:
        report.required_fix.append(LintFinding(
            "Brief", "Brief is empty or too short."
        ))
        return report

    sections = _parse_sections(content)

    # Check required sections
    for name in REQUIRED_SECTIONS:
        if name not in sections:
            report.required_fix.append(LintFinding(name, f"Missing required section: ## {name}"))

    # Check each present section
    for name, body in sections.items():
        for pat in PLACEHOLDER_PATTERNS:
            if pat.search(body):
                report.required_fix.append(
                    LintFinding(name, f"Unfilled placeholder: {pat.pattern}")
                )
                break

        if len(body) < 20:
            report.acceptable_risk.append(
                LintFinding(name, "Section has less than 20 characters")
            )

    # Constraints bullets
    if "Constraints" in sections and _count_list_items(sections["Constraints"]) < 2:
        report.nice_to_have.append(
            LintFinding("Constraints", "Fewer than 2 list items")
        )

    # Deliverables bullets
    if "Deliverables" in sections and _count_list_items(sections["Deliverables"]) < 1:
        report.required_fix.append(
            LintFinding("Deliverables", "No list items — use bullets or numbered list")
        )

    return report
