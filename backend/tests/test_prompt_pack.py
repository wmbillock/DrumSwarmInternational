"""Tests for mode-specific prompt templates in prompts/."""

import pathlib
import re

import pytest

PROMPTS_DIR = pathlib.Path(__file__).resolve().parents[2] / "prompts"

TEMPLATES = {
    "design_room.md": ["corps_id", "season_id", "show_slug"],
    "show_mode.md": ["corps_id", "season_id", "show_slug"],
    "rehearsal_mode.md": ["corps_id", "season_id", "show_slug"],
    "offseason_review.md": ["corps_id", "season_id"],
    "judging.md": ["corps_id", "season_id", "show_slug"],
}

DRUM_CORPS_KEYWORDS = {"corps", "rehearsal", "performance", "season", "show", "judge"}


class TestPromptPack:
    def test_all_templates_exist(self):
        for name in TEMPLATES:
            path = PROMPTS_DIR / name
            assert path.exists(), f"Missing template: {name}"

    @pytest.mark.parametrize("name,placeholders", list(TEMPLATES.items()))
    def test_required_placeholders(self, name, placeholders):
        text = (PROMPTS_DIR / name).read_text()
        for var in placeholders:
            assert f"{{{{ {var} }}}}" in text, (
                f"{name} missing placeholder {{{{ {var} }}}}"
            )

    @pytest.mark.parametrize("name,placeholders", list(TEMPLATES.items()))
    def test_no_unfilled_after_substitution(self, name, placeholders):
        text = (PROMPTS_DIR / name).read_text()
        for var in placeholders:
            text = text.replace(f"{{{{ {var} }}}}", "VALUE")
        assert not re.search(r'\{\{\s*\w+\s*\}\}', text), f"{name} has unfilled placeholders after substitution"

    @pytest.mark.parametrize("name", list(TEMPLATES.keys()))
    def test_minimal_lint_no_empty(self, name):
        text = (PROMPTS_DIR / name).read_text()
        assert len(text) >= 50, f"{name} is too short ({len(text)} chars)"

    @pytest.mark.parametrize("name", list(TEMPLATES.keys()))
    def test_templates_reference_metaphor(self, name):
        text = (PROMPTS_DIR / name).read_text().lower()
        found = {kw for kw in DRUM_CORPS_KEYWORDS if kw in text}
        assert found, f"{name} contains no drum-corps keywords"
