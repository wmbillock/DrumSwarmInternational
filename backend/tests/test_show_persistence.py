"""Tests for show persistence layer."""

import pytest
import yaml

from backend.services.show_persistence import (
    append_design_notes,
    check_field_ready,
    create_show,
    load_status,
    slugify,
    synthesize_prompt,
    update_status,
)


class TestSlugify:
    def test_basic(self):
        assert slugify("My Cool Show") == "my-cool-show"

    def test_strips_punctuation(self):
        assert slugify("My Cool Show!") == "my-cool-show"

    def test_collapses_hyphens(self):
        assert slugify("foo---bar") == "foo-bar"

    def test_strips_leading_trailing(self):
        assert slugify("--hello--") == "hello"


class TestCreateShow:
    def test_creates_workspace(self, tmp_path):
        show_dir = create_show("My Cool Show", tmp_path)
        assert show_dir.name == "my-cool-show"
        assert (show_dir / "design_notes.md").exists()
        assert (show_dir / "show_prompt.md").exists()
        assert (show_dir / "status.yaml").exists()

    def test_default_status_is_draft(self, tmp_path):
        show_dir = create_show("My Cool Show", tmp_path)
        status = yaml.safe_load((show_dir / "status.yaml").read_text())
        assert status["status"] == "draft"

    def test_slug_collision(self, tmp_path):
        first = create_show("My Cool Show", tmp_path)
        second = create_show("My Cool Show", tmp_path)
        assert first.name == "my-cool-show"
        assert second.name == "my-cool-show-2"

    def test_slug_collision_increments(self, tmp_path):
        create_show("My Cool Show", tmp_path)
        create_show("My Cool Show", tmp_path)
        third = create_show("My Cool Show", tmp_path)
        assert third.name == "my-cool-show-3"


class TestDesignNotes:
    def test_append(self, tmp_path):
        show_dir = create_show("Test", tmp_path)
        append_design_notes(show_dir, "first note")
        append_design_notes(show_dir, "second note")
        content = (show_dir / "design_notes.md").read_text()
        assert "first note" in content
        assert "second note" in content


class TestSynthesizePrompt:
    def test_writes_content(self, tmp_path):
        show_dir = create_show("Test", tmp_path)
        synthesize_prompt(show_dir)
        content = (show_dir / "show_prompt.md").read_text()
        assert len(content) > 0

    def test_has_required_sections(self, tmp_path):
        show_dir = create_show("Test", tmp_path)
        # Write a spec with a title
        (show_dir / "spec.md").write_text("# My Great Show\n\nA show about something.\n")
        synthesize_prompt(show_dir)
        content = (show_dir / "show_prompt.md").read_text()
        for section in ["Show Concept", "Musical Design", "Visual Design",
                        "Guard Design", "General Effect", "Constraints",
                        "Deliverables", "Evaluation Rubric"]:
            assert f"## {section}" in content

    def test_incorporates_spec_title(self, tmp_path):
        show_dir = create_show("Test", tmp_path)
        (show_dir / "spec.md").write_text("# Stellar Voyage\n\nA cosmic journey.\n")
        synthesize_prompt(show_dir)
        content = (show_dir / "show_prompt.md").read_text()
        assert "Stellar Voyage" in content

    def test_routes_tagged_notes(self, tmp_path):
        show_dir = create_show("Test", tmp_path)
        notes = "<!-- tags: music_writer -->\nBrass fanfare in measure 12.\n"
        (show_dir / "design_notes.md").write_text(notes)
        synthesize_prompt(show_dir)
        content = (show_dir / "show_prompt.md").read_text()
        assert "Brass fanfare in measure 12" in content
        assert "## Musical Design" in content


class TestStatus:
    def test_load_status(self, tmp_path):
        show_dir = create_show("Test", tmp_path)
        status = load_status(show_dir)
        assert status["status"] == "draft"

    def test_update_valid(self, tmp_path):
        show_dir = create_show("Test", tmp_path)
        update_status(show_dir, "needs_review")
        assert load_status(show_dir)["status"] == "needs_review"

    def test_update_invalid_raises(self, tmp_path):
        show_dir = create_show("Test", tmp_path)
        with pytest.raises(ValueError):
            update_status(show_dir, "bogus")


class TestApprovalGate:
    def test_not_ready_when_draft(self, tmp_path):
        show_dir = create_show("Test", tmp_path)
        assert check_field_ready(show_dir) is False

    def test_ready_when_approved(self, tmp_path):
        show_dir = create_show("Test", tmp_path)
        update_status(show_dir, "approved")
        assert check_field_ready(show_dir) is True
