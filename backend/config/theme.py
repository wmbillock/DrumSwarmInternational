"""Theme system — configurable domain language for the swarm orchestrator.

All four swarm variants (DCI, Ensemble, Lebowski, Gastown) use the same
orchestration patterns with different metaphors. This module lets the domain
vocabulary be configured via YAML theme files.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class CommandDef:
    label: str
    description: str
    category: str


@dataclass
class SwarmTheme:
    name: str
    display_name: str
    # Organizational units
    org_unit: str                          # "corps", "ensemble", "rig"
    org_unit_plural: str                   # "corps", "ensembles", "rigs"
    project: str                           # "show", "project", "convoy"
    project_plural: str                    # "shows", "projects", "convoys"
    work_levels: list[str] = field(default_factory=list)  # ["movement","set","segment"]
    work_item: str = "rep"                 # "rep", "task", "bead"
    work_item_plural: str = "reps"
    # Role tier names
    tier_labels: dict[str, str] = field(default_factory=dict)  # "opus" -> "Strategic"
    # Lifecycle states
    org_states: list[str] = field(default_factory=list)
    execution_modes: list[str] = field(default_factory=list)
    # Commands
    commands: dict[str, CommandDef] = field(default_factory=dict)
    # UI
    color_palette: dict[str, str] = field(default_factory=dict)
    # Admin section name
    admin_name: str = "Admin"


THEMES_DIR = Path(__file__).parent / "themes"

_current_theme: Optional[SwarmTheme] = None


def _parse_commands(raw: dict) -> dict[str, CommandDef]:
    result = {}
    for key, val in raw.items():
        if isinstance(val, dict):
            result[key] = CommandDef(
                label=val.get("label", key),
                description=val.get("description", ""),
                category=val.get("category", "general"),
            )
    return result


def load_theme(name: str) -> SwarmTheme:
    """Load a theme from YAML file."""
    path = THEMES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Theme '{name}' not found at {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    return SwarmTheme(
        name=data.get("name", name),
        display_name=data.get("display_name", name.title()),
        org_unit=data.get("org_unit", "corps"),
        org_unit_plural=data.get("org_unit_plural", data.get("org_unit", "corps")),
        project=data.get("project", "show"),
        project_plural=data.get("project_plural", data.get("project", "show") + "s"),
        work_levels=data.get("work_levels", ["movement", "set", "segment"]),
        work_item=data.get("work_item", "rep"),
        work_item_plural=data.get("work_item_plural", "reps"),
        tier_labels=data.get("tier_labels", {}),
        org_states=data.get("org_states", []),
        execution_modes=data.get("execution_modes", []),
        commands=_parse_commands(data.get("commands", {})),
        color_palette=data.get("color_palette", {}),
        admin_name=data.get("admin_name", "Admin"),
    )


def get_theme() -> SwarmTheme:
    """Get the current theme (loads from DCI_THEME env var or defaults to 'dci')."""
    global _current_theme
    if _current_theme is None:
        theme_name = os.environ.get("DCI_THEME", "dci")
        try:
            _current_theme = load_theme(theme_name)
        except FileNotFoundError:
            # Return a minimal DCI default if no theme file exists
            _current_theme = SwarmTheme(
                name="dci",
                display_name="DCI Swarm",
                org_unit="corps",
                org_unit_plural="corps",
                project="show",
                project_plural="shows",
                work_levels=["movement", "set", "segment"],
                work_item="rep",
                work_item_plural="reps",
                admin_name="Critique",
            )
    return _current_theme


def set_theme(theme: SwarmTheme) -> None:
    """Override the current theme (useful for testing)."""
    global _current_theme
    _current_theme = theme


def list_themes() -> list[str]:
    """List available theme names."""
    if not THEMES_DIR.exists():
        return []
    return [p.stem for p in THEMES_DIR.glob("*.yaml")]
