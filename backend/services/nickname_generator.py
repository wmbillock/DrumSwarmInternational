"""Generate names at two levels:

1. **Corps names** — whimsical fake drum & bugle corps names for the whole swarm
   e.g. "The Northwestern Topeka Cadets"

2. **Agent nicknames** — individual names for agents within a corps:
   - Staff/instructional (ED, PC, caption heads, drum major, timing judge):
     inspired by famous DCI personalities
   - Members/techs (haiku-tier workers):
     humorous corps-activity + famous musician mashups
"""

import random

# ─── Corps-level names (the whole swarm) ───────────────────────────────

_DIRECTIONS = [
    "Northern", "Southern", "Eastern", "Western", "Northwestern", "Southeastern",
    "Upper", "Lower", "Central", "Greater", "Lesser", "Inner", "Outer", "Mid",
    "North-Central", "South-Southwest", "East-Northeast", "Far Eastern",
]

_PLACES = [
    "Akron", "Topeka", "Duluth", "Peoria", "Scranton", "Fresno", "Omaha",
    "Tuscaloosa", "Kalamazoo", "Tallahassee", "Chattanooga", "Boise",
    "Pensacola", "Albuquerque", "Sheboygan", "Walla Walla", "Ypsilanti",
    "Hoboken", "Poughkeepsie", "Schenectady", "Cucamonga", "Saskatoon",
    "Woonsocket", "Pawtucket", "Terre Haute", "Fond du Lac", "Kenosha",
    "Muncie", "Oshkosh", "Bemidji", "Wichita", "Boca Raton",
]

_INSTITUTIONS = [
    "University", "Community College", "Technical Institute", "Polytechnic",
    "Academy", "Preparatory School", "Seminary", "Conservatory",
    "School of Mines", "A&M", "State", "Bible College",
]

_CORPS_TYPES = [
    "Cadets", "Crusaders", "Scouts", "Lancers", "Brigadiers", "Troopers",
    "Marauders", "Pioneers", "Vanguard", "Sentinels", "Ambassadors",
    "Cavaliers", "Guardsmen", "Grenadiers", "Musketeers", "Buccaneers",
    "Imperials", "Royales", "Colts", "Spartans", "Centurions",
    "Thunderbolts", "Stardusters", "Phantoms", "Mystics", "Bluecoats",
    "Kingsmen", "Muchachos", "Freelancers", "Velvet Knights",
    "Sky Ryders", "Sunrisers", "Bridgemen", "Blue Stars",
]


_MASCOT_ADJECTIVES = [
    "Crimson", "Golden", "Silver", "Emerald", "Midnight", "Scarlet",
    "Cobalt", "Blazing", "Iron", "Phantom", "Thunder", "Silent",
    "Royal", "Soaring", "Burning", "Frozen", "Steel", "Shadow",
]

_MASCOT_ANIMALS = [
    "Hawks", "Eagles", "Wolves", "Lions", "Stallions", "Falcons",
    "Dragons", "Panthers", "Vipers", "Griffins", "Phoenixes", "Ravens",
    "Mustangs", "Jaguars", "Serpents", "Titans", "Spartans", "Knights",
]


def generate_mascot(existing: set[str] | None = None) -> str:
    """Generate a unique mascot name, e.g. 'The Crimson Hawks'."""
    used = existing or set()
    for _ in range(200):
        adj = random.choice(_MASCOT_ADJECTIVES)
        animal = random.choice(_MASCOT_ANIMALS)
        name = f"The {adj} {animal}"
        if name not in used:
            return name
    return f"The {random.choice(_MASCOT_ANIMALS)} #{random.randint(1, 99)}"


def generate_corps_name(existing: set[str] | None = None) -> str:
    """Generate a unique whimsical fake drum corps name for a show swarm.

    Examples: 'The Northwestern Topeka Cadets', 'The Greater Ypsilanti Crusaders'
    """
    used = existing or set()
    for _ in range(200):
        direction = random.choice(_DIRECTIONS)
        place = random.choice(_PLACES)
        if random.random() < 0.3:
            inst = random.choice(_INSTITUTIONS)
            name = f"The {direction} {place} {inst} {random.choice(_CORPS_TYPES)}"
        else:
            name = f"The {direction} {place} {random.choice(_CORPS_TYPES)}"
        if name not in used:
            return name
    return f"The {random.choice(_PLACES)} All-Stars #{random.randint(1, 99)}"


# ─── Staff nicknames (admin & instructional roles) ────────────────────
# Inspired by famous DCI personalities — directors, arrangers, designers,
# judges, and legends of the drum corps activity.

