"""dci demo tour — run full lifecycle tour with reputation tracking."""

import sys
import tempfile
from pathlib import Path


def cmd_demo_tour(args) -> None:
    plan = getattr(args, "plan", False)
    yes = getattr(args, "yes", False)

    if plan or not yes:
        print("Plan: run full lifecycle tour (pool → draft → score → reputation → decay)")
        print("  Creates temporary directory with talent pool, corps, and season")
        print("  Drafts agents, scores performance, updates reputations, applies decay")
        print("  Prints summary of trust score changes")
        if not plan:
            print("\nPass --yes to apply, or --plan to preview.")
        return

    from backend.scripts.tour_demo import run_tour

    with tempfile.TemporaryDirectory() as tmpdir:
        summary = run_tour(Path(tmpdir))

    print("=== DCI Swarm Lifecycle Tour ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print("Tour complete.")
