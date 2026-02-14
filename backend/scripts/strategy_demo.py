"""Strategy evolution demo — full feedback loop.

Seeds model specs and corps with different strategies, runs a simulated
season, computes standings, generates strategy evolution proposals, applies
them, and prints a before/after summary.

Uses DB for strategy/spec/performance tracking + filesystem for seasons/shows.
No live LLM calls required — mock performance data simulates the results.
"""

import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
import backend.models  # noqa: F401 — register all models

from backend.models.corps import Corps
from backend.models.corps_strategy import CorpsStrategy, ModelPolicy
from backend.models.model_spec import ModelSpec
from backend.models.score import JudgeType
from backend.services.model_spec_service import (
    get_spec_leaderboard,
    record_model_spec_outcome,
)
from backend.services.offseason_proposals import (
    apply_proposals,
    create_proposals_file,
    load_proposals,
)
from backend.services.scoring_engine import compute_standings
from backend.services.scoring_service import CompositeScore, DEFAULT_WEIGHTS
from backend.services.season_persistence import create_season
from backend.services.strategy_evolution import generate_strategy_proposals
from backend.services.yaml_util import atomic_write, safe_dump_yaml


# -- Corps definitions --------------------------------------------------------

CORPS_DEFS = [
    {
        "id": "quiet-trumpets",
        "name": "The Quiet Trumpets",
        "policy": "single_provider",
        "provider": "anthropic",
        "exploration": 0.05,
        "risk": 0.3,
    },
    {
        "id": "pit-happens",
        "name": "Pit Happens",
        "policy": "best_of_breed",
        "provider": None,
        "exploration": 0.15,
        "risk": 0.6,
    },
    {
        "id": "toss-and-pray",
        "name": "Toss And Pray",
        "policy": "random_exploration",
        "provider": None,
        "exploration": 0.4,
        "risk": 0.9,
    },
]

# -- Spec definitions ---------------------------------------------------------

SPEC_DEFS = [
    # Anthropic — good at backend, mediocre at frontend
    {
        "name": "claude-sonnet-4-5",
        "provider": "anthropic",
        "model_id": "claude-sonnet-4-5-20250929",
        "categories": "frontend,backend,testing,general",
    },
    # Ollama — great at frontend, weak at backend
    {
        "name": "deepseek-coder-v2",
        "provider": "ollama",
        "model_id": "deepseek-coder-v2:16b",
        "categories": "frontend,backend,testing,general",
    },
    # OpenAI — balanced
    {
        "name": "gpt-4o",
        "provider": "openai",
        "model_id": "gpt-4o",
        "categories": "frontend,backend,testing,general",
    },
]

# Simulated global performance (spec_name → category → avg_score)
SIMULATED_SCORES = {
    "claude-sonnet-4-5": {
        "frontend": 72.0,
        "backend": 91.0,
        "testing": 84.0,
    },
    "deepseek-coder-v2": {
        "frontend": 93.0,
        "backend": 65.0,
        "testing": 78.0,
    },
    "gpt-4o": {
        "frontend": 82.0,
        "backend": 80.0,
        "testing": 86.0,
    },
}

# Simulated per-corps performance adjustments
# (corps_id → category → score delta from the spec they used)
CORPS_ADJUSTMENTS = {
    "quiet-trumpets": {"frontend": -8.0, "backend": 2.0, "testing": -3.0},
    "pit-happens": {"frontend": 3.0, "backend": 1.0, "testing": 2.0},
    "toss-and-pray": {"frontend": -5.0, "backend": -10.0, "testing": -7.0},
}

# Competition caption scores (deterministic)
CORPS_CAPTION_SCORES = {
    "quiet-trumpets": {
        JudgeType.BRASS: 70.0,
        JudgeType.PERCUSSION: 68.0,
        JudgeType.GUARD: 65.0,
        JudgeType.VISUAL: 72.0,
        JudgeType.GENERAL_EFFECT: 74.0,
        JudgeType.ENSEMBLE_TECHNIQUE: 69.0,
    },
    "pit-happens": {
        JudgeType.BRASS: 88.0,
        JudgeType.PERCUSSION: 90.0,
        JudgeType.GUARD: 85.0,
        JudgeType.VISUAL: 82.0,
        JudgeType.GENERAL_EFFECT: 91.0,
        JudgeType.ENSEMBLE_TECHNIQUE: 87.0,
    },
    "toss-and-pray": {
        JudgeType.BRASS: 60.0,
        JudgeType.PERCUSSION: 55.0,
        JudgeType.GUARD: 58.0,
        JudgeType.VISUAL: 62.0,
        JudgeType.GENERAL_EFFECT: 64.0,
        JudgeType.ENSEMBLE_TECHNIQUE: 57.0,
    },
}