_STAFF_FIRST_NAMES = [
    # Inspired by real DCI luminaries (names are fictional composites)
    "George", "Fred", "Jim", "Bobby", "Wayne", "Dennis",
    "Michael", "Tom", "Gary", "Don", "Garfield", "Ralph",
    "Thom", "Jay", "Scott", "Mark", "David", "Paul",
    "Gene", "Harold", "Gail", "Lou", "Brandt", "Will",
]

_STAFF_LAST_NAMES = [
    # Fictional but evocative of the activity
    "Zingali", "Bocook", "Ottavio", "Rennick", "Downfield",
    "Vanderkolff", "Brasswell", "Hornsby", "Cadenza", "Fortissimo",
    "Crescendo", "DaCapperton", "Sfortzando", "Marcato", "Staccato",
    "Fermata", "Rubato", "Tenuto", "Vivace", "Maestoso",
    "Allegretti", "Cantabile", "Risoluto", "Grandioso",
]

# Role-specific titles that get prepended
_STAFF_TITLES = {
    "executive_director": "Director",
    "program_coordinator": "Coordinator",
    "drill_writer": "Drill Designer",
    "music_writer": "Arranger",
    "choreographer": "Choreographer",
    "brass_caption_head": "Caption Head",
    "percussion_caption_head": "Caption Head",
    "guard_caption_head": "Caption Head",
    "visual_caption_head": "Caption Head",
    "drum_major": "Drum Major",
    "timing_judge": "Judge",
}

_STAFF_ROLES = set(_STAFF_TITLES.keys())


# ─── Member nicknames (techs / worker agents) ─────────────────────────
# Humorous mashups of corps activity terms + famous musicians/composers

_CORPS_TERMS = [
    "Tick", "Box 5", "Backfield", "Hash", "Contra", "Pit",
    "Mello", "Snare", "Tenor", "Baritone", "Sousaphone",
    "Marimba", "Vibes", "Cymbal", "Flugelhorn", "Bugle",
    "Ratchet", "Gock Block", "Diddle", "Flam", "Paradiddle",
    "Rimshot", "Buzz Roll", "Drag", "Ratamacue", "Crossover",
    "Double Beat", "Step Two", "Fadeout", "Aux Perc", "Synth Pad",
    "Park and Blow", "Company Front", "Pinwheel", "Follow the Leader",
    "Scatter Drill", "Chair Step", "Mark Time", "Horns Up",
    "Slide", "To the Box", "Gate Turn", "Ripple",
]

_FAMOUS_MUSICIANS = [
    "Mozart", "Beethoven", "Bach", "Vivaldi", "Chopin",
    "Liszt", "Brahms", "Tchaikovsky", "Debussy", "Ravel",
    "Stravinsky", "Copland", "Bernstein", "Gershwin", "Sousa",
    "Holst", "Grainger", "Ellington", "Basie", "Gillespie",
    "Coltrane", "Parker", "Miles", "Mingus", "Monk",
    "Maynard", "Buddy Rich", "Elvin Jones", "Art Blakey",
    "Marsalis", "Sandoval", "Doc Severinsen", "Rafael Méndez",
    "Yo-Yo Ma", "Paganini", "Heifetz", "Itzhak",
]


def generate_nickname(role: str, existing: set[str] | None = None) -> str:
    """Generate a unique nickname for an individual agent.

    Staff roles get DCI-personality-inspired names.
    Member/tech roles get corps-term + musician mashup names.
    """
    used = existing or set()

    if role in _STAFF_ROLES:
        return _generate_staff_name(role, used)
    else:
        return _generate_member_name(used)


def _generate_staff_name(role: str, used: set[str]) -> str:
    """e.g. 'Director George Zingali', 'Caption Head Thom Crescendo'"""
    title = _STAFF_TITLES.get(role, "Staff")
    for _ in range(200):
        first = random.choice(_STAFF_FIRST_NAMES)
        last = random.choice(_STAFF_LAST_NAMES)
        name = f"{title} {first} {last}"
        if name not in used:
            return name
    return f"{title} #{random.randint(1, 99)}"


def _generate_member_name(used: set[str]) -> str:
    """e.g. 'Tick Box Mozart', 'Backfield Beethoven', 'Paradiddle Coltrane'"""
    for _ in range(200):
        term = random.choice(_CORPS_TERMS)
        musician = random.choice(_FAMOUS_MUSICIANS)
        name = f"{term} {musician}"
        if name not in used:
            return name
    return f"Member #{random.randint(1, 99)}"
