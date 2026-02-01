"""Mode commands: switch corps mode."""

from backend.cli.output import print_json, print_success, print_error

MODES = ["design_room", "show_mode", "rehearsal_mode", "judging", "offseason_review"]
MODE_SHORTCUTS = {
    "design-room": "design_room",
    "show": "show_mode",
    "rehearsal": "rehearsal_mode",
    "judging": "judging",
    "offseason": "offseason_review",
}


def cmd_mode_switch(client, args):
    mode = MODE_SHORTCUTS.get(args.mode, args.mode)
    if mode not in MODES:
        print_error(f"Invalid mode: {args.mode}. Valid modes: {', '.join(MODES)}")
        return
    result = client.mode_switch(args.corps_id, mode)
    if "error" in result:
        print_error(result["error"])
    else:
        print_success(f"Mode switched to {mode}")
        print_json(result)


def cmd_mode_shortcut(client, args, mode_name: str):
    """Handle mode shortcuts like 'dci-swarm mode design-room <corps-id>'."""
    result = client.mode_switch(args.corps_id, mode_name)
    if "error" in result:
        print_error(result["error"])
    else:
        print_success(f"Mode switched to {mode_name}")
        print_json(result)
