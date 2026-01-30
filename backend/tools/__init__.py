"""DCI Swarm — Rehearsal Tools.

Registers all tools in a shared ToolRegistry for use by agent sessions.
"""

from backend.services.tool_executor import ToolRegistry
from backend.tools.metronome import tick as metronome_tick
from backend.tools.tuner import Tuner
from backend.tools.gock_block import GockBlock
from backend.tools.dressing import Dressing
from backend.tools.cleaning import Cleaning


def create_tool_registry() -> ToolRegistry:
    """Create and populate the default tool registry."""
    registry = ToolRegistry()

    registry.register("metronome", metronome_tick, {
        "name": "metronome",
        "description": "Liveness monitor — checks and reclaims stale reps",
        "parameters": {"corps_id": {"type": "string"}},
    })

    # Class-based tools — register their primary methods
    tuner = Tuner()
    registry.register("tuner", tuner.validate, {
        "name": "tuner",
        "description": "Validation tool — types, tests, schema checks",
        "parameters": {"coordinate_id": {"type": "string"}},
    })

    gock = GockBlock()
    registry.register("gock_block", gock.run, {
        "name": "gock_block",
        "description": "Isolated timing/performance check",
        "parameters": {"coordinate_id": {"type": "string"}},
    })

    dressing = Dressing()
    registry.register("dressing", dressing.check_alignment, {
        "name": "dressing",
        "description": "Alignment check with adjacent/related work",
        "parameters": {"coordinate_id": {"type": "string"}},
    })

    cleaning = Cleaning()
    registry.register("cleaning", cleaning.sweep, {
        "name": "cleaning",
        "description": "Quality sweep on completed artifacts",
        "parameters": {"coordinate_id": {"type": "string"}},
    })

    return registry


__all__ = ["create_tool_registry", "Tuner", "GockBlock", "Dressing", "Cleaning"]
