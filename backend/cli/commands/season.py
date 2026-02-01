"""Season commands: create, list, register-corps, run-contest."""

import hashlib
import os
import sys
from pathlib import Path

from backend.cli.output import print_json, print_success, print_error


def cmd_season_create(client, args):
    result = client.season_create(args.name, year=args.year)
    if "error" in result:
        print_error(result["error"])
    else:
        print_success(f"Season '{args.name}' created: {result.get('season_id', '')}")
        print_json(result)


# ---------------------------------------------------------------------------
# Filesystem-only governance commands
# ---------------------------------------------------------------------------

def _get_root() -> Path:
    from backend.cli.commands.doctor import _find_project_root
    override = os.environ.get("DCI_PROJECT_ROOT", "")
    if override:
        return Path(override).resolve()
    return Path(_find_project_root())


def cmd_season_create_workspace(args):
    """Filesystem-only season create."""
    root = _get_root()
    season_id = args.season_id
    plan = getattr(args, "plan", False)
    yes = getattr(args, "yes", False)

    season_dir = root / "seasons" / season_id
    if plan or not yes:
        print(f"Plan: create season '{season_id}' at {season_dir}")
        if not plan:
            print("\nPass --yes to apply.")
        return

    from backend.services.season_persistence import create_season
    try:
        create_season(root, season_id, metadata={"season_id": season_id})
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    print(f"Season '{season_id}' created at {season_dir}")


def cmd_season_register_corps(args):
    """Filesystem-only corps registration for a season."""
    root = _get_root()
    season_id = args.season_id
    corps_id = args.corps_id
    plan = getattr(args, "plan", False)
    yes = getattr(args, "yes", False)

    season_dir = root / "seasons" / season_id
    if plan or not yes:
        print(f"Plan: register corps '{corps_id}' in season '{season_id}'")
        if not plan:
            print("\nPass --yes to apply.")
        return

    from backend.services.season_persistence import register_corps
    try:
        register_corps(season_dir, corps_id, root / "corps")
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    print(f"Corps '{corps_id}' registered for season '{season_id}'")


def _stub_caption_scores(corps_id: str, show_slug: str) -> dict:
    """Deterministic scores per caption, seeded from corps_id + show_slug."""
    from backend.models.score import JudgeType
    scores = {}
    for jtype in [JudgeType.BRASS, JudgeType.PERCUSSION, JudgeType.GUARD,
                  JudgeType.VISUAL, JudgeType.GENERAL_EFFECT]:
        seed = hashlib.sha256(f"{corps_id}:{show_slug}:{jtype.value}".encode()).hexdigest()
        scores[jtype] = (int(seed[:8], 16) % 30) + 60  # 60-89
    return scores


def cmd_season_run_contest(args):
    """Run a contest: deterministic stub scoring, standings, reputation updates."""
    root = _get_root()
    season_id = args.season_id
    show_slug = args.show_slug
    corps_ids = args.corps_ids
    plan = getattr(args, "plan", False)
    yes = getattr(args, "yes", False)

    season_dir = root / "seasons" / season_id

    if plan or not yes:
        print(f"Plan: run contest in season '{season_id}', show '{show_slug}'")
        print(f"  Corps: {', '.join(corps_ids)}")
        if not plan:
            print("\nPass --yes to apply.")
        return

    # Validate season exists
    if not (season_dir / "season.yaml").exists():
        print(f"Season '{season_id}' not found", file=sys.stderr)
        sys.exit(1)

    # Validate show exists and is approved
    show_dir = root / "shows" / show_slug
    if not (show_dir / "status.yaml").exists():
        print(f"Show '{show_slug}' not found", file=sys.stderr)
        sys.exit(1)
    from backend.services.show_persistence import check_field_ready
    if not check_field_ready(show_dir):
        print(f"Show '{show_slug}' is not approved", file=sys.stderr)
        sys.exit(1)

    # Validate all corps exist and are registered
    for cid in corps_ids:
        corps_dir = root / "corps" / cid
        if not (corps_dir / "corps.yaml").exists():
            print(f"Corps '{cid}' not found", file=sys.stderr)
            sys.exit(1)
        perf_dir = season_dir / "performances" / cid
        if not perf_dir.exists():
            print(f"Corps '{cid}' not registered for season '{season_id}'", file=sys.stderr)
            sys.exit(1)

    # Build composites
    from backend.models.score import JudgeType
    from backend.services.scoring_service import CompositeScore, DEFAULT_WEIGHTS
    from backend.services.scoring_engine import compute_standings
    from backend.services.yaml_util import atomic_write, safe_dump_yaml

    composites = {}
    for cid in corps_ids:
        caption_scores = _stub_caption_scores(cid, show_slug)
        raw_total = sum(caption_scores[jt] * DEFAULT_WEIGHTS[jt] for jt in caption_scores)
        composites[cid] = CompositeScore(
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
    for cid in corps_ids:
        composite = composites[cid]
        scores_data = {
            "corps_id": cid,
            "show_slug": show_slug,
            "caption_scores": {jt.value: v for jt, v in composite.caption_scores.items()},
            "raw_total": composite.raw_total,
            "final_score": composite.final_score,
        }
        perf_dir = season_dir / "performances" / cid
        atomic_write(perf_dir / "scores.yaml", safe_dump_yaml(scores_data))

    # Record corps placement
    from backend.services.reputation import record_corps_placement, update_reputations
    from backend.services.corps_persistence import load_roster

    for r in standings.results:
        corps_dir = root / "corps" / r.corps_id
        record_corps_placement(corps_dir, season_id, r.rank, r.final_score,
                               notes=f"show:{show_slug}")

    # Build roster_map and update reputations
    roster_map = {}
    for cid in corps_ids:
        corps_dir = root / "corps" / cid
        roster = load_roster(corps_dir)
        roster_map[cid] = [a["agent_id"] for a in roster.get("assignments", [])]

    session_id = f"{season_id}-{show_slug}"
    pool_dir = root / "talent_pool"
    update_reputations(standings, pool_dir, roster_map, session_id=session_id)

    print(f"Contest complete for season '{season_id}', show '{show_slug}'")
    for r in standings.results:
        print(f"  #{r.rank} {r.corps_id}: {r.final_score:.2f}")
