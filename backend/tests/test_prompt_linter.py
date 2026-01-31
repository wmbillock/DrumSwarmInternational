"""Tests for prompt_linter."""

from backend.services.prompt_linter import lint_prompt


MINIMAL_VALID = """## Show Concept
A show about the ocean and waves crashing on shore.

## Musical Design
Features brass fanfares and percussion features throughout.

## Visual Design
Formations represent waves and water movement patterns.

## Guard Design
Silks in blue and white represent ocean spray and foam.

## General Effect
The audience should feel transported to a coastal setting with immersive sound.

## Constraints
- Must fit within 11 minutes
- Maximum 150 performers on field

## Deliverables
- Full drill charts for all movements

## Evaluation Rubric
Scoring follows DCI caption judging: music, visual, guard, GE.
"""


def test_deliberately_incomplete():
    content = """## Show Concept
TODO fill this in

## Musical Design
TBD
"""
    report = lint_prompt(content)
    # Missing sections
    missing = [f.section for f in report.required_fix if "Missing" in f.message]
    assert "Visual Design" in missing
    assert "Guard Design" in missing
    assert "Deliverables" in missing
    # Placeholders
    placeholder = [f.section for f in report.required_fix if "placeholder" in f.message.lower() or "Unfilled" in f.message]
    assert "Show Concept" in placeholder
    assert "Musical Design" in placeholder


def test_minimal_valid():
    report = lint_prompt(MINIMAL_VALID)
    assert report.required_fix == []


def test_placeholder_detection():
    for marker in ["TODO", "TBD", "[PLACEHOLDER]"]:
        content = f"""## Show Concept
Some text here with {marker} inside.

## Musical Design
Content here is valid and long enough to pass checks.

## Visual Design
Content here is valid and long enough to pass checks.

## Guard Design
Content here is valid and long enough to pass checks.

## General Effect
Content here is valid and long enough to pass checks.

## Constraints
- Item one
- Item two

## Deliverables
- Drill charts

## Evaluation Rubric
Standard DCI evaluation criteria apply here.
"""
        report = lint_prompt(content)
        placeholder_sections = [f.section for f in report.required_fix if "Unfilled" in f.message]
        assert "Show Concept" in placeholder_sections, f"Failed for {marker}"


def test_short_section_acceptable_risk():
    content = MINIMAL_VALID.replace(
        "A show about the ocean and waves crashing on shore.",
        "Short.",
    )
    report = lint_prompt(content)
    risk_sections = [f.section for f in report.acceptable_risk if "less than 20" in f.message]
    assert "Show Concept" in risk_sections


def test_missing_deliverables_bullets():
    content = MINIMAL_VALID.replace(
        "- Full drill charts for all movements",
        "No bullets here just text.",
    )
    report = lint_prompt(content)
    assert any(f.section == "Deliverables" and "no bullet" in f.message.lower() for f in report.required_fix)
