"""Art Director — automatic style classification and image generation.

Given a text description, picks the right workflow template and builds
a style-appropriate prompt, then delegates to image_service for generation.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

WORKFLOWS_DIR = Path(__file__).parent.parent / "config" / "comfyui_workflows"

# Keyword → category mappings.  Order matters: first match wins.
_CATEGORY_RULES: list[tuple[list[str], str]] = [
    (["icon", "button", "ui", "nav", "toolbar", "menu"], "web_icons"),
    (["16-bit", "16bit", "snes", "genesis", "mega drive"], "pixel_art_16bit"),
    (["pixel", "8-bit", "8bit", "retro", "nes", "chiptune"], "pixel_art_8bit"),
    (["sprite", "2d game", "platformer", "side-scroller", "tileset"], "game_art_2d"),
    (["realistic", "photo", "photograph", "human", "headshot"], "photo_realistic"),
    (["emblem", "crest", "badge", "heraldry", "coat of arms", "insignia"], "stylized_icon"),
    (["logo", "brand", "corporate", "wordmark", "logotype", "monogram"], "corporate_logo"),
    (["cartoon", "anime", "animated", "toon", "cel-shaded"], "cartoon_animation"),
    (["poster", "banner", "flyer", "event art", "promotional"], "show_poster"),
    (["character", "avatar", "agent", "portrait", "face"], "character_portrait"),
]

_DEFAULT_CATEGORY = "game_art_2d"

# All valid category names (loaded lazily from workflow files)
_ALL_CATEGORIES: Optional[list[str]] = None


def _get_all_categories() -> list[str]:
    """Return sorted list of all category names from workflow files."""
    global _ALL_CATEGORIES
    if _ALL_CATEGORIES is not None:
        return _ALL_CATEGORIES
    cats = []
    if WORKFLOWS_DIR.exists():
        for f in sorted(WORKFLOWS_DIR.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                # Only include template workflows (not native API ones)
                if not data.get("native_api"):
                    cats.append(f.stem)
            except Exception:
                pass
    _ALL_CATEGORIES = cats
    return _ALL_CATEGORIES


def classify(description: str) -> str:
    """Classify a text description into an art category.

    Uses keyword matching against the description.  Returns the best
    matching category name, or the default fallback.
    """
    text = description.lower()
    for keywords, category in _CATEGORY_RULES:
        for kw in keywords:
            if kw in text:
                return category
    return _DEFAULT_CATEGORY


def list_categories() -> list[dict]:
    """Return all available art categories with descriptions."""
    result = []
    for cat_name in _get_all_categories():
        path = WORKFLOWS_DIR / f"{cat_name}.json"
        try:
            data = json.loads(path.read_text())
            result.append({
                "category": cat_name,
                "description": data.get("description", ""),
                "width": data.get("width", 1024),
                "height": data.get("height", 1024),
                "steps": data.get("steps", 20),
                "cfg_scale": data.get("cfg_scale", 7.0),
            })
        except Exception:
            result.append({"category": cat_name, "description": ""})
    return result


def generate(
    description: str,
    category: Optional[str] = None,
    seed: Optional[int] = None,
    output_filename: Optional[str] = None,
) -> dict:
    """Generate art using the art director pipeline.

    1. Classify the description (or use the explicit category).
    2. Load the matching workflow template.
    3. Inject the description into the prompt template.
    4. Delegate to image_service.generate_from_workflow().
    5. Return result + metadata.
    """
    from backend.services.image_service import generate_from_workflow

    chosen_category = category if category else classify(description)

    # Validate the category exists
    template_path = WORKFLOWS_DIR / f"{chosen_category}.json"
    if not template_path.exists():
        return {
            "success": False,
            "output_path": None,
            "error": f"Unknown category '{chosen_category}'",
            "workflow_used": None,
            "category": chosen_category,
            "prompt_used": None,
        }

    # Load the template to build the final prompt
    try:
        template = json.loads(template_path.read_text())
    except Exception as e:
        return {
            "success": False,
            "output_path": None,
            "error": f"Failed to load template: {e}",
            "workflow_used": chosen_category,
            "category": chosen_category,
            "prompt_used": None,
        }

    # Build the final prompt by substituting {description}
    prompt_template = template.get("prompt_template", "{description}")
    try:
        final_prompt = prompt_template.format(description=description)
    except KeyError:
        # Template has other placeholders — just use description raw
        final_prompt = prompt_template.replace("{description}", description)

    result = generate_from_workflow(
        workflow_name=chosen_category,
        template_vars={"description": description},
        seed=seed,
        output_filename=output_filename,
        prompt_override=final_prompt,
    )

    result["category"] = chosen_category
    result["prompt_used"] = final_prompt
    return result
