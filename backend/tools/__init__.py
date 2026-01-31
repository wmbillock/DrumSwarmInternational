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

    # Service-layer tools (create_segment, create_rep, handoff, etc.)
    register_service_tools(registry)

    return registry


__all__ = ["create_tool_registry", "Tuner", "GockBlock", "Dressing", "Cleaning"]
