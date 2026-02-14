"""DCI Swarm CLI — dual-mode (API client / direct service).

Usage: python -m backend.cli.main <command> [args]
   or: ./dci swarm <command> [args]

Auto-detects API mode (server running) vs direct mode (DB access).
"""

import argparse
import sys


def _get_client():
    """Auto-detect: try API client first, fall back to direct DB access."""
    try:
        from backend.cli.client import APIClient
        client = APIClient()
        if client.ping():
            return client, "api"
    except Exception:
        pass

    from backend.cli.direct import DirectClient
    return DirectClient(), "direct"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dci-swarm",
        description="DCI Swarm CLI — manage the agent orchestration engine",
    )
    parser.add_argument("--api-url", default=None, help="Override API base URL")
    parser.add_argument("--direct", action="store_true", help="Force direct DB mode")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # --- season ---
    season = sub.add_parser("season", help="Season management")
    season_sub = season.add_subparsers(dest="season_cmd")

    sc = season_sub.add_parser("create", help="Create a new season")
    sc.add_argument("name", help="Season name")
    sc.add_argument("--year", type=int, default=None, help="Season year")
    sc.add_argument("--plan", action="store_true", help="Preview writes without applying")
    sc.add_argument("--yes", action="store_true", help="Apply writes")

    sr = season_sub.add_parser("register-corps", help="Register corps for season")
    sr.add_argument("season_id", help="Season ID")
    sr.add_argument("corps_id", help="Corps ID")
    sr.add_argument("--plan", action="store_true", help="Preview writes without applying")
    sr.add_argument("--yes", action="store_true", help="Apply writes")

    src_contest = season_sub.add_parser("run-contest", help="Run a contest")
    src_contest.add_argument("season_id", help="Season ID")
    src_contest.add_argument("--show", required=True, dest="show_slug", help="Show slug")
    src_contest.add_argument("--corps", required=True, action="append", dest="corps_ids", help="Corps ID (repeatable)")
    src_contest.add_argument("--plan", action="store_true", help="Preview writes without applying")
    src_contest.add_argument("--yes", action="store_true", help="Apply writes")

    # --- corps ---
    corps = sub.add_parser("corps", help="Corps management")
    corps_sub = corps.add_subparsers(dest="corps_cmd")

    cl = corps_sub.add_parser("list", help="List corps/shows")
    cl.add_argument("--season", default=None, help="Filter by season ID")

    cs = corps_sub.add_parser("status", help="Corps status")
    cs.add_argument("id", help="Corps ID")

    ci = corps_sub.add_parser("init", help="Create corps workspace on disk")
    ci.add_argument("corps_id", help="Corps identifier")
    ci.add_argument("--plan", action="store_true", help="Preview writes without applying")
    ci.add_argument("--yes", action="store_true", help="Apply writes")

    # corps history
    ch = corps_sub.add_parser("history", help="Corps history index management")
    ch_sub = ch.add_subparsers(dest="history_cmd")

    chb = ch_sub.add_parser("build", help="Build history index for a corps")
    chb.add_argument("corps_id", help="Corps ID")
    chb.add_argument("--plan", action="store_true", help="Preview writes without applying")
    chb.add_argument("--yes", action="store_true", help="Apply writes")

    chl = ch_sub.add_parser("list", help="List history entries for a corps")
    chl.add_argument("corps_id", help="Corps ID")

    # --- show ---
    show = sub.add_parser("show", help="Show management")
    show_sub = show.add_subparsers(dest="show_cmd")

    shc = show_sub.add_parser("create", help="Create a show")
    shc.add_argument("title", help="Show title or slug")
    shc.add_argument("--description", default=None, help="Show description")
    shc.add_argument("--title", dest="show_title", default=None, help="Display title (for workspace mode)")
    shc.add_argument("--plan", action="store_true", help="Preview writes without applying")
    shc.add_argument("--yes", action="store_true", help="Apply writes")

    sha = show_sub.add_parser("activate", help="Activate a show")
    sha.add_argument("id", help="Show ID")

    show_sub.add_parser("list", help="List shows")

    shs = show_sub.add_parser("status", help="Show workspace status")
    shs.add_argument("slug", help="Show slug")

    shap = show_sub.add_parser("approve", help="Approve a show")
    shap.add_argument("slug", help="Show slug")
    shap.add_argument("--plan", action="store_true", help="Preview writes without applying")
    shap.add_argument("--yes", action="store_true", help="Apply writes")

    # --- draft ---
    draft = sub.add_parser("draft", help="Agent drafting")
    draft_sub = draft.add_subparsers(dest="draft_cmd")

    dr = draft_sub.add_parser("run", help="Run agent draft")
    dr.add_argument("corps_id", help="Corps ID")
    dr.add_argument("--count", type=int, default=None, help="Number of agents to draft")

    # --- mode ---
    mode = sub.add_parser("mode", help="Corps mode management")
    mode_sub = mode.add_subparsers(dest="mode_cmd")

    ms = mode_sub.add_parser("switch", help="Switch corps mode")
    ms.add_argument("corps_id", help="Corps ID")
    ms.add_argument("mode", help="Target mode (design_room, show_mode, rehearsal_mode, judging, offseason_review)")

    for shortcut, mode_name in [("design-room", "design_room"), ("rehearsal", "rehearsal_mode"),
                                 ("show", "show_mode"), ("judging", "judging"), ("offseason", "offseason_review")]:
        s = mode_sub.add_parser(shortcut, help=f"Shortcut: switch to {mode_name}")
        s.add_argument("corps_id", help="Corps ID")

    # --- score ---
    score = sub.add_parser("score", help="Scoring")
    score_sub = score.add_subparsers(dest="score_cmd")

    ss = score_sub.add_parser("submit", help="Submit a score")
    ss.add_argument("corps_id", help="Corps ID")
    ss.add_argument("--caption", required=True, help="Caption/judge type")
    ss.add_argument("--value", required=True, type=float, help="Score value")

    # --- status ---
    st = sub.add_parser("status", help="Swarm status")
    st.add_argument("--corps", default=None, help="Corps ID for specific status")
    st.add_argument("--json", action="store_true", help="Output as JSON")

    # --- logs ---
    lg = sub.add_parser("logs", help="View work logs")
    lg.add_argument("corps_id", help="Corps ID")
    lg.add_argument("--tail", type=int, default=20, help="Number of log entries")

    # --- source ---
    src = sub.add_parser("source", help="Accept external work")
    src.add_argument("task_description", nargs="+", help="Task description")
    src.add_argument("--poll", action="store_true", help="Poll for completion after activation")
    src.add_argument("--poll-interval", type=int, default=5, help="Poll interval in seconds")

    # --- watch ---
    wt = sub.add_parser("watch", help="Live tail of corps activity")
    wt.add_argument("corps_id", help="Corps ID")
    wt.add_argument("--interval", type=int, default=2, help="Poll interval in seconds")
    wt.add_argument("--no-follow", action="store_true", help="Show recent logs and exit")

    # --- batch ---
    bt = sub.add_parser("batch", help="Execute a scripted YAML workflow")
    bt.add_argument("script", help="Path to YAML workflow file")
    bt.add_argument("--dry-run", action="store_true", help="Preview steps without executing")

    # --- pool ---
    pool = sub.add_parser("pool", help="Talent pool management")
    pool_sub = pool.add_subparsers(dest="pool_cmd")

    pi = pool_sub.add_parser("init", help="Initialize talent pool structure")
    pi.add_argument("--plan", action="store_true", help="Preview writes without applying")
    pi.add_argument("--yes", action="store_true", help="Apply writes")

    pl = pool_sub.add_parser("list", help="List talent pool agents")
    pl.add_argument("--instrument", default=None, help="Filter by instrument/role")
    pl.add_argument("--json", action="store_true", dest="json_output", help="JSON output")

    # --- run ---
    run = sub.add_parser("run", help="Execute a show run")
    run_sub = run.add_subparsers(dest="run_cmd")
    rs = run_sub.add_parser("show", help="Run a show end-to-end")
    rs.add_argument("show_slug", help="Show slug")
    rs.add_argument("--corps", required=True, dest="corps_id", help="Corps ID")
    rs.add_argument("--season", required=True, dest="season_id", help="Season ID")
    rs.add_argument("--plan", action="store_true", help="Preview writes without applying")
    rs.add_argument("--yes", action="store_true", help="Apply writes")
    rs.add_argument("--timeout-seconds", type=int, default=None, dest="timeout_seconds", help="LLM timeout in seconds (default: 300)")
    rs.add_argument("--max-iterations", type=int, default=None, dest="max_iterations", help="Max agent iterations (default: 30)")

    # --- demo ---
    demo = sub.add_parser("demo", help="Demo workflows")
    demo_sub = demo.add_subparsers(dest="demo_cmd")
    dt = demo_sub.add_parser("tour", help="Run full lifecycle tour")
    dt.add_argument("--seed", type=int, default=1, help="Deterministic seed")
    dt.add_argument("--seasons", type=int, default=1, help="Number of seasons to simulate")
    dt.add_argument("--corps-count", type=int, default=2, help="Number of corps")
    dt.add_argument("--plan", action="store_true", help="Preview without applying")
    dt.add_argument("--yes", action="store_true", help="Apply")

    # --- seance ---
    seance = sub.add_parser("seance", help="Seance session management")
    seance_sub = seance.add_subparsers(dest="seance_cmd")

    ss_start = seance_sub.add_parser("start", help="Start a seance session from a history entry")
    ss_start.add_argument("--corps", required=True, dest="corps_id", help="Corps ID")
    ss_start.add_argument("--entry", required=True, dest="entry_id", help="History entry ID")
    ss_start.add_argument("--plan", action="store_true", help="Preview writes without applying")
    ss_start.add_argument("--yes", action="store_true", help="Apply writes")

    ss_status = seance_sub.add_parser("status", help="Show seance session status")
    ss_status.add_argument("seance_id", help="Seance ID")

    ss_binder = seance_sub.add_parser("binder", help="Print resolved artifact list")
    ss_binder.add_argument("seance_id", help="Seance ID")

    # --- dashboard ---
    dash = sub.add_parser("dashboard", help="Launch cross-platform TUI dashboard")
    dash.add_argument("--terminal", action="store_true", help="Enable embedded terminal pane (split view)")
    dash.add_argument("--refresh", type=int, default=3, help="Refresh interval in seconds")

    # --- doctor ---
    doc = sub.add_parser("doctor", help="Validate repo layout and environment")
    doc.add_argument("--json", action="store_true", dest="json_output", help="Machine-readable JSON output")

    # --- export ---
    ex = sub.add_parser("export", help="Export corps data")
    ex.add_argument("corps_id", help="Corps ID")
    ex.add_argument("--format", choices=["json", "summary"], default="json", help="Output format")
    ex.add_argument("--output", "-o", default=None, help="Output file path")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Commands that run without a client (filesystem-only)
    if args.command == "dashboard":
        from backend.tui.app import main as tui_main
        tui_main()
        return

    if args.command == "doctor":
        from backend.cli.commands.doctor import cmd_doctor
        cmd_doctor(args)
        return

    if args.command == "demo":
        from backend.cli.commands.demo import cmd_demo_tour
        if getattr(args, "demo_cmd", None) == "tour":
            cmd_demo_tour(args)
        else:
            parser.parse_args(["demo", "--help"])
        return

    if args.command == "pool":
        from backend.cli.commands.pool import cmd_pool_init, cmd_pool_list
        if getattr(args, "pool_cmd", None) == "init":
            cmd_pool_init(args)
        elif getattr(args, "pool_cmd", None) == "list":
            cmd_pool_list(args)
        else:
            parser.parse_args(["pool", "--help"])
        return

    if args.command == "run":
        from backend.cli.commands.run import cmd_run_show
        if getattr(args, "run_cmd", None) == "show":
            cmd_run_show(args)
        else:
            parser.parse_args(["run", "--help"])
        return

    if args.command == "season" and getattr(args, "season_cmd", None) == "create" and (
        getattr(args, "plan", False) or getattr(args, "yes", False)
    ):
        from backend.cli.commands.season import cmd_season_create_workspace
        # Map 'name' positional to 'season_id' for workspace command
        args.season_id = args.name
        cmd_season_create_workspace(args)
        return

    if args.command == "season" and getattr(args, "season_cmd", None) == "register-corps":
        from backend.cli.commands.season import cmd_season_register_corps
        cmd_season_register_corps(args)
        return

    if args.command == "season" and getattr(args, "season_cmd", None) == "run-contest":
        from backend.cli.commands.season import cmd_season_run_contest
        cmd_season_run_contest(args)
        return

    if args.command == "corps" and getattr(args, "corps_cmd", None) == "init":
        from backend.cli.commands.artifacts import cmd_corps_init
        cmd_corps_init(args)
        return

    if args.command == "corps" and getattr(args, "corps_cmd", None) == "history":
        from backend.cli.commands.history import cmd_corps_history_build, cmd_corps_history_list
        if getattr(args, "history_cmd", None) == "build":
            cmd_corps_history_build(args)
        elif getattr(args, "history_cmd", None) == "list":
            cmd_corps_history_list(args)
        else:
            parser.parse_args(["corps", "history", "--help"])
        return

    if args.command == "seance":
        from backend.cli.commands.seance_cmd import cmd_seance_start, cmd_seance_status, cmd_seance_binder
        if getattr(args, "seance_cmd", None) == "start":
            cmd_seance_start(args)
        elif getattr(args, "seance_cmd", None) == "status":
            cmd_seance_status(args)
        elif getattr(args, "seance_cmd", None) == "binder":
            cmd_seance_binder(args)
        else:
            parser.parse_args(["seance", "--help"])
        return

    if args.command == "show" and getattr(args, "show_cmd", None) in ("status", "approve"):
        from backend.cli.commands.artifacts import cmd_show_status_workspace, cmd_show_approve
        if args.show_cmd == "status":
            cmd_show_status_workspace(args)
        else:
            cmd_show_approve(args)
        return

    if args.command == "show" and getattr(args, "show_cmd", None) == "create" and (
        getattr(args, "plan", False) or getattr(args, "yes", False)
    ):
        from backend.cli.commands.artifacts import cmd_show_create_workspace
        cmd_show_create_workspace(args)
        return

    # Resolve client
    if args.direct:
        from backend.cli.direct import DirectClient
        client = DirectClient()
        mode = "direct"
    elif args.api_url:
        from backend.cli.client import APIClient
        client = APIClient(base_url=args.api_url)
        mode = "api"
    else:
        client, mode = _get_client()

    from backend.cli.output import print_info
    print_info(f"[{mode} mode]")

    # Dispatch
    cmd = args.command

    if cmd == "season":
        from backend.cli.commands.season import cmd_season_create
        if args.season_cmd == "create":
            cmd_season_create(client, args)
        else:
            parser.parse_args(["season", "--help"])

    elif cmd == "corps":
        from backend.cli.commands.corps import cmd_corps_list, cmd_corps_status
        if args.corps_cmd == "list":
            cmd_corps_list(client, args)
        elif args.corps_cmd == "status":
            cmd_corps_status(client, args)
        else:
            parser.parse_args(["corps", "--help"])

    elif cmd == "show":
        from backend.cli.commands.show import cmd_show_create, cmd_show_activate, cmd_show_list
        if args.show_cmd == "create":
            cmd_show_create(client, args)
        elif args.show_cmd == "activate":
            cmd_show_activate(client, args)
        elif args.show_cmd == "list":
            cmd_show_list(client, args)
        else:
            parser.parse_args(["show", "--help"])

    elif cmd == "draft":
        from backend.cli.commands.draft import cmd_draft_run
        if args.draft_cmd == "run":
            cmd_draft_run(client, args)
        else:
            parser.parse_args(["draft", "--help"])

    elif cmd == "mode":
        from backend.cli.commands.mode import cmd_mode_switch, cmd_mode_shortcut, MODE_SHORTCUTS
        if args.mode_cmd == "switch":
            cmd_mode_switch(client, args)
        elif args.mode_cmd in MODE_SHORTCUTS:
            cmd_mode_shortcut(client, args, MODE_SHORTCUTS[args.mode_cmd])
        else:
            parser.parse_args(["mode", "--help"])

    elif cmd == "score":
        from backend.cli.commands.score import cmd_score_submit
        if args.score_cmd == "submit":
            cmd_score_submit(client, args)
        else:
            parser.parse_args(["score", "--help"])

    elif cmd == "status":
        from backend.cli.commands.query import cmd_status
        cmd_status(client, args)

    elif cmd == "logs":
        from backend.cli.commands.query import cmd_logs
        cmd_logs(client, args)

    elif cmd == "source":
        from backend.cli.commands.source import cmd_source
        cmd_source(client, args)

    elif cmd == "watch":
        from backend.cli.commands.watch import cmd_watch
        args.follow = not getattr(args, "no_follow", False)
        cmd_watch(client, args)

    elif cmd == "batch":
        from backend.cli.commands.batch import cmd_batch
        cmd_batch(client, args)

    elif cmd == "export":
        from backend.cli.commands.export import cmd_export
        cmd_export(client, args)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
