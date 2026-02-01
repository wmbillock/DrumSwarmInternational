"""Query commands: status, health, logs."""

from backend.cli.output import print_json, print_table, print_info


def cmd_status(client, args):
    corps_id = getattr(args, "corps", None)
    use_json = getattr(args, "json", False)

    if corps_id:
        result = client.corps_status(corps_id)
    else:
        result = client.system_health()

    if use_json:
        print_json(result)
    else:
        if corps_id:
            print_info(f"Corps: {result.get('name', corps_id)}")
            print_info(f"Status: {result.get('status', 'unknown')}")
            print_info(f"Mode: {result.get('mode', 'none')}")
        else:
            print_info(f"Active Corps: {result.get('active_corps', 0)}")
            print_info(f"Active Agents: {result.get('active_agents', 0)}/{result.get('total_agents', 0)}")
            print_info(f"Failure Rate: {result.get('failure_rate', 0)}%")
            summaries = result.get("corps_summaries", [])
            if summaries:
                rows = [[s["name"], s["status"], s.get("mode") or "-", str(s["agents_active"]), f"{s['reps_completed']}/{s['reps_total']}"] for s in summaries]
                print_table(["Name", "Status", "Mode", "Agents", "Reps"], rows)


def cmd_logs(client, args):
    corps_id = args.corps_id
    limit = getattr(args, "tail", 20)
    result = client.work_log(corps_id, limit=limit)
    if isinstance(result, list):
        rows = [[l.get("event_type", ""), l.get("role", ""), (l.get("details") or "")[:60]] for l in result]
        print_table(["Event", "Role", "Details"], rows, title=f"Logs for {corps_id[:8]}")
    else:
        print_json(result)
