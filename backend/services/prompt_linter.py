"""Prompt linter ('Judge Snare') — validates show_prompt.md content.

The Swarm Prompt is a distilled action document telling agent corps what to build.
It is NOT a copy of the Brief. It should have a clear objective, specific deliverables,
and constraints — not the same section structure as the spec.
"""

import re
from dataclasses import dataclass, field
from typing import List

# Sections expected in the Swarm Prompt (action-oriented, not spec-mirroring)
REQUIRED_SECTIONS = [
    "Objective",
    "Deliverables",
]

RECOMMENDED_SECTIONS = [
    "Constraints",
    "Acceptance Criteria",
]

PLACEHOLDER_PATTERNS = [
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r"\bTBD\b", re.IGNORECASE),
    re.compile(r"\[PLACEHOLDER\]", re.IGNORECASE),
    re.compile(r"___"),
    re.compile(r"\bXXX\b", re.IGNORECASE),
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


def lint_prompt(content: str) -> LintReport:
    """Lint show_prompt.md content and return findings."""
    report = LintReport()

    if not content or len(content.strip()) < 30:
        report.required_fix.append(LintFinding(
            "Prompt", "Prompt is empty or too short. It should describe what the swarm needs to build."
        ))
        return report

    sections = _parse_sections(content)

    # Check required sections
    for name in REQUIRED_SECTIONS:
        if name not in sections:
            report.required_fix.append(LintFinding(name, f"Missing required section: ## {name}"))

    # Check recommended sections
    for name in RECOMMENDED_SECTIONS:
        if name not in sections:
            report.nice_to_have.append(LintFinding(name, f"Consider adding: ## {name}"))

    # Check each present section
    for name, body in sections.items():
        # Placeholder detection
        for pat in PLACEHOLDER_PATTERNS:
            if pat.search(body):
                report.required_fix.append(
                    LintFinding(name, f"Unfilled placeholder found: {pat.pattern}")
                )
                break

        # Short section
        if len(body) < 20:
            report.acceptable_risk.append(
                LintFinding(name, "Section has less than 20 characters of content")
            )

    # Deliverables should have bullet items
    if "Deliverables" in sections and _count_list_items(sections["Deliverables"]) < 1:
        report.required_fix.append(
            LintFinding("Deliverables", "Deliverables section has no list items — use bullets or numbered list")
        )

    # Constraints bullets
    if "Constraints" in sections and _count_list_items(sections["Constraints"]) < 1:
        report.nice_to_have.append(
            LintFinding("Constraints", "Constraints section has no list items")
        )

    return report
