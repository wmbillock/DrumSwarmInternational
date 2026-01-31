"""Note routing — keyword-based tagger for design notes."""

import re
from typing import List

TAG_KEYWORDS: dict[str, list[str]] = {
    "music": [
        "tempo", "bpm", "key signature", "brass", "percussion", "woodwind",
        "melody", "chord", "dynamics", "crescendo", "decrescendo", "forte",
        "piano", "measure", "beat", "instrument", "horn", "drum", "marimba",
        "pit", "front ensemble", "battery", "music",
    ],
    "visual": [
        "drill", "formation", "set", "transition", "spacing", "step size",
        "march", "visual", "hash", "yard line", "staging", "block", "scatter",
        "follow-the-leader",
    ],
    "guard": [
        "guard", "flag", "rifle", "sabre", "toss", "catch", "silk",
        "color guard", "equipment", "spin",
    ],
    "ge": [
        "ge", "general effect", "audience", "impact", "emotion", "story",
        "narrative", "theme", "arc", "pacing", "energy",
    ],
    "admin": [
        "budget", "schedule", "deadline", "travel", "logistics", "roster",
        "staffing", "uniform", "prop", "admin",
    ],
}

# Pre-compile patterns: sort keywords longest-first so multi-word phrases match before single words
_TAG_PATTERNS: dict[str, re.Pattern] = {
    tag: re.compile(
        r"\b(?:" + "|".join(re.escape(kw) for kw in sorted(keywords, key=len, reverse=True)) + r")\b",
        re.IGNORECASE,
    )
    for tag, keywords in TAG_KEYWORDS.items()
}


def route_note(text: str) -> List[str]:
    """Return sorted list of tags matching the given note text."""
    tags: list[str] = []
    for tag, pattern in _TAG_PATTERNS.items():
        if pattern.search(text):
            tags.append(tag)
    if "?" in text:
        tags.append("questions")
    if not tags:
        tags.append("admin")
    return sorted(tags)
