"""Tests for prompt_linter."""

from backend.services.prompt_linter import lint_prompt


MINIMAL_VALID = """## Objective
Build an ocean-themed show with brass fanfares and guard features.

## Deliverables
- Full drill charts for all movements
- Musical score with brass and percussion parts
- Guard choreography document

## Constraints
- Must fit within 11 minutes
- Maximum 150 performers on field

## Acceptance Criteria
- All movements reviewed by caption heads
- Scoring follows DCI caption judging: music, visual, guard, GE
"""


def test_deliberately_incomplete():
    content = """## Objective
TODO fill this in

## Constraints
TBD
"""
    report = lint_prompt(content)
    # Missing sections
    missing = [f.section for f in report.required_fix if "Missing" in f.message]
    assert "Deliverables" in missing
    # Placeholders
    placeholder = [f.section for f in report.required_fix if "placeholder" in f.message.lower() or "Unfilled" in f.message]
    assert "Objective" in placeholder
    assert "Constraints" in placeholder


def test_minimal_valid():
    report = lint_prompt(MINIMAL_VALID)
    assert report.required_fix == []


def test_placeholder_detection():
    for marker in ["TODO", "TBD", "[PLACEHOLDER]"]:
        content = f"""## Objective
Some text here with {marker} inside this objective section.

## Deliverables
- Drill charts
- Musical score
"""
        report = lint_prompt(content)
        placeholder_sections = [f.section for f in report.required_fix if "Unfilled" in f.message]
        assert "Objective" in placeholder_sections, f"Failed for {marker}"


def test_short_section_acceptable_risk():
    content = MINIMAL_VALID.replace(
        "Build an ocean-themed show with brass fanfares and guard features.",
        "Short.",
    )
    report = lint_prompt(content)
    risk_sections = [f.section for f in report.acceptable_risk if "less than 20" in f.message]
    assert "Objective" in risk_sections


def test_missing_deliverables_bullets():
    content = MINIMAL_VALID.replace(
        "- Full drill charts for all movements\n- Musical score with brass and percussion parts\n- Guard choreography document",
        "No bullets here just text.",
    )
    report = lint_prompt(content)
    assert any(f.section == "Deliverables" and "no list items" in f.message.lower() for f in report.required_fix)
