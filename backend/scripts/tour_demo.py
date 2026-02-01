"""Deterministic end-to-end lifecycle tour.

Runs pool init → commission corps → draft → create/approve show →
contest(s) → standings → reputation → decay → recap.

All outputs are deterministic given (seed, seasons, corps_count).
No LLM calls, no DB access — pure filesystem operations.
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import yaml

from backend.models.score import JudgeType
from backend.services.corps_persistence import create_corps, load_roster, update_corps_state
from backend.services.drafting import RoleRequirement, execute_draft
from backend.services.reputation import (
    apply_season_decay,
    record_corps_placement,
    release_agent,
    update_reputations,
)
from backend.services.scoring_engine import compute_standings
from backend.services.scoring_service import CompositeScore, DEFAULT_WEIGHTS
from backend.services.season_persistence import create_season, register_corps
from backend.services.show_persistence import update_status
from backend.services.yaml_util import atomic_write, safe_dump_yaml


# -- Fixture generation (deterministic from seed) ---------------------------

INSTRUMENTS = ["brass", "percussion", "guard", "visual", "general_effect"]
SPECIALTIES_BY_INSTRUMENT = {
    "brass": ["jazz", "classical", "fanfare"],
    "percussion": ["rudimental", "mallet", "electronic"],
    "guard": ["rifle", "sabre", "flag"],
    "visual": ["drill", "choreography", "staging"],
    "general_effect": ["arrangement", "composition", "pacing"],
}


def _seed_int(seed: int, *parts: str) -> int:
    """Deterministic integer from seed + string parts."""
    data = f"{seed}:" + ":".join(parts)
    return int(hashlib.sha256(data.encode()).hexdigest()[:8], 16)


def _generate_agents(seed: int, corps_count: int) -> list[dict]:
    """Generate enough agents to fill all corps rosters.

    Each corps needs one agent per instrument (5 roles).
    We generate corps_count * 5 agents to ensure the draft succeeds.
    """
    agents = []
    for i in range(corps_count * len(INSTRUMENTS)):
        instrument = INSTRUMENTS[i % len(INSTRUMENTS)]
        idx = i // len(INSTRUMENTS)
        agent_id = f"agent-{instrument[:3]}-{idx:02d}"
        h = _seed_int(seed, "agent", agent_id)
        specialties_pool = SPECIALTIES_BY_INSTRUMENT[instrument]
        specialty = specialties_pool[h % len(specialties_pool)]
        agents.append({
            "agent_id": agent_id,
            "display_name": f"{instrument.title()} {idx}",
            "primary_instrument": instrument,
            "availability": "active",
            "trust_score": 50.0 + (h % 20),
            "total_sessions": 0,
            "successful_sessions": 0,
            "failed_sessions": 0,
            "experience_seasons": (h % 3),
            "specialties": [specialty],
            "seen_sessions": [],
        })
    return agents


def _generate_corps_names(seed: int, count: int) -> list[str]:
    """Deterministic corps IDs."""
    base_names = [
        "bluecoats", "cavaliers", "phantoms", "cadets", "crusaders",
        "scouts", "troopers", "vanguard", "pioneers", "regiment",
    ]
    names = []
    for i in range(count):
        h = _seed_int(seed, "corps", str(i))
        name = base_names[h % len(base_names)]
        # Ensure uniqueness
        candidate = name
        suffix = 2
        while candidate in names:
            candidate = f"{name}-{suffix}"
            suffix += 1
        names.append(candidate)
    return names


# -- Pool setup -------------------------------------------------------------

def _write_pool(pool_dir: Path, agents: list[dict]) -> None:
    """Write ledger.yaml and per-agent YAML files."""
    pool_dir.mkdir(parents=True, exist_ok=True)
    agents_dir = pool_dir / "agents"
    agents_dir.mkdir(exist_ok=True)
    ledger = {
        "agents": [
            {
                "agent_id": a["agent_id"],
                "display_name": a["display_name"],
                "primary_instrument": a["primary_instrument"],
                "availability": a["availability"],
                "trust_score": a["trust_score"],
            }
            for a in agents
        ]
    }
    atomic_write(pool_dir / "ledger.yaml", safe_dump_yaml(ledger))
    for a in agents:
        atomic_write(agents_dir / f"{a['agent_id']}.yaml", safe_dump_yaml(a))


# -- Stub scoring (deterministic) -------------------------------------------

def _stub_caption_scores(corps_id: str, show_slug: str, seed: int) -> dict:
    """Deterministic scores per caption, seeded from corps_id + show_slug + seed."""
    scores = {}
    for jtype in [JudgeType.BRASS, JudgeType.PERCUSSION, JudgeType.GUARD,
                  JudgeType.VISUAL, JudgeType.GENERAL_EFFECT]:
        h = hashlib.sha256(
            f"{seed}:{corps_id}:{show_slug}:{jtype.value}".encode()
        ).hexdigest()
        scores[jtype] = (int(h[:8], 16) % 30) + 60  # 60-89
    return scores


# -- Main tour function -----------------------------------------------------

def run_deterministic_tour(
    root: Path,
    seed: int = 1,
    seasons: int = 1,
    corps_count: int = 2,
) -> str:
    """Run the full tour. Returns recap markdown string.

    All operations are filesystem-only, deterministic, and idempotent
    for a given (root, seed, seasons, corps_count).
    """
    root = Path(root)
    pool_dir = root / "talent_pool"
    corps_base = root / "corps"

    recap_lines = [
        f"# Tour Recap (seed={seed}, seasons={seasons}, corps={corps_count})",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    # 1. Init talent pool
    agents = _generate_agents(seed, corps_count)
    _write_pool(pool_dir, agents)
    recap_lines.append(f"## Pool: {len(agents)} agents initialized")
    recap_lines.append("")

    # 2. Commission corps and draft rosters
    corps_names = _generate_corps_names(seed, corps_count)
    draft_results = {}
    for cname in corps_names:
        corps_dir = corps_base / cname
        if not (corps_dir / "corps.yaml").exists():
            create_corps(corps_dir, {
                "corps_id": cname,
                "display_name": cname.replace("-", " ").title(),
                "philosophy": f"Seed-{seed} philosophy",
                "state": "commissioned",
            })
            update_corps_state(corps_dir, "active")

        requirements = [RoleRequirement(inst, 1) for inst in INSTRUMENTS]
        result = execute_draft(cname, requirements, pool_dir, corps_dir)
        draft_results[cname] = result
        recap_lines.append(f"### Corps: {cname}")
        recap_lines.append(f"  Drafted: {[a['agent_id'] for a in result.assignments]}")
        recap_lines.append("")

    # 3. Create and approve show
    show_slug = f"tour-show-s{seed}"
    show_dir = root / "shows" / show_slug
    if not show_dir.exists():
        show_dir.mkdir(parents=True)
        atomic_write(show_dir / "status.yaml", safe_dump_yaml({"status": "draft"}))
        atomic_write(show_dir / "design_notes.md", f"# {show_slug}\n\nDeterministic demo show.\n")
        atomic_write(show_dir / "show_prompt.md", f"# Show Prompt: {show_slug}\n\nGenerated for tour seed {seed}.\n")
    update_status(show_dir, "approved")
    recap_lines.append(f"## Show: {show_slug} (approved)")
    recap_lines.append("")

    # 4. Run seasons
    for s_idx in range(1, seasons + 1):
        season_id = f"tour-s{s_idx}"
        season_dir = root / "seasons" / season_id
        if not season_dir.exists():
            create_season(root, season_id, metadata={"season_id": season_id, "seed": seed})

        # Register all corps
        for cname in corps_names:
            register_corps(season_dir, cname, corps_base)

        # Build composites
        composites = {}
        for cname in corps_names:
            caption_scores = _stub_caption_scores(cname, show_slug, seed + s_idx - 1)
            raw_total = sum(caption_scores[jt] * DEFAULT_WEIGHTS[jt] for jt in caption_scores)
            composites[cname] = CompositeScore(
                caption_scores=caption_scores,
                raw_total=raw_total,
                penalties_total=0.0,
                final_score=raw_total,
                needs_rework=False,
                needs_escalation=False,
            )

        standings = compute_standings(season_id, DEFAULT_WEIGHTS, composites)

        # Write standings.yaml
        standings_data = {
            "season_id": standings.season_id,
            "generated_at": standings.generated_at,
            "results": [
                {
                    "corps_id": r.corps_id,
                    "rank": r.rank,
                    "final_score": r.final_score,
                    "raw_score": r.raw_score,
                    "caption_scores": {jt.value: v for jt, v in r.caption_scores.items()},
                }
                for r in standings.results
            ],
        }
        atomic_write(season_dir / "standings.yaml", safe_dump_yaml(standings_data))

        # Write per-corps scores.yaml
        for cname in corps_names:
            composite = composites[cname]
            scores_data = {
                "corps_id": cname,
                "show_slug": show_slug,
                "caption_scores": {jt.value: v for jt, v in composite.caption_scores.items()},
                "raw_total": composite.raw_total,
                "final_score": composite.final_score,
            }
            perf_dir = season_dir / "performances" / cname
            atomic_write(perf_dir / "scores.yaml", safe_dump_yaml(scores_data))

        # Record corps placement
        for r in standings.results:
            corps_dir = corps_base / r.corps_id
            record_corps_placement(corps_dir, season_id, r.rank, r.final_score)

        # Update reputations
        roster_map = {}
        for cname in corps_names:
            roster = load_roster(corps_base / cname)
            roster_map[cname] = [a["agent_id"] for a in roster.get("assignments", [])]

        session_id = f"{season_id}-{show_slug}"
        update_reputations(standings, pool_dir, roster_map, session_id=session_id)

        recap_lines.append(f"## Season {season_id}")
        for r in standings.results:
            recap_lines.append(f"  #{r.rank} {r.corps_id}: {r.final_score:.2f}")
        recap_lines.append("")

        # Release agents back to pool between seasons
        for cname in corps_names:
            roster = load_roster(corps_base / cname)
            for a in roster.get("assignments", []):
                release_agent(pool_dir, a["agent_id"])

        # Offseason decay if more seasons remain
        if s_idx < seasons:
            apply_season_decay(pool_dir)
            recap_lines.append(f"  (offseason decay applied)")
            recap_lines.append("")

    # 5. Final agent summary
    recap_lines.append("## Final Agent Trust Scores")
    for agent in agents:
        agent_path = pool_dir / "agents" / f"{agent['agent_id']}.yaml"
        if agent_path.exists():
            data = yaml.safe_load(agent_path.read_text())
            recap_lines.append(
                f"  {data['agent_id']}: trust={data['trust_score']:.4f} "
                f"sessions={data.get('total_sessions', 0)}"
            )
    recap_lines.append("")

    # 6. Write recap artifact
    recap_text = "\n".join(recap_lines)
    docs_dir = root / "docs" / "outputs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    recap_path = docs_dir / f"tour_seed{seed}.md"
    atomic_write(recap_path, recap_text)

    return recap_text
