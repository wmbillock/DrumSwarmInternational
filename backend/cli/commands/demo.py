"""dci demo tour — deterministic end-to-end lifecycle demo."""

import os
import sys
from pathlib import Path


def _get_root() -> Path:
    from backend.cli.commands.doctor import _find_project_root
    override = os.environ.get("DCI_PROJECT_ROOT", "")
    if override:
        return Path(override).resolve()
    return Path(_find_project_root())


def cmd_demo_tour(args) -> None:
    plan = getattr(args, "plan", False)
    yes = getattr(args, "yes", False)
    seed = getattr(args, "seed", 1)
    seasons = getattr(args, "seasons", 1)
    corps_count = getattr(args, "corps_count", 2)

    root = _get_root()

    if plan or not yes:
        print(f"Plan: run deterministic lifecycle tour (seed={seed}, seasons={seasons}, corps={corps_count})")
        print(f"  Root: {root}")
        print("  Steps:")
        print("    1. Init talent pool with fixture agents")
        print(f"    2. Commission {corps_count} corps with drafted rosters")
        print("    3. Create and approve show workspace")
        for s in range(1, seasons + 1):
            print(f"    4.{s}. Run contest for season tour-s{s}")
            if s < seasons:
                print(f"    5.{s}. Apply offseason decay")
        print(f"    6. Write recap to docs/outputs/tour_seed{seed}.md")
        if not plan:
            print("\nPass --yes to apply, or --plan to preview.")
        return

    from backend.scripts.tour_demo import run_deterministic_tour

    recap = run_deterministic_tour(root, seed=seed, seasons=seasons, corps_count=corps_count)

    print("=== DCI Swarm Lifecycle Tour ===")
    print(recap)
    print("Tour complete.")
