"""Note routing — keyword-based tagger for design notes.

Tags serve as metadata for messages. In the DSI swarm, "shows" are software
features/tasks, so keywords span both DCI metaphor and software engineering.
"""

import re
from typing import List

TAG_KEYWORDS: dict[str, list[str]] = {
    "architecture": [
        # Software: backend, data, APIs
        "api", "endpoint", "route", "model", "schema", "database", "migration",
        "service", "backend", "data flow", "data model", "orm", "query",
        "sqlalchemy", "fastapi", "rest", "websocket", "authentication", "auth",
        # DCI metaphor (music = composition/architecture)
        "tempo", "bpm", "key signature", "brass", "percussion", "melody",
        "chord", "dynamics", "music",
    ],
    "interface": [
        # Software: frontend, UI, UX
        "frontend", "component", "page", "react", "typescript", "css", "layout",
        "button", "form", "input", "modal", "tab", "panel", "sidebar",
        "responsive", "mobile", "ui", "ux", "user interface", "user experience",
        "navigation", "routing", "state management", "hook",
        # DCI metaphor (drill = formations/visual flow)
        "drill", "formation", "visual", "staging", "transition", "spacing",
    ],
    "quality": [
        # Software: testing, QA, edge cases
        "test", "testing", "edge case", "edge cases", "error", "bug", "fix", "validation",
        "integration", "e2e", "unit test", "pytest", "vitest", "coverage",
        "regression", "failure", "exception", "guard", "safety", "security",
        # DCI metaphor (guard = precision/quality)
        "guard", "flag", "rifle", "sabre", "choreographer",
    ],
    "ge": [
        # General effect / user impact
        "ge", "general effect", "audience", "impact", "emotion", "story",
        "narrative", "theme", "arc", "pacing", "energy", "user experience",
        "usability", "accessibility", "performance", "speed",
    ],
    "admin": [
        # Project management
        "budget", "schedule", "deadline", "travel", "logistics", "roster",
        "staffing", "uniform", "prop", "admin", "priority", "scope",
        "milestone", "blocker", "dependency", "timeline",
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
