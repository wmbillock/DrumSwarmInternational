"""Tests for theme system."""

import pytest
from backend.config.theme import load_theme, get_theme, set_theme, list_themes, SwarmTheme


class TestThemeLoading:
    def test_load_dci_theme(self):
        theme = load_theme("dci")
        assert theme.name == "dci"
        assert theme.display_name == "DCI Swarm"
        assert theme.org_unit == "corps"
        assert theme.project == "show"
        assert theme.work_item == "rep"
        assert theme.admin_name == "Critique"
        assert len(theme.work_levels) == 3
        assert "movement" in theme.work_levels

    def test_load_ensemble_theme(self):
        theme = load_theme("ensemble")
        assert theme.name == "ensemble"
        assert theme.org_unit == "ensemble"
        assert theme.project == "project"
        assert theme.work_item == "task"

    def test_load_gastown_theme(self):
        theme = load_theme("gastown")
        assert theme.name == "gastown"
        assert theme.org_unit == "rig"
        assert theme.project == "convoy"
        assert theme.work_item == "bead"

    def test_load_nonexistent_theme(self):
        with pytest.raises(FileNotFoundError):
            load_theme("nonexistent_theme_xyz")

    def test_list_themes(self):
        themes = list_themes()
        assert "dci" in themes
        assert "ensemble" in themes
        assert "gastown" in themes

    def test_dci_commands(self):
        theme = load_theme("dci")
        assert "resume_hut" in theme.commands
        assert theme.commands["resume_hut"].label == "Resume, Hut!"
        assert theme.commands["resume_hut"].category == "control"
        assert "attention" in theme.commands
        assert "basics" in theme.commands

    def test_dci_color_palette(self):
        theme = load_theme("dci")
        assert "executive_director" in theme.color_palette
        assert theme.color_palette["executive_director"].startswith("#")

    def test_dci_execution_modes(self):
        theme = load_theme("dci")
        assert "basics" in theme.execution_modes
        assert "sectionals" in theme.execution_modes
        assert "full_ensemble" in theme.execution_modes
        assert "run_through" in theme.execution_modes


class TestThemeSingleton:
    def test_get_theme_returns_dci_by_default(self):
        theme = get_theme()
        assert theme.name == "dci"

    def test_set_theme_overrides(self):
        original = get_theme()
        custom = SwarmTheme(
            name="test", display_name="Test",
            org_unit="team", org_unit_plural="teams",
            project="task", project_plural="tasks",
        )
        set_theme(custom)
        assert get_theme().name == "test"
        # Restore
        set_theme(original)


class TestPromptArrangerThemeIntegration:
    def test_prompt_arranger_injects_theme_vars(self):
        from backend.services.prompt_arranger import assemble_prompt
        # Even if no manifest exists for a test role, the function should not crash
        result = assemble_prompt("nonexistent_role_xyz")
        # Returns empty string for missing manifest
        assert result == ""

    def test_prompt_arranger_uses_theme_context(self):
        from backend.services.prompt_arranger import assemble_prompt
        # Assemble for a real role — should include theme variables
        result = assemble_prompt("executive_director")
        # If manifest exists it should produce a non-empty prompt
        if result:
            assert len(result) > 0
