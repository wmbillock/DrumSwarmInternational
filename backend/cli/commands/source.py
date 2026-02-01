"""Source command: accept external work by creating + activating a show.

Enhanced with tracking handle and optional polling for completion.
"""

import time

from backend.cli.output import print_json, print_success, print_error, print_info


def cmd_source(client, args):
    task_desc = " ".join(args.task_description)
    if not task_desc.strip():
        print_error("Task description required")
        return

    poll = getattr(args, "poll", False)
    poll_interval = getattr(args, "poll_interval", 5)

    # Create a show from the task description
    result = client.show_create(task_desc[:100], description=task_desc)
    if "error" in result:
        print_error(result["error"])
        return

    show_id = result.get("id")
    print_success(f"Show created: {show_id}")

    # Activate it
    if not show_id:
        print_error("No show ID returned")
        return

    activate_result = client.show_activate(show_id)
    if "error" in activate_result:
        print_error(activate_result["error"])
        return

    corps_id = activate_result.get("corps_id", "")
    print_success(f"Show activated — corps {corps_id[:8]}")

    # Transition to autonomous execution
    if corps_id:
        try:
            tour_result = client.post(f"/api/corps/{corps_id}/command", json={"command": "go_on_tour"})
            if tour_result.get("status") == "ok":
                print_success("Corps on tour — autonomous execution started")
            else:
                print_error(f"Tour transition: {tour_result}")
        except Exception as e:
            print_error(f"Tour transition failed: {e}")

    # Print tracking handle
    print_info(f"Tracking handle:")
    print_info(f"  show_id:  {show_id}")
    print_info(f"  corps_id: {corps_id}")
    print_info(f"  status:   dci-swarm status --corps {corps_id}")
    print_info(f"  logs:     dci-swarm logs {corps_id}")
    print_info(f"  watch:    dci-swarm watch {corps_id}")

    if not poll:
        return

    # Poll for completion
    print_info(f"\nPolling for completion (every {poll_interval}s, Ctrl+C to stop)...")
    try:
        while True:
            time.sleep(poll_interval)
            try:
                status = client.corps_status(corps_id)
                current = status.get("status", "unknown")
                mode = status.get("mode", "none")
                print_info(f"  status={current} mode={mode}")
                if current in ("completed", "disbanded"):
                    print_success(f"Corps finished: {current}")
                    print_json(status)
                    return
            except Exception:
                pass
    except KeyboardInterrupt:
        print_info("\nStopped polling.")
