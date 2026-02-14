"""Model spec seeder — creates default ModelSpec rows for known LLM providers.

Called alongside seed_founding_corps() on startup.
Idempotent: skips specs where provider+model_id already exist.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.model_spec import ModelSpec

logger = logging.getLogger(__name__)

# Default model specs to seed.  Each entry: (name, provider, model_id, categories)
DEFAULT_SPECS: list[tuple[str, str, str, str]] = [
    (
        "claude-opus-4-5",
        "anthropic",
        "claude-opus-4-5-20250929",
        "architecture,documentation,complex_reasoning",
    ),
    (
        "claude-sonnet-4-5",
        "anthropic",
        "claude-sonnet-4-5-20250929",
        "general,frontend,backend",
    ),
    (
        "claude-haiku-4-5",
        "anthropic",
        "claude-haiku-4-5-20251001",
        "general,testing,quick_tasks",
    ),
    (
        "deepseek-coder-v2",
        "ollama",
        "deepseek-coder-v2:16b",
        "backend,frontend,testing",
    ),
    (
        "qwen2.5-coder",
        "ollama",
        "qwen2.5-coder:7b",
        "frontend,backend",
    ),
]


def _is_ollama_available() -> bool:
    """Quick check: can we reach the Ollama API?"""
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2):
            return True
    except Exception:
        return False


def seed_default_specs(db: Session, check_ollama: bool = True) -> list[ModelSpec]:
    """Create ModelSpec rows for known models.

    Idempotent — skips any spec whose provider+model_id already exists.
    Ollama specs are only created when the Ollama API is reachable
    (override with check_ollama=False for testing).

    Returns list of newly created specs.
    """
    ollama_ok: Optional[bool] = None
    created: list[ModelSpec] = []

    for name, provider, model_id, categories in DEFAULT_SPECS:
        # Lazy-check Ollama availability only once
        if provider == "ollama" and check_ollama:
            if ollama_ok is None:
                ollama_ok = _is_ollama_available()
            if not ollama_ok:
                logger.debug("Skipping ollama spec %s — Ollama not reachable", name)
                continue

        existing = (
            db.query(ModelSpec)
            .filter(
                ModelSpec.provider == provider,
                ModelSpec.model_id == model_id,
            )
            .first()
        )
        if existing:
            continue

        spec = ModelSpec(
            name=name,
            provider=provider,
            model_id=model_id,
            task_categories=categories,
        )
        db.add(spec)
        created.append(spec)
        logger.info("Seeded model spec: %s (%s/%s)", name, provider, model_id)

    if created:
        db.commit()
        logger.info("Seeded %d model specs", len(created))
    else:
        logger.info("All default model specs already exist")

    return created
