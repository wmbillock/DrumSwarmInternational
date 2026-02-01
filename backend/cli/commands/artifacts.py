"""dci corps init / show create / show status / show approve — filesystem artifact commands."""

import os
import sys
from pathlib import Path

import yaml

from backend.cli.commands.doctor import _find_project_root


def _get_root() -> Path:
    override = os.environ.get("DCI_PROJECT_ROOT", "")
    if override:
        return Path(override).resolve()
    return Path(_find_project_root())


# ---------------------------------------------------------------------------
# corps init
# ---------------------------------------------------------------------------

def cmd_corps_init(args) -> None:
    root = _get_root()
    corps_id = args.corps_id
    corps_dir = root / "corps" / corps_id

    plan = getattr(args, "plan", False)
    yes = getattr(args, "yes", False)

    if plan or not yes:
        print(f"Plan: create corps workspace '{corps_id}'")
        print(f"  create {corps_dir}/corps.yaml")
        print(f"  create {corps_dir}/roster.yaml")
        if not plan:
            print("\nPass --yes to apply, or --plan to preview.")
        return

    # Idempotent
    if (corps_dir / "corps.yaml").exists():
        print(f"Corps '{corps_id}' already exists at {corps_dir}")
        return

    from backend.services.corps_persistence import create_corps
    data = {
        "corps_id": corps_id,
        "display_name": corps_id,
        "philosophy": "",
        "state": "commissioned",
    }
    create_corps(corps_dir, data)
    print(f"Corps '{corps_id}' created at {corps_dir}")


# ---------------------------------------------------------------------------
# show create (filesystem workspace)
# ---------------------------------------------------------------------------

def cmd_show_create_workspace(args) -> None:
    root = _get_root()
    slug = args.title  # positional arg is the slug
    title = getattr(args, "show_title", None) or slug
    shows_dir = root / "shows"

    plan = getattr(args, "plan", False)
    yes = getattr(args, "yes", False)

    from backend.services.show_persistence import slugify
    resolved_slug = slugify(title) if title != slug else slug

    show_dir = shows_dir / resolved_slug

    if plan or not yes:
        print(f"Plan: create show workspace '{resolved_slug}'")
        print(f"  create {show_dir}/status.yaml")
        print(f"  create {show_dir}/design_notes.md")
        print(f"  create {show_dir}/show_prompt.md")
        if not plan:
            print("\nPass --yes to apply, or --plan to preview.")
        return

    from backend.services.show_persistence import create_show
    shows_dir.mkdir(parents=True, exist_ok=True)

    # create_show uses title for slug generation; we want the explicit slug
    # Write directly to honor the user-provided slug
    show_dir.mkdir(parents=True, exist_ok=True)
    from backend.services.yaml_util import atomic_write, safe_dump_yaml
    if not (show_dir / "status.yaml").exists():
        atomic_write(show_dir / "status.yaml", safe_dump_yaml({"status": "draft"}))
    if not (show_dir / "design_notes.md").exists():
        atomic_write(show_dir / "design_notes.md", "")
    if not (show_dir / "show_prompt.md").exists():
        atomic_write(show_dir / "show_prompt.md", "")
    print(f"Show workspace created at {show_dir}")


# ---------------------------------------------------------------------------
# show status (read-only)
# ---------------------------------------------------------------------------

def cmd_show_status_workspace(args) -> None:
    root = _get_root()
    slug = args.slug
    show_dir = root / "shows" / slug

    status_file = show_dir / "status.yaml"
    if not status_file.exists():
        print(f"Show '{slug}' not found at {show_dir}", file=sys.stderr)
        sys.exit(1)

    data = yaml.safe_load(status_file.read_text())
    print(f"Show: {slug}")
    print(f"Status: {data.get('status', 'unknown')}")


# ---------------------------------------------------------------------------
# show approve
# ---------------------------------------------------------------------------

def cmd_show_approve(args) -> None:
    root = _get_root()
    slug = args.slug
    show_dir = root / "shows" / slug

    status_file = show_dir / "status.yaml"
    if not status_file.exists():
        print(f"Show '{slug}' not found at {show_dir}", file=sys.stderr)
        sys.exit(1)

    plan = getattr(args, "plan", False)
    yes = getattr(args, "yes", False)

    if plan or not yes:
        print(f"Plan: approve show '{slug}'")
        print(f"  update {status_file}: status -> approved")
        if not plan:
            print("\nPass --yes to apply, or --plan to preview.")
        return

    from backend.services.show_persistence import update_status
    update_status(show_dir, "approved")
    print(f"Show '{slug}' approved.")
