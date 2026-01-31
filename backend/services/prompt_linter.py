"""Prompt linter ('Judge Snare') — validates show_prompt.md content."""

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
    "Evaluation Rubric",
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


def _count_bullets(text: str) -> int:
    return len(re.findall(r"^\s*[-*]\s+", text, re.MULTILINE))


def lint_prompt(content: str) -> LintReport:
    """Lint show_prompt.md content and return findings."""
    report = LintReport()
    sections = _parse_sections(content)

    # Check required sections
    for name in REQUIRED_SECTIONS:
        if name not in sections:
            report.required_fix.append(LintFinding(name, f"Missing required section: ## {name}"))

    # Check each present section
    for name, body in sections.items():
        # Placeholder detection
        for pat in PLACEHOLDER_PATTERNS:
            if pat.search(body):
                report.required_fix.append(
                    LintFinding(name, f"Unfilled placeholder found: {pat.pattern}")
                )
                break  # one finding per section for placeholders

        # Short section
        if len(body) < 20:
            report.acceptable_risk.append(
                LintFinding(name, "Section has less than 20 characters of content")
            )

    # Constraints bullets
    if "Constraints" in sections and _count_bullets(sections["Constraints"]) < 2:
        report.nice_to_have.append(
            LintFinding("Constraints", "Constraints section has fewer than 2 bullet items")
        )

    # Deliverables bullets
    if "Deliverables" in sections and _count_bullets(sections["Deliverables"]) < 1:
        report.required_fix.append(
            LintFinding("Deliverables", "Deliverables section has no bullet items")
        )

    # Evaluation Rubric empty/no references
    if "Evaluation Rubric" in sections:
        body = sections["Evaluation Rubric"]
        if not body or not body.strip():
            report.nice_to_have.append(
                LintFinding("Evaluation Rubric", "Evaluation Rubric section is empty or has no references")
            )

    # Ambiguous MUST
    for name, body in sections.items():
        for m in re.finditer(r"\bMUST\b", body):
            start = m.start()
            snippet = body[start:start + 60]
            # Check for concrete verb/noun after MUST — simplistic: at least one lowercase word follows
            after_must = snippet[4:].strip()
            if not re.match(r"[a-z]", after_must):
                report.nice_to_have.append(
                    LintFinding(name, f"Ambiguous MUST without concrete verb/noun within 60 chars")
                )

    return report
