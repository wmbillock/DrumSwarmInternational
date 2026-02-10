"""Image service — high-level image generation using ComfyUI.

Provides workflow-based generation (show posters, corps logos, etc.)
and raw prompt generation. Falls back gracefully when ComfyUI is offline.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def generate_image(
    prompt: str,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    steps: int = 20,
    cfg_scale: float = 7.0,
    seed: Optional[int] = None,
    output_filename: Optional[str] = None,
) -> dict:
    """Generate an image from a text prompt.

    Returns {success, output_path, error}.
    """
    from backend.tools.image_generator import get_connector

    connector = get_connector()
    return connector.generate(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        steps=steps,
        cfg_scale=cfg_scale,
        seed=seed,
        output_filename=output_filename,
    )


def generate_from_workflow(
    workflow_name: str,
    template_vars: Optional[dict] = None,
    seed: Optional[int] = None,
    output_filename: Optional[str] = None,
) -> dict:
    """Generate an image using a named workflow template.

    Template variables are substituted into the prompt_template.
    Returns {success, output_path, error, workflow_used}.
    """
    from backend.tools.image_generator import load_workflow_template, get_connector

    template = load_workflow_template(workflow_name)
    if template is None:
        return {
            "success": False,
            "output_path": None,
            "error": f"Workflow template '{workflow_name}' not found",
            "workflow_used": workflow_name,
        }

    # Build prompt from template
    prompt_template = template.get("prompt_template", "")
    vars_dict = template_vars or {}
    try:
        prompt = prompt_template.format(**vars_dict)
    except KeyError as e:
        prompt = prompt_template  # Use raw template if vars missing

    result = generate_image(
        prompt=prompt,
        negative_prompt=template.get("negative_prompt", ""),
        width=template.get("width", 1024),
        height=template.get("height", 1024),
        steps=template.get("steps", 20),
        cfg_scale=template.get("cfg_scale", 7.0),
        seed=seed,
        output_filename=output_filename,
    )
    result["workflow_used"] = workflow_name
    return result


def list_workflows() -> list[dict]:
    """List available workflow templates."""
    from backend.tools.image_generator import CONFIG_DIR

    workflows_dir = CONFIG_DIR / "comfyui_workflows"
    if not workflows_dir.exists():
        return []

    result = []
    for f in sorted(workflows_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            result.append({
                "name": f.stem,
                "description": data.get("description", ""),
                "prompt_template": data.get("prompt_template", ""),
                "width": data.get("width", 1024),
                "height": data.get("height", 1024),
            })
        except Exception:
            pass

    return result


def check_status() -> dict:
    """Check if ComfyUI is available and return status."""
    from backend.tools.image_generator import get_connector

    connector = get_connector()
    available = connector.is_available()
    return {
        "available": available,
        "server_url": connector.server_url,
    }
