"""Achievement catalog loader for caption awards."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


CATALOG_PATH = Path(__file__).resolve().parents[1] / "config" / "awards" / "caption_awards.yaml"


@dataclass(frozen=True)
class AchievementTrigger:
    metric: str
    op: str
    value: float
    caption: str | None = None
    min_reps_completed: int | None = None
    min_total_sessions: int | None = None
    min_success_rate: float | None = None


@dataclass(frozen=True)
class AchievementDefinition:
    id: str
    category: str
    tier: str
    scope: str
    name: str
    description: str
    trigger: AchievementTrigger


def _load_yaml() -> dict[str, Any]:
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"Achievement catalog not found at {CATALOG_PATH}")
    with CATALOG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _parse_trigger(data: dict[str, Any]) -> AchievementTrigger:
    return AchievementTrigger(
        metric=str(data.get("metric", "")),
        op=str(data.get("op", ">=")),
        value=float(data.get("value", 0)),
        caption=data.get("caption"),
        min_reps_completed=data.get("min_reps_completed"),
        min_total_sessions=data.get("min_total_sessions"),
        min_success_rate=data.get("min_success_rate"),
    )


def _parse_achievement(entry: dict[str, Any]) -> AchievementDefinition:
    trigger = _parse_trigger(entry.get("trigger", {}))
    return AchievementDefinition(
        id=str(entry.get("id", "")),
        category=str(entry.get("category", "")),
        tier=str(entry.get("tier", "")),
        scope=str(entry.get("scope", "")),
        name=str(entry.get("name", "")),
        description=str(entry.get("description", "")),
        trigger=trigger,
    )


@lru_cache(maxsize=1)
def load_achievement_catalog() -> list[AchievementDefinition]:
    """Load the caption award catalog from YAML."""
    data = _load_yaml()
    raw_entries = data.get("achievements", [])
    return [_parse_achievement(entry) for entry in raw_entries]


def clear_catalog_cache() -> None:
    load_achievement_catalog.cache_clear()
