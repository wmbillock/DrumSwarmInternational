"""Corps configuration service — manage per-corps LLM and methodology settings."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.corps_config import CorpsConfig

logger = logging.getLogger(__name__)


def get_config(db: Session, corps_id: str) -> Optional[CorpsConfig]:
    """Get configuration for a corps."""
    return db.get(CorpsConfig, corps_id)


def get_or_create_config(db: Session, corps_id: str) -> CorpsConfig:
    """Get config for a corps, creating a default if none exists."""
    config = db.get(CorpsConfig, corps_id)
    if config is None:
        config = CorpsConfig(corps_id=corps_id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def update_config(
    db: Session,
    corps_id: str,
    llm_provider: Optional[str] = None,
    llm_model_override: Optional[str] = None,
    methodology: Optional[str] = None,
    architecture_style: Optional[str] = None,
    coding_style: Optional[str] = None,
    extra: Optional[dict] = None,
) -> CorpsConfig:
    """Update a corps' configuration."""
    config = get_or_create_config(db, corps_id)

    if llm_provider is not None:
        config.llm_provider = llm_provider
    if llm_model_override is not None:
        config.llm_model_override = llm_model_override
    if methodology is not None:
        config.methodology = methodology
    if architecture_style is not None:
        config.architecture_style = architecture_style
    if coding_style is not None:
        config.coding_style = coding_style
    if extra is not None:
        config.extra = extra

    db.commit()
    db.refresh(config)
    return config


def list_configs(db: Session) -> list[CorpsConfig]:
    """List all corps configurations."""
    return db.query(CorpsConfig).all()


def config_to_dict(config: CorpsConfig) -> dict:
    """Serialize a CorpsConfig to a dict."""
    return {
        "corps_id": config.corps_id,
        "llm_provider": config.llm_provider,
        "llm_model_override": config.llm_model_override,
        "methodology": config.methodology,
        "architecture_style": config.architecture_style,
        "coding_style": config.coding_style,
        "extra": config.extra,
    }
