"""Generate friendly nicknames for agents."""

import random

_ADJECTIVES = [
    "Swift", "Bold", "Keen", "Calm", "Sage", "Deft", "Warm", "True",
    "Bright", "Sharp", "Quick", "Steady", "Noble", "Vivid", "Clear",
    "Grand", "Prime", "Loyal", "Brave", "Wise", "Fair", "Glad",
    "Crisp", "Fresh", "Pure", "Firm", "Fine", "Neat", "Cool", "Zen",
]

_NOUNS = [
    "Phoenix", "Falcon", "Osprey", "Wren", "Heron", "Finch", "Lark",
    "Cedar", "Maple", "Birch", "Aspen", "Oak", "Pine", "Elm", "Ivy",
    "Flint", "Onyx", "Jade", "Opal", "Ruby", "Pearl", "Amber",
    "Atlas", "Echo", "Nova", "Pulse", "Drift", "Spark", "Blaze",
    "Ridge", "Brook", "Tide", "Storm", "Frost", "Dune", "Cliff",
]


def generate_nickname(role: str, existing: set[str] | None = None) -> str:
    """Generate a unique friendly nickname like 'Swift Phoenix'."""
    used = existing or set()
    for _ in range(100):
        name = f"{random.choice(_ADJECTIVES)} {random.choice(_NOUNS)}"
        if name not in used:
            return name
    # Fallback with number
    return f"{random.choice(_ADJECTIVES)} {random.choice(_NOUNS)} {random.randint(1, 99)}"
