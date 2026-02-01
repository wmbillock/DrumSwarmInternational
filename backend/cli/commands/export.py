"""Export command: generate reports from corps data."""

import json

from backend.cli.output import print_info, print_success, print_error, print_table


def cmd_export(client, args):
    corps_id = args.corps_id
    fmt = getattr(args, "format", "json")
    output = getattr(args, "output", None)

    print_info(f"Exporting data for corps {corps_id[:8]}...")

    try:
        data = _gather_export_data(client, corps_id)
    except Exception as e:
        print_error(f"Failed to gather data: {e}")
        return

    if fmt == "json":
        content = json.dumps(data, indent=2, default=str)
    elif fmt == "summary":
        content = _format_summary(data)
    else:
        print_error(f"Unknown format: {fmt}")
        return

    if output:
        with open(output, "w") as f:
            f.write(content)
        print_success(f"Exported to {output}")
    else:
        print(content)


def _gather_export_data(client, corps_id: str) -> dict:
    """Gather all exportable data for a corps."""
    data = {"corps_id": corps_id}

    try:
        data["status"] = client.corps_status(corps_id)
    except Exception:
        data["status"] = {}

    try:
        data["scoresheet"] = client.scoresheet(corps_id)
    except Exception:
        data["scoresheet"] = {}

    try:
        data["logs"] = client.work_log(corps_id, limit=200)
    except Exception:
        data["logs"] = []

    return data


def _format_summary(data: dict) -> str:
    """Format export data as a human-readable summary."""
    lines = []
    status = data.get("status", {})
    lines.append(f"Corps: {status.get('name', data['corps_id'][:8])}")
    lines.append(f"Status: {status.get('status', 'unknown')}")
    lines.append(f"Mode: {status.get('mode', 'none')}")
    lines.append("")

    scoresheet = data.get("scoresheet", {})
    composite = scoresheet.get("composite", {})
    if composite:
        lines.append(f"Final Score: {composite.get('final_score', 'N/A')}")
        lines.append(f"Needs Escalation: {composite.get('needs_escalation', False)}")
        lines.append(f"Needs Rework: {composite.get('needs_rework', False)}")
        lines.append("")

    logs = data.get("logs", [])
    lines.append(f"Log Entries: {len(logs)}")
    if logs:
        # Count by event type
        types = {}
        for l in logs:
            t = l.get("event_type", "unknown")
            types[t] = types.get(t, 0) + 1
        for t, count in sorted(types.items(), key=lambda x: -x[1]):
            lines.append(f"  {t}: {count}")

    return "\n".join(lines)
