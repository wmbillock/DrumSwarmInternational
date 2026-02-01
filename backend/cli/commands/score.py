"""Score commands: submit scores."""

from backend.cli.output import print_json, print_success, print_error


def cmd_score_submit(client, args):
    if hasattr(client, "score_submit"):
        result = client.score_submit(args.corps_id, args.caption, args.value)
    else:
        result = {"error": "Score submission not available in direct mode"}
    if "error" in result:
        print_error(result["error"])
    else:
        print_success("Score submitted")
        print_json(result)
