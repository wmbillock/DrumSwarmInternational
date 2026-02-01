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
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # --- season ---
    season = sub.add_parser("season", help="Season management")
    season_sub = season.add_subparsers(dest="season_cmd")

    sc = season_sub.add_parser("create", help="Create a new season")
    sc.add_argument("name", help="Season name")
    sc.add_argument("--year", type=int, default=None, help="Season year")

    # --- corps ---
    corps = sub.add_parser("corps", help="Corps management")
    corps_sub = corps.add_subparsers(dest="corps_cmd")

    cl = corps_sub.add_parser("list", help="List corps/shows")
    cl.add_argument("--season", default=None, help="Filter by season ID")

    cs = corps_sub.add_parser("status", help="Corps status")
    cs.add_argument("id", help="Corps ID")

    # --- show ---
    show = sub.add_parser("show", help="Show management")
    show_sub = show.add_subparsers(dest="show_cmd")

    shc = show_sub.add_parser("create", help="Create a show")
    shc.add_argument("title", help="Show title")
    shc.add_argument("--description", default=None, help="Show description")

    sha = show_sub.add_parser("activate", help="Activate a show")
    sha.add_argument("id", help="Show ID")

    show_sub.add_parser("list", help="List shows")

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
