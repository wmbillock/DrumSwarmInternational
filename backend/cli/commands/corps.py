"""Corps commands: list, status."""

from backend.cli.output import print_json, print_table, print_error


def cmd_corps_list(client, args):
    result = client.corps_list(season_id=getattr(args, "season", None))
    if isinstance(result, list):
        rows = []
        for s in result:
            rows.append([
                s.get("id", "")[:8],
                s.get("title", s.get("name", "")),
                s.get("status", ""),
                s.get("corps_id", "")[:8] if s.get("corps_id") else "-",
            ])
        print_table(["ID", "Title", "Status", "Corps"], rows, title="Corps / Shows")
    else:
        print_json(result)


def cmd_corps_status(client, args):
    result = client.corps_status(args.id)
    if "error" in result:
        print_error(result["error"])
    else:
        print_json(result)
