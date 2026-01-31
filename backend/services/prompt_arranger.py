"""PromptArranger — config-driven prompt assembly from markdown components + YAML manifests.

Assembles system prompts from reusable markdown components with Jinja2 variable substitution.
Components: role_identity, tool_protocol, phase_instructions, verification_rules.
"""

import os
from pathlib import Path
from typing import Optional

import yaml


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
MANIFESTS_DIR = PROMPTS_DIR / "manifests"


def _load_component(name: str) -> str:
    """Load a markdown component from the prompts directory."""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        return ""
    return path.read_text()


def _render_template(template: str, context: dict) -> str:
    """Simple Jinja2-style variable substitution.

    Supports {{ variable }} syntax. Falls back to empty string for missing vars.
    """
    import re
    def replace_var(match):
        var_name = match.group(1).strip()
        return str(context.get(var_name, ""))
    return re.sub(r'\{\{\s*(\w+)\s*\}\}', replace_var, template)


def load_manifest(role: str) -> Optional[dict]:
    """Load YAML manifest for a role."""
    path = MANIFESTS_DIR / f"{role}.yaml"
    if not path.exists():
        return None
    with open(path) as f:
        return yaml.safe_load(f)


def assemble_prompt(role: str, context: Optional[dict] = None) -> str:
    """Assemble a system prompt for a role from its manifest and components.

    Args:
        role: The agent role name.
        context: Variables for template substitution (e.g. tools list, phase info).

    Returns:
        Complete system prompt string.
    """
    ctx = context or {}
    ctx.setdefault("role", role)

    manifest = load_manifest(role)
    if manifest is None:
        return ""

    # Merge manifest-level context defaults
    for k, v in manifest.get("context", {}).items():
        ctx.setdefault(k, v)

    sections = []
    for component_name in manifest.get("components", []):
        component_text = _load_component(component_name)
        if component_text:
            rendered = _render_template(component_text, ctx)
            sections.append(rendered)

    # Add any inline content from the manifest
    if "inline" in manifest:
        rendered = _render_template(manifest["inline"], ctx)
        sections.append(rendered)

    return "\n\n".join(sections)


def get_available_roles() -> list[str]:
    """List all roles that have manifest files."""
    if not MANIFESTS_DIR.exists():
        return []
    return [p.stem for p in MANIFESTS_DIR.glob("*.yaml")]
