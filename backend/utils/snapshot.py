"""Shared JSON snapshot parsing utilities."""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_snapshot(raw: str | None) -> dict[str, Any]:
    """Safely parse a JSON snapshot string, returning {} on failure."""
    if not raw:
        return {}
    try:
        result = json.loads(raw)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError):
        logger.debug("Failed to parse snapshot: %s", str(raw)[:200] if raw else "")
        return {}
