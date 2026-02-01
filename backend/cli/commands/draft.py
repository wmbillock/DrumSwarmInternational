"""Draft commands: run agent drafting for a corps."""

from backend.cli.output import print_json, print_success, print_error


def cmd_draft_run(client, args):
    if hasattr(client, "draft_run"):
        result = client.draft_run(args.corps_id)
    else:
        result = {"error": "Draft not available in direct mode"}
    if "error" in result:
        print_error(result["error"])
    else:
        print_success("Draft initiated")
        print_json(result)
