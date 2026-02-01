"""dci corps history build / list — corps history index commands."""

import os
from pathlib import Path

from backend.cli.commands.doctor import _find_project_root
from backend.cli.output import print_table, print_success, print_error, print_info


def _get_root() -> Path:
    override = os.environ.get("DCI_PROJECT_ROOT", "")
    if override:
        return Path(override).resolve()
    return Path(_find_project_root())


def cmd_corps_history_build(args) -> None:
    root = _get_root()
    corps_id = args.corps_id
    plan = getattr(args, "plan", False)
    yes = getattr(args, "yes", False)

    index_path = root / "corps" / corps_id / "history" / "index.yaml"

    if plan or not yes:
        print(f"Plan: build history index for corps '{corps_id}'")
        print(f"  scan corps/{corps_id}/corps.yaml history entries")
        print(f"  probe season artifacts on disk")
        print(f"  write {index_path}")
        if not plan:
            print("\nPass --yes to apply, or --plan to preview.")
        return

    corps_path = root / "corps" / corps_id / "corps.yaml"
    if not corps_path.exists():
        print_error(f"Corps '{corps_id}' not found at {corps_path}")
        return

    from backend.services.corps_history import build_history_index
    index = build_history_index(root, corps_id)
    n = len(index["entries"])
    print_success(f"Built history index for '{corps_id}': {n} entr{'y' if n == 1 else 'ies'}")


def cmd_corps_history_list(args) -> None:
    root = _get_root()
    corps_id = args.corps_id

    corps_path = root / "corps" / corps_id / "corps.yaml"
    if not corps_path.exists():
        print_error(f"Corps '{corps_id}' not found at {corps_path}")
        return

    from backend.services.corps_history import load_history_index
    index = load_history_index(root, corps_id)

    if not index["entries"]:
        print_info(f"No history entries for corps '{corps_id}'.")
        return

    rows = []
    for e in index["entries"]:
        artifact_count = len(e.get("artifacts", {}))
        run_count = len(e.get("runs", []))
        rows.append([
            e["entry_id"],
            e["season_id"],
            e.get("show_slug") or "-",
            str(e["placement"]),
            str(e["final_score"]),
            str(artifact_count),
            str(run_count),
        ])

    print_table(
        ["Entry ID", "Season", "Show", "Place", "Score", "Artifacts", "Runs"],
        rows,
        title=f"History: {corps_id}",
    )
