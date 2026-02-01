"""Season commands: create, list."""

from backend.cli.output import print_json, print_success, print_error


def cmd_season_create(client, args):
    result = client.season_create(args.name, year=args.year)
    if "error" in result:
        print_error(result["error"])
    else:
        print_success(f"Season '{args.name}' created: {result.get('season_id', '')}")
        print_json(result)
