"""V1 API router — backward-compatibility shim.

All routes have been split into domain-specific modules.
This module re-exports helpers for test monkeypatching compatibility.
"""

# Re-export helpers that tests monkeypatch via "backend.api.v1.router._get_db_session"
from backend.api.v1.helpers import (  # noqa: F401
    _get_root,
    _validate_id,
    _get_db_session,
    _get_llm_client,
    _llm_chat,
    _slugify,
    _shows_dir,
    _validate_slug,
    _show_dir,
    _generate_color_scheme,
    _parse_competition_id,
)
