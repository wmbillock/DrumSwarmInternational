"""V1 API — Scoreboards router (placeholder).

Scoreboard endpoints currently live in metrics.py. This module exists
as an extension point for dedicated scoreboard features.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["scoreboards"])
