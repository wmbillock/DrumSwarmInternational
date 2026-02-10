"""DCI Swarm — Rehearsal Tools.

Registers all tools in a shared ToolRegistry for use by agent sessions.
"""

from backend.services.tool_executor import ToolRegistry
from backend.services.tool_registry_setup import register_service_tools
from backend.tools.metronome import tick as metronome_tick
from backend.tools.tuner import Tuner
from backend.tools.gock_block import GockBlock
from backend.tools.dressing import Dressing
from backend.tools.cleaning import Cleaning


def create_tool_registry() -> ToolRegistry:
    """Create and populate the default tool registry."""
    registry = ToolRegistry()

    # Rehearsal tools
    registry.register("metronome", metronome_tick, {
        "name": "metronome",
        "description": "Liveness monitor — checks and reclaims stale reps",
        "input_schema": {
            "type": "object",
            "properties": {"corps_id": {"type": "string"}},
            "required": ["corps_id"],
        },
    })

    tuner = Tuner()
    registry.register("tuner", tuner.validate, {
        "name": "tuner",
        "description": "Validation tool — types, tests, schema checks",
        "input_schema": {
            "type": "object",
            "properties": {"segment_id": {"type": "string"}},
            "required": ["segment_id"],
        },
    })

    gock = GockBlock()
    registry.register("gock_block", gock.run, {
        "name": "gock_block",
        "description": "Isolated timing/performance check",
        "input_schema": {
            "type": "object",
            "properties": {"segment_id": {"type": "string"}},
            "required": ["segment_id"],
        },
    })

    dressing = Dressing()
    registry.register("dressing", dressing.check_alignment, {
        "name": "dressing",
        "description": "Alignment check with adjacent/related work",
        "input_schema": {
            "type": "object",
            "properties": {"segment_id": {"type": "string"}},
            "required": ["segment_id"],
        },
    })

    cleaning = Cleaning()
    registry.register("cleaning", cleaning.sweep, {
        "name": "cleaning",
        "description": "Quality sweep on completed artifacts",
        "input_schema": {
            "type": "object",
            "properties": {"segment_id": {"type": "string"}},
            "required": ["segment_id"],
        },
    })

    # Image generation tools (ComfyUI)
    def _generate_image(db, **kwargs):
        from backend.services.image_service import generate_image
        return generate_image(
            prompt=kwargs.get("prompt", ""),
            negative_prompt=kwargs.get("negative_prompt", ""),
            width=kwargs.get("width", 1024),
            height=kwargs.get("height", 1024),
            steps=kwargs.get("steps", 20),
            cfg_scale=kwargs.get("cfg_scale", 7.0),
            seed=kwargs.get("seed"),
        )

    registry.register("generate_image", _generate_image, {
        "name": "generate_image",
        "description": "Generate an image from a text prompt using ComfyUI/Stable Diffusion. Returns {success, output_path, error}.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Text prompt for image generation"},
                "negative_prompt": {"type": "string", "description": "Negative prompt (things to avoid)"},
                "width": {"type": "integer", "description": "Image width in pixels (default 1024)"},
                "height": {"type": "integer", "description": "Image height in pixels (default 1024)"},
                "steps": {"type": "integer", "description": "Number of diffusion steps (default 20)"},
                "cfg_scale": {"type": "number", "description": "CFG scale / guidance (default 7.0)"},
                "seed": {"type": "integer", "description": "Random seed for reproducibility"},
            },
            "required": ["prompt"],
        },
    })

    def _generate_from_workflow(db, **kwargs):
        from backend.services.image_service import generate_from_workflow
        return generate_from_workflow(
            workflow_name=kwargs.get("workflow_name", ""),
            template_vars=kwargs.get("template_vars"),
            seed=kwargs.get("seed"),
        )

    registry.register("generate_from_workflow", _generate_from_workflow, {
        "name": "generate_from_workflow",
        "description": "Generate an image using a named workflow template (e.g. show_poster, corps_logo). Returns {success, output_path, error, workflow_used}.",
        "input_schema": {
            "type": "object",
            "properties": {
                "workflow_name": {"type": "string", "description": "Workflow template name (e.g. 'show_poster', 'corps_logo')"},
                "template_vars": {"type": "object", "description": "Variables to substitute into the prompt template"},
                "seed": {"type": "integer", "description": "Random seed for reproducibility"},
            },
            "required": ["workflow_name"],
        },
    })

    # Service-layer tools (create_segment, create_rep, handoff, etc.)
    register_service_tools(registry)

    return registry


__all__ = ["create_tool_registry", "Tuner", "GockBlock", "Dressing", "Cleaning"]
