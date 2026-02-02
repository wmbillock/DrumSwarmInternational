"""Batch command: execute scripted YAML workflows."""

from backend.cli.output import print_info, print_success, print_error, print_json
from backend.services.yaml_util import safe_load_yaml_dict


def cmd_batch(client, args):
    script_path = args.script
    dry_run = getattr(args, "dry_run", False)

    try:
        with open(script_path) as f:
            workflow = safe_load_yaml_dict(f.read())
    except FileNotFoundError:
        print_error(f"Script not found: {script_path}")
        return

    if not isinstance(workflow, dict) or "steps" not in workflow:
        print_error("Workflow must have a 'steps' key with a list of steps")
        return

    name = workflow.get("name", script_path)
    steps = workflow["steps"]
    print_info(f"Batch: {name} ({len(steps)} steps)")

    # Track variables from step results
    context = {}

    for i, step in enumerate(steps, 1):
        action = step.get("action")
        label = step.get("label", f"step {i}")
        save_as = step.get("save_as")

        if not action:
            print_error(f"Step {i}: missing 'action'")
            return

        # Resolve variable references in step params
        params = {k: _resolve(v, context) for k, v in step.items()
                  if k not in ("action", "label", "save_as")}

        print_info(f"  [{i}/{len(steps)}] {label}")

        if dry_run:
            print_info(f"    (dry-run) {action} {params}")
            continue

        try:
            result = _execute_step(client, action, params)
            if save_as and isinstance(result, dict):
                context[save_as] = result
            print_success(f"    done")
        except Exception as e:
            print_error(f"    failed: {e}")
            if not step.get("continue_on_error", False):
                print_error("Batch aborted.")
                return

    print_success(f"Batch complete: {name}")


def _resolve(value, context: dict):
    """Resolve $var references in string values."""
    if not isinstance(value, str):
        return value
    if value.startswith("$") and "." in value:
        parts = value[1:].split(".", 1)
        var_name, key = parts
        obj = context.get(var_name, {})
        return obj.get(key, value)
    if value.startswith("$"):
        var_name = value[1:]
        return context.get(var_name, value)
    return value


def _execute_step(client, action: str, params: dict):
    """Execute a single batch step."""
    if action == "show.create":
        return client.show_create(params["title"], description=params.get("description"))
    elif action == "show.activate":
        return client.show_activate(params["id"])
    elif action == "mode.switch":
        return client.mode_switch(params["corps_id"], params["mode"])
    elif action == "command":
        return client.execute_command(params["corps_id"], params["command"])
    elif action == "season.create":
        return client.season_create(params["name"], year=params.get("year"))
    elif action == "wait":
        import time
        seconds = int(params.get("seconds", 5))
        time.sleep(seconds)
        return {"waited": seconds}
    else:
        raise ValueError(f"Unknown action: {action}")
