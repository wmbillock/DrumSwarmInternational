"""Tests for prompt arranger."""

from backend.services.prompt_arranger import assemble_prompt, load_manifest, get_available_roles, _render_template


class TestRenderTemplate:
    def test_basic_substitution(self):
        result = _render_template("Hello {{ name }}", {"name": "World"})
        assert result == "Hello World"

    def test_missing_var(self):
        result = _render_template("Hello {{ name }}", {})
        assert result == "Hello "

    def test_multiple_vars(self):
        result = _render_template("{{ a }} and {{ b }}", {"a": "X", "b": "Y"})
        assert result == "X and Y"


class TestPromptArranger:
    def test_load_manifest(self):
        m = load_manifest("executive_director")
        assert m is not None
        assert "components" in m

    def test_load_manifest_missing(self):
        m = load_manifest("nonexistent_role_xyz")
        assert m is None

    def test_assemble_prompt(self):
        prompt = assemble_prompt("executive_director")
        assert prompt  # Should produce non-empty prompt
        assert "Executive Director" in prompt

    def test_assemble_prompt_missing_role(self):
        prompt = assemble_prompt("nonexistent_role_xyz")
        assert prompt == ""

    def test_get_available_roles(self):
        roles = get_available_roles()
        assert "executive_director" in roles
        assert "brass_tech" in roles

    def test_all_roles_produce_prompts(self):
        roles = get_available_roles()
        for role in roles:
            prompt = assemble_prompt(role)
            assert prompt, f"No prompt generated for {role}"
