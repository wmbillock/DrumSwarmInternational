"""dci seance start / status / binder — seance session CLI commands."""

import os
from pathlib import Path

from backend.cli.commands.doctor import _find_project_root
from backend.cli.output import print_table, print_success, print_error, print_info, print_json


def _get_root() -> Path:
    override = os.environ.get("DCI_PROJECT_ROOT", "")
    if override:
        return Path(override).resolve()
    return Path(_find_project_root())


def cmd_seance_start(args) -> None:
    root = _get_root()
    corps_id = args.corps_id
    entry_id = args.entry_id
    plan = getattr(args, "plan", False)
    yes = getattr(args, "yes", False)

    if plan or not yes:
        print(f"Plan: start seance session")
        print(f"  corps: {corps_id}")
        print(f"  entry: {entry_id}")
        print(f"  create seances/<id>/session.yaml")
        print(f"  create seances/<id>/transcript.md")
        if not plan:
            print("\nPass --yes to apply, or --plan to preview.")
        return

    from backend.services.seance_session import create_session
    try:
        session = create_session(root, corps_id, entry_id)
    except (ValueError, FileNotFoundError) as e:
        print_error(str(e))
        return

    print_success(f"Seance started: {session['seance_id']}")
    print_info(f"  corps: {session['corps_id']}")
    print_info(f"  season: {session['season_id']}")
    if session.get("show_slug"):
        print_info(f"  show: {session['show_slug']}")
    print_info(f"  participant: {session['participant']}")
    loaded = sum(1 for b in session["context_binder"] if b["loaded"])
    total = len(session["context_binder"])
    print_info(f"  context binder: {loaded}/{total} artifacts loaded")


def cmd_seance_status(args) -> None:
    root = _get_root()
    seance_id = args.seance_id

    from backend.services.seance_session import load_session
    try:
        session = load_session(root, seance_id)
    except (ValueError, FileNotFoundError) as e:
        print_error(str(e))
        return

    print(f"Seance: {session['seance_id']}")
    print(f"Status: {session['status']}")
    print(f"Corps: {session['corps_id']}")
    print(f"Season: {session['season_id']}")
    if session.get("show_slug"):
        print(f"Show: {session['show_slug']}")
    print(f"Participant: {session['participant']}")
    print(f"Created: {session['created_at']}")
    loaded = sum(1 for b in session["context_binder"] if b["loaded"])
    total = len(session["context_binder"])
    print(f"Context: {loaded}/{total} artifacts loaded")


def cmd_seance_binder(args) -> None:
    root = _get_root()
    seance_id = args.seance_id

    from backend.services.seance_session import load_session
    try:
        session = load_session(root, seance_id)
    except (ValueError, FileNotFoundError) as e:
        print_error(str(e))
        return

    rows = []
    for item in session["context_binder"]:
        rows.append([
            item["type"],
            item["path"],
            "yes" if item["loaded"] else "no",
        ])

    print_table(
        ["Type", "Path", "Loaded"],
        rows,
        title=f"Context Binder: {seance_id}",
    )