def _header(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}")


def _subheader(text: str) -> None:
    print(f"\n--- {text} ---")


def run_strategy_demo(root: Path) -> str:
    """Run the full strategy evolution demo. Returns recap text."""
    root = Path(root)

    # -- Setup DB (in-memory for demo) --
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    recap_lines = [
        "# Strategy Evolution Demo",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    try:
        # ====================================================================
        # Step 1: Seed model specs
        # ====================================================================
        _header("Step 1: Seeding Model Specs")
        specs = {}
        for sd in SPEC_DEFS:
            spec = ModelSpec(
                name=sd["name"],
                provider=sd["provider"],
                model_id=sd["model_id"],
                task_categories=sd["categories"],
            )
            db.add(spec)
            db.flush()
            specs[sd["name"]] = spec
            print(f"  Created spec: {spec.name} ({spec.provider})")

        # Seed global performance data (8 attempts each)
        for spec_name, categories in SIMULATED_SCORES.items():
            spec = specs[spec_name]
            for cat, score in categories.items():
                for _ in range(8):
                    jitter = random.uniform(-2.0, 2.0)
                    record_model_spec_outcome(
                        db, spec.id, cat, score=score + jitter,
                        success=True, corps_id=None,
                    )
        db.commit()
        print(f"  Seeded global performance for {len(specs)} specs")

        recap_lines.append("## Model Specs")
        for s in specs.values():
            recap_lines.append(f"- {s.name} ({s.provider})")
        recap_lines.append("")

        # ====================================================================
        # Step 2: Create corps with strategies
        # ====================================================================
        _header("Step 2: Creating Corps with Strategies")
        strategies_before = {}
        for cd in CORPS_DEFS:
            corps = Corps(id=cd["id"], name=cd["name"])
            db.add(corps)
            db.flush()

            strategy = CorpsStrategy(
                corps_id=cd["id"],
                model_policy=cd["policy"],
                preferred_provider=cd["provider"],
                exploration_rate=cd["exploration"],
                risk_tolerance=cd["risk"],
                adaptation_style="model_swap",
            )
            db.add(strategy)
            db.flush()

            strategies_before[cd["id"]] = {
                "policy": cd["policy"],
                "provider": cd["provider"],
                "exploration": cd["exploration"],
                "risk": cd["risk"],
            }
            print(f"  {cd['name']}: policy={cd['policy']}, "
                  f"exploration={cd['exploration']}, risk={cd['risk']}")

        # Seed corps-specific performance
        for corps_id, adjustments in CORPS_ADJUSTMENTS.items():
            # Quiet Trumpets only uses anthropic spec
            if corps_id == "quiet-trumpets":
                spec = specs["claude-sonnet-4-5"]
                for cat, delta in adjustments.items():
                    base = SIMULATED_SCORES["claude-sonnet-4-5"][cat]
                    for _ in range(6):
                        jitter = random.uniform(-2.0, 2.0)
                        record_model_spec_outcome(
                            db, spec.id, cat, score=base + delta + jitter,
                            success=True, corps_id=corps_id,
                        )
            else:
                # Other corps use a mix
                for spec_name, spec in specs.items():
                    for cat, delta in adjustments.items():
                        base = SIMULATED_SCORES[spec_name][cat]
                        for _ in range(4):
                            jitter = random.uniform(-2.0, 2.0)
                            record_model_spec_outcome(
                                db, spec.id, cat, score=base + delta + jitter,
                                success=True, corps_id=corps_id,
                            )
        db.commit()
        print(f"  Seeded corps-specific performance data")

        # ====================================================================
        # Step 3: Create season and show on filesystem
        # ====================================================================
        _header("Step 3: Creating Season & Show")
        season_id = "strategy-demo-s1"
        show_slug = "strategy-demo-show"

        # Create season directory
        seasons_dir = root / "seasons"
        seasons_dir.mkdir(parents=True, exist_ok=True)
        season_dir = seasons_dir / season_id
        if not season_dir.exists():
            create_season(root, season_id, metadata={
                "season_id": season_id,
                "name": "Strategy Demo Season 1",
            })
        print(f"  Season: {season_id}")

        # Create show directory
        show_dir = root / "shows" / show_slug
        show_dir.mkdir(parents=True, exist_ok=True)
        atomic_write(show_dir / "status.yaml", safe_dump_yaml({"status": "approved"}))
        atomic_write(show_dir / "spec.md", (
            "# Strategy Demo Show\n\n"
            "## Segments\n"
            "- Frontend UI build (React components)\n"
            "- Backend API implementation (FastAPI endpoints)\n"
            "- Test suite creation (pytest)\n"
        ))
        print(f"  Show: {show_slug}")

        # Register corps (create filesystem entries)
        corps_base = root / "corps"
        for cd in CORPS_DEFS:
            corps_dir = corps_base / cd["id"]
            corps_dir.mkdir(parents=True, exist_ok=True)
            atomic_write(corps_dir / "corps.yaml", safe_dump_yaml({
                "corps_id": cd["id"],
                "display_name": cd["name"],
                "state": "active",
                "philosophy": f"{cd['policy']} strategy",
            }))
            perf_dir = season_dir / "performances" / cd["id"]
            perf_dir.mkdir(parents=True, exist_ok=True)

        recap_lines.append("## Season Setup")
        recap_lines.append(f"- Season: {season_id}")
        recap_lines.append(f"- Show: {show_slug}")
        recap_lines.append(f"- Corps: {', '.join(cd['name'] for cd in CORPS_DEFS)}")
        recap_lines.append("")

        # ====================================================================
        # Step 4 & 5: Simulate agent runs + scoring
        # ====================================================================
        _header("Step 4: Simulating Agent Runs & Scoring")

        composites = {}
        for corps_id, caption_scores in CORPS_CAPTION_SCORES.items():
            raw_total = sum(
                caption_scores[jt] * DEFAULT_WEIGHTS[jt]
                for jt in caption_scores
            )
            composites[corps_id] = CompositeScore(
                caption_scores=caption_scores,
                raw_total=raw_total,
                penalties_total=0.0,
                final_score=raw_total,
                needs_rework=raw_total < 60.0,
                needs_escalation=raw_total < 40.0,
            )
            print(f"  {corps_id}: raw={raw_total:.2f}")

        # ====================================================================
        # Step 6: Compute standings
        # ====================================================================
        _header("Step 5: Computing Standings")
        standings = compute_standings(
            season_id, DEFAULT_WEIGHTS, composites,
        )

        standings_results = []
        for r in standings.results:
            standings_results.append({
                "corps_id": r.corps_id,
                "rank": r.rank,
                "final_score": r.final_score,
            })
            print(f"  #{r.rank} {r.corps_id}: {r.final_score:.2f}")

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

        recap_lines.append("## Standings")
        for r in standings.results:
            recap_lines.append(f"- #{r.rank} {r.corps_id}: {r.final_score:.2f}")
        recap_lines.append("")

        # ====================================================================
        # Step 7: Generate strategy proposals
        # ====================================================================
        _header("Step 6: Generating Strategy Evolution Proposals")
        proposals = generate_strategy_proposals(db, season_id, standings_results)

        if proposals:
            from backend.services.lifecycle_transitions import SeasonPhase
            create_proposals_file(root, season_id, proposals, phase=SeasonPhase.OFFSEASON)

            recap_lines.append("## Strategy Proposals")
            for p in proposals:
                print(f"  [{p.corps_id}] {p.description}")
                recap_lines.append(f"- [{p.corps_id}] {p.description}")
                for k, v in p.changes.items():
                    print(f"    {k}: {v}")
            recap_lines.append("")
        else:
            print("  No proposals generated")

        # ====================================================================
        # Step 8: Apply proposals
        # ====================================================================
        _header("Step 7: Applying Offseason Proposals")
        if proposals:
            audit = apply_proposals(
                root, season_id, corps_base, root / "talent_pool",
                apply=True, db=db,
            )
            for entry in audit:
                status = entry["result"]
                error = entry.get("error", "")
                print(f"  Proposal {entry['proposal_index']}: {status} {error}")
                recap_lines.append(f"- Proposal {entry['proposal_index']}: {status}")
            recap_lines.append("")
        else:
            print("  No proposals to apply")

        # ====================================================================
        # Step 9: Verify strategy updates
        # ====================================================================
        _header("Step 8: Verifying Strategy Updates")
        strategies_after = {}
        for cd in CORPS_DEFS:
            strategy = (
                db.query(CorpsStrategy)
                .filter(CorpsStrategy.corps_id == cd["id"])
                .first()
            )
            strategies_after[cd["id"]] = {
                "policy": strategy.model_policy,
                "provider": strategy.preferred_provider,
                "exploration": strategy.exploration_rate,
                "risk": strategy.risk_tolerance,
            }

        # ====================================================================
        # Step 10: Print summary
        # ====================================================================
        _header("SUMMARY: Strategy Before & After")
        recap_lines.append("## Strategy Changes")

        for cd in CORPS_DEFS:
            cid = cd["id"]
            before = strategies_before[cid]
            after = strategies_after[cid]
            changed = before != after

            print(f"\n  {cd['name']} ({cid}):")
            print(f"    BEFORE: policy={before['policy']}, "
                  f"exploration={before['exploration']:.2f}, "
                  f"provider={before['provider']}")
            print(f"    AFTER:  policy={after['policy']}, "
                  f"exploration={after['exploration']:.2f}, "
                  f"provider={after['provider']}")
            if changed:
                diffs = []
                for k in before:
                    if before[k] != after[k]:
                        diffs.append(f"{k}: {before[k]} -> {after[k]}")
                print(f"    CHANGED: {', '.join(diffs)}")
            else:
                print(f"    (no change)")

            recap_lines.append(f"\n### {cd['name']}")
            recap_lines.append(f"- Before: policy={before['policy']}, "
                             f"exploration={before['exploration']:.2f}")
            recap_lines.append(f"- After: policy={after['policy']}, "
                             f"exploration={after['exploration']:.2f}")
            recap_lines.append(f"- Changed: {'Yes' if changed else 'No'}")

        # Model spec leaderboard
        _subheader("Model Spec Leaderboard")
        recap_lines.append("\n## Model Spec Leaderboard")
        for category in ["frontend", "backend", "testing"]:
            entries = get_spec_leaderboard(db, category, limit=5)
            print(f"\n  {category.upper()}:")
            recap_lines.append(f"\n### {category}")
            for i, entry in enumerate(entries):
                line = (f"    #{i+1} {entry['name']} ({entry['provider']}): "
                        f"avg={entry['avg_score']:.1f}, "
                        f"attempts={entry['total_attempts']}")
                print(line)
                recap_lines.append(f"- #{i+1} {entry['name']}: "
                                 f"avg={entry['avg_score']:.1f}")

        # Improvement analysis
        _subheader("Improvement Analysis")
        recap_lines.append("\n## Improvement Analysis")
        for cd in CORPS_DEFS:
            cid = cd["id"]
            before = strategies_before[cid]
            after = strategies_after[cid]
            if before != after:
                msg = (f"  {cd['name']}: Strategy evolved! "
                       f"({before['policy']} -> {after['policy']})")
                print(msg)
                recap_lines.append(f"- {cd['name']}: Improved "
                                 f"({before['policy']} -> {after['policy']})")
            else:
                msg = f"  {cd['name']}: Strategy stable (performing well or at top)"
                print(msg)
                recap_lines.append(f"- {cd['name']}: Stable")

        print()

    finally:
        db.close()

    # Write recap
    recap_text = "\n".join(recap_lines)
    docs_dir = root / "docs" / "outputs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    recap_path = docs_dir / "strategy_demo.md"
    atomic_write(recap_path, recap_text)
    print(f"Recap written to: {recap_path}")

    return recap_text


if __name__ == "__main__":
    import sys
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    run_strategy_demo(root)
