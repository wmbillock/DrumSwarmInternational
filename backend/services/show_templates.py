"""Show templates — YAML-defined show structures (formulas).

Templates define segment tree skeletons, role requirements, verification
settings, and scoring weights. Instantiate a full show from a template.
"""

import logging
from pathlib import Path
from typing import Optional

import yaml
from sqlalchemy.orm import Session

from backend.models.segment import SegmentType
from backend.services.segment_service import create_segment
from backend.services.rep_service import create_rep

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "config" / "show_templates"


def list_templates() -> list[str]:
    """List available show template names."""
    if not TEMPLATES_DIR.exists():
        return []
    return [p.stem for p in TEMPLATES_DIR.glob("*.yaml")]


def load_template(name: str) -> dict:
    """Load a show template by name."""
    path = TEMPLATES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Show template '{name}' not found at {path}")
    with open(path) as f:
        return yaml.safe_load(f)


def create_show_from_template(
    db: Session,
    template_name: str,
    title: Optional[str] = None,
    params: Optional[dict] = None,
) -> dict:
    """Instantiate a full segment tree from a template.

    Returns dict with root segment and created structure summary.
    """
    template = load_template(template_name)
    params = params or {}

    show_title = title or template.get("title", template_name)
    description = template.get("description", "")

    # Create root show segment
    root = create_segment(
        db,
        type=SegmentType.SHOW,
        title=show_title,
        description=description,
    )

    created = {"root_id": root.id, "segments": 1, "reps": 0}

    # Build segment tree from template structure
    for movement_def in template.get("movements", []):
        movement = create_segment(
            db,
            type=SegmentType.MOVEMENT,
            title=_interpolate(movement_def.get("title", "Movement"), params),
            description=_interpolate(movement_def.get("description", ""), params),
            parent_id=root.id,
            caption=movement_def.get("caption"),
        )
        created["segments"] += 1

        for set_def in movement_def.get("sets", []):
            set_coord = create_segment(
                db,
                type=SegmentType.SET,
                title=_interpolate(set_def.get("title", "Set"), params),
                description=_interpolate(set_def.get("description", ""), params),
                parent_id=movement.id,
                caption=set_def.get("caption") or movement_def.get("caption"),
            )
            created["segments"] += 1

            for task_def in set_def.get("tasks", []):
                task = create_segment(
                    db,
                    type=SegmentType.SEGMENT,
                    title=_interpolate(task_def.get("title", "Task"), params),
                    description=_interpolate(task_def.get("description", ""), params),
                    parent_id=set_coord.id,
                    caption=task_def.get("caption") or set_def.get("caption") or movement_def.get("caption"),
                )
                created["segments"] += 1

                # Auto-create reps for leaf tasks
                if task_def.get("auto_rep", True):
                    create_rep(db, task.id)
                    created["reps"] += 1

    return created


def _interpolate(text: str, params: dict) -> str:
    """Simple parameter interpolation in template strings."""
    if not text or not params:
        return text
    for key, value in params.items():
        text = text.replace(f"{{{{{key}}}}}", str(value))
    return text
