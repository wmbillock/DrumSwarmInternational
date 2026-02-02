"""Shared helpers for V1 API routers."""

import colorsys
import hashlib
import os
import re
from pathlib import Path

from fastapi import HTTPException


def _get_root() -> Path:
    override = os.environ.get("DCI_PROJECT_ROOT", "")
    if override:
        return Path(override).resolve()
    from backend.cli.commands.doctor import _find_project_root
    return Path(_find_project_root())


def _validate_id(value: str, label: str = "id") -> None:
    """Reject path-traversal attempts and non-slug characters."""
    if ".." in value or "/" in value or "\\" in value:
        raise HTTPException(400, f"Invalid {label}: must not contain path separators")
    if not value:
        raise HTTPException(400, f"Invalid {label}: must not be empty")
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$", value):
        raise HTTPException(
            400,
            f"Invalid {label}: '{value}' must start with a letter or digit and contain only letters, digits, dots, underscores, or hyphens",
        )


def _get_db_session():
    """Get a SQLAlchemy session for DB fallback queries."""
    from backend.api.app import SessionFactory
    return SessionFactory()


def _get_llm_client():
    """Get the shared LLM client from the task manager."""
    try:
        from backend.api.app import get_task_manager
        tm = get_task_manager()
        if tm and hasattr(tm, "llm_client"):
            return tm.llm_client
    except (ImportError, AttributeError):
        pass
    return None


def _llm_chat(llm_client, system_prompt: str, user_message: str) -> str | None:
    """Send a chat to the LLM client and return the response text, or None on failure."""
    try:
        from backend.services.llm_client import LLMMessage
        from backend.models.agent_definition import ModelTier

        resp = llm_client.chat(
            messages=[
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_message),
            ],
            model_tier=ModelTier.HAIKU,
        )
        if resp.content and resp.stop_reason != "error":
            return resp.content.strip()
    except Exception:
        pass
    return None


def _slugify(text: str) -> str:
    """Convert a descriptive name to a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "season"


def _shows_dir() -> Path:
    root = _get_root()
    d = root / "shows"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _validate_slug(slug: str) -> None:
    if ".." in slug or "/" in slug or "\\" in slug:
        raise HTTPException(400, "Invalid show slug")
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", slug):
        raise HTTPException(400, "Invalid show slug")


def _show_dir(slug: str) -> Path:
    _validate_slug(slug)
    d = _shows_dir() / slug
    if not d.exists():
        raise HTTPException(404, f"Show '{slug}' not found")
    return d


def _generate_color_scheme(seed: str) -> dict:
    """Generate a deterministic DCI-inspired color scheme from a seed string."""
    h = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16)
    hue = (h % 360)
    r, g, b = colorsys.hls_to_rgb(hue / 360.0, 0.25, 0.7)
    primary = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    r, g, b = colorsys.hls_to_rgb(((hue + 30) % 360) / 360.0, 0.45, 0.5)
    secondary = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    r, g, b = colorsys.hls_to_rgb(((hue + 180) % 360) / 360.0, 0.55, 0.8)
    accent = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    return {"primary": primary, "secondary": secondary, "accent": accent}


def _parse_competition_id(competition_id: str, root: Path) -> tuple[str, str]:
    """Parse competition_id into (season_id, show_slug)."""
    import yaml
    seasons_dir = root / "seasons"
    if seasons_dir.exists():
        season_names = sorted(
            (d.name for d in seasons_dir.iterdir() if d.is_dir() and (d / "season.yaml").is_file()),
            key=len, reverse=True
        )
        for sdir_name in season_names:
            sdir = seasons_dir / sdir_name
            try:
                data = yaml.safe_load((sdir / "season.yaml").read_text())
                sid = data.get("season_id", sdir_name)
            except Exception:
                sid = sdir_name
            prefix = f"{sid}-"
            if competition_id.startswith(prefix) and len(competition_id) > len(prefix):
                return sid, competition_id[len(prefix):]
    parts = competition_id.split("-", 1)
    if len(parts) != 2:
        raise HTTPException(400, "Invalid competition_id format (expected season_id-show_slug)")
    return parts[0], parts[1]
