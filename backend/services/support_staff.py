"""Support staff agent definitions and lifecycle engines:
- Souvie Crew: artifact/deliverable management
- Accountant: budget/token cost tracking
- Board of Directors: multi-project governance
- Housing Coordinator: infrastructure/resource management
"""

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.agent_definition import AgentDefinition, ModelTier
from backend.services.agent_lifecycle import create_definition, spawn_session


# Support staff role definitions
SUPPORT_STAFF_ROLES = {
    "souvie_crew": {
        "system_prompt": (
            "You are the Souvie Crew. You manage artifacts and deliverables "
            "for the audience (user). You collect, organize, and present "
            "completed work products."
        ),
        "model_tier": ModelTier.HAIKU,
        "tools_allowed": ["cleaning", "dressing"],
    },
    "accountant": {
        "system_prompt": (
            "You are the Accountant. You track budget, token costs, and "
            "resource spend per caption and corps. You report on financial "
            "health and flag overruns."
        ),
        "model_tier": ModelTier.HAIKU,
        "tools_allowed": [],
    },
    "board_of_directors": {
        "system_prompt": (
            "You are the Board of Directors. You oversee multiple corps "
            "and projects. You make governance decisions and ensure "
            "cross-project alignment."
        ),
        "model_tier": ModelTier.OPUS,
        "tools_allowed": [],
    },
    "housing_coordinator": {
        "system_prompt": (
            "You are the Housing Coordinator. You manage infrastructure "
            "and resource allocation for the corps. You handle compute, "
            "storage, and environment provisioning."
        ),
        "model_tier": ModelTier.HAIKU,
        "tools_allowed": [],
    },
}


def create_support_staff_definitions(
    db: Session, corps_id: str
) -> dict[str, AgentDefinition]:
    """Create all support staff definitions for a corps."""
    definitions = {}
    for role, config in SUPPORT_STAFF_ROLES.items():
        defn = create_definition(
            db,
            role=role,
            system_prompt=config["system_prompt"],
            model_tier=config["model_tier"],
            tools_allowed=config["tools_allowed"],
            corps_id=corps_id,
        )
        definitions[role] = defn
    return definitions


def spawn_support_staff(
    db: Session, corps_id: str, definitions: dict[str, AgentDefinition]
) -> dict[str, "AgentSession"]:
    """Spawn sessions for all support staff from their definitions."""
    from backend.models.agent_session import AgentSession

    sessions = {}
    for role, defn in definitions.items():
        session = spawn_session(db, definition_id=defn.id, corps_id=corps_id)
        sessions[role] = session
    return sessions
