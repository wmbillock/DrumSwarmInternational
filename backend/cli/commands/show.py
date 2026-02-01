"""Show commands: create, activate, list."""

from backend.cli.output import print_json, print_table, print_success, print_error


def cmd_show_create(client, args):
    result = client.show_create(args.title, description=getattr(args, "description", None))
    if "error" in result:
        print_error(result["error"])
    else:
        print_success(f"Show created: {result.get('id', '')}")
        print_json(result)


def cmd_show_activate(client, args):
    result = client.show_activate(args.id)
    if "error" in result:
        print_error(result["error"])
    else:
        print_success(f"Show activated: {result.get('id', '')}")
        print_json(result)


def cmd_show_list(client, args):
    result = client.show_list()
    if isinstance(result, list):
        rows = []
        for s in result:
            rows.append([
                s.get("id", "")[:8],
                s.get("title", ""),
                s.get("status", ""),
                s.get("corps_id", "")[:8] if s.get("corps_id") else "-",
            ])
        print_table(["ID", "Title", "Status", "Corps"], rows, title="Shows")
    else:
        print_json(result)
