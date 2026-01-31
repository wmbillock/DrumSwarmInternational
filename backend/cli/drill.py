#!/usr/bin/env python3
"""DCI Swarm CLI Calibration Tool — `./dci drill`

Creates a show, activates it, and runs the full agent swarm —
ED → PC → Caption Heads → Techs — until the problem is solved.

Usage:
    python -m backend.cli.drill "Solve Project Euler #1: sum of multiples of 3 or 5 below 1000"
    python -m backend.cli.drill --problem 1
    python -m backend.cli.drill --loop 1,2,3,4,5  # Calibration loop
"""

import argparse
import json
import sys
import os
import time

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


EULER_PROBLEMS = {
    1: "Find the sum of all multiples of 3 or 5 below 1000.",
    2: "Find the sum of even-valued Fibonacci terms that do not exceed four million.",
    3: "What is the largest prime factor of the number 600851475143?",
    4: "Find the largest palindrome made from the product of two 3-digit numbers.",
    5: "What is the smallest positive number evenly divisible by all numbers from 1 to 20?",
    6: "Find the difference between the sum of the squares and the square of the sum of the first 100 natural numbers.",
    7: "What is the 10001st prime number?",
    8: "Find the thirteen adjacent digits in the 1000-digit number that have the greatest product.",
    9: "Find the product abc where a+b+c=1000 and a^2+b^2=c^2 (Pythagorean triplet).",
    10: "Find the sum of all primes below two million.",
}

# Colors
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
MAGENTA = "\033[0;35m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"


def log(color, prefix, msg):
    print(f"{color}[{prefix}]{NC} {msg}")


def on_event(event: dict):
    """Pretty-print agent runtime events."""
    t = event.get("type", "?")
    role = event.get("role", "?")

    if t == "agent_status":
        status = event.get("status", "?")
        color = GREEN if status in ("running", "completed") else RED if status == "failed" else YELLOW
        log(color, role, f"status: {status}")
        if event.get("error"):
            log(RED, role, f"  error: {event['error']}")

    elif t == "agent_response":
        content = event.get("content", "")
        log(CYAN, role, f"response ({len(content)} chars):")
        for line in content[:500].split("\n"):
            print(f"  {DIM}{line}{NC}")
        if len(content) > 500:
            print(f"  {DIM}... ({len(content) - 500} more chars){NC}")

    elif t == "tool_call":
        tool = event.get("tool", "?")
        args = event.get("args", {})
        args_str = json.dumps(args, indent=None)[:200]
        log(BLUE, role, f"tool: {tool}({args_str})")

    elif t == "tool_result":
        tool = event.get("tool", "?")
        result = event.get("result", {})
        success = result.get("success", False)
        color = GREEN if success else RED
        if success:
            output = json.dumps(result.get("output", ""), indent=None)[:200]
        else:
            output = result.get("error", "unknown error")[:200]
        log(color, role, f"  -> {output}")


def build_llm_client():
    """Build the LLM client with circuit breaker failover."""
    import shutil
    from backend.services.llm_client import (
        CircuitBreakerLLMClient, ClaudeCLIClient, ChatGPTCLIClient,
        AnthropicLLMClient, OpenAIClient, MockLLMClient,
    )

    if os.environ.get("DCI_DRY_RUN"):
        from backend.services.simulation import SimulationLLMClient
        inner = MockLLMClient()
        # Try to get a real client for planning
        if shutil.which("claude"):
            inner = ClaudeCLIClient()
        elif os.environ.get("ANTHROPIC_API_KEY"):
            inner = AnthropicLLMClient()
        log(YELLOW, "drill", "Dry-run: using SimulationLLMClient")
        return SimulationLLMClient(inner)

    clients = []

    if shutil.which("claude"):
        clients.append(("claude_cli", ClaudeCLIClient()))
    if os.environ.get("ANTHROPIC_API_KEY"):
        clients.append(("anthropic_api", AnthropicLLMClient()))
    if shutil.which("chatgpt"):
        clients.append(("chatgpt_cli", ChatGPTCLIClient()))
    if os.environ.get("OPENAI_API_KEY"):
        clients.append(("openai_api", OpenAIClient()))

    if not clients:
        log(YELLOW, "drill", "No LLM client available — using mock")
        return MockLLMClient()

    if len(clients) == 1:
        name, client = clients[0]
        log(GREEN, "drill", f"Using {name}")
        return client

    cb = CircuitBreakerLLMClient(clients, threshold=2)
    names = [n for n, _ in clients]
    log(GREEN, "drill", f"Using {names[0]} (failover: {', '.join(names[1:])})")
    return cb


def find_session_for_role(db, corps_id: str, role: str):
    """Find or create an active agent session for a role in a corps.

    If the previous session completed, spawns a new one with context from the old session.
    """
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.agent_definition import AgentDefinition
    from backend.services.agent_lifecycle import spawn_session

    # Look for active session first
    active = (
        db.query(AgentSession)
        .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
        .filter(
            AgentSession.corps_id == corps_id,
            AgentDefinition.role == role,
            AgentSession.status == SessionStatus.ACTIVE,
        )
        .first()
    )
    if active:
        return active

    # Find the most recent completed session and respawn
    completed = (
        db.query(AgentSession)
        .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
        .filter(
            AgentSession.corps_id == corps_id,
            AgentDefinition.role == role,
            AgentSession.status == SessionStatus.COMPLETED,
        )
        .order_by(AgentSession.id.desc())
        .first()
    )
    if completed:
        new_session = spawn_session(db, completed.definition_id, corps_id)
        log(DIM, "orchestrator", f"Respawned {role} session: {new_session.id[:8]}...")
        return new_session

    return None


def run_agent_for_role(db, role, session, llm_client, tool_executor, task_desc, corps_id):
    """Run a single agent and return the result."""
    from backend.services.agent_runtime import run_agent

    log(MAGENTA, "orchestrator", f"Dispatching {role} (session: {session.id[:8]}...)")
    print(f"\n{'-'*40}")

    # Load previous context snapshot for continuity
    context_snapshot = session.context_snapshot if hasattr(session, 'context_snapshot') else None

    start = time.time()
    result = run_agent(
        db=db,
        session_id=session.id,
        llm_client=llm_client,
        tool_executor=tool_executor,
        task_description=task_desc,
        context_snapshot=context_snapshot,
        on_event=on_event,
        keep_alive=True,
    )
    elapsed = time.time() - start

    status_color = GREEN if result.status == "completed" else RED
    log(status_color, role,
        f"Done: {result.status} | {result.iterations} iters | {len(result.tool_calls_made)} tools | {elapsed:.1f}s")

    if result.error:
        log(RED, role, f"Error: {result.error}")

    return result


def run_orchestration_loop(db, corps_id, root_coord_id, llm_client, tool_executor, max_rounds=50):
    """Poll for handoff messages and dispatch agents until all work is done."""
    from backend.services.message_service import poll_messages, acknowledge_message
    from backend.models.message import MessageType
    from backend.models.rep import RepStatus
    from backend.services.rep_service import get_reps_for_segment
    from backend.services.segment_service import get_children

    print(f"\n{BOLD}{'='*60}{NC}")
    log(MAGENTA, "orchestrator", "Starting orchestration loop")
    print(f"{'='*60}")

    total_agents_run = 0

    for round_num in range(1, max_rounds + 1):
        log(MAGENTA, "orchestrator", f"--- Round {round_num}/{max_rounds} ---")

        # Find all unacknowledged handoff messages
        messages = poll_messages(db, corps_id)
        handoffs = [m for m in messages if m.type == MessageType.HANDOFF and m.to_role]

        if not handoffs:
            # Check if there's still pending work (reps or leaf coords without reps)
            pending_work = _check_pending_work(db, root_coord_id)
            if pending_work:
                log(YELLOW, "orchestrator", f"No handoffs but {pending_work} items still pending")
                # Try to find agents with pending messages of any type
                all_pending = [m for m in messages if m.to_role]
                if all_pending:
                    handoffs = all_pending
                else:
                    # Auto-dispatch program_coordinator to break down pending segments
                    pc_session = find_session_for_role(db, corps_id, "program_coordinator")
                    if pc_session:
                        log(YELLOW, "orchestrator", "Auto-dispatching program_coordinator for pending segments")
                        tree = _build_tree_summary(db, root_coord_id)
                        task_desc = (
                            f"Root segment ID: {root_coord_id}\n\n"
                            f"CURRENT TREE STATE:\n{tree}\n\n"
                            f"There are {pending_work} pending items that need reps. "
                            f"DO NOT create new sets or segments that already exist. "
                            f"For each leaf segment that has NO reps, call create_rep with its segment_id. "
                            f"Then hand off to appropriate caption heads.\n"
                            f"NOTE: corps_id and from_role are auto-injected — do NOT include them in tool calls."
                        )
                        result = run_agent_for_role(db, "program_coordinator", pc_session, llm_client, tool_executor, task_desc, corps_id)
                        total_agents_run += 1
                        if result.status == "failed":
                            log(RED, "orchestrator", "PC auto-dispatch failed")
                            break
                        continue  # Re-check for new handoffs
                    else:
                        log(YELLOW, "orchestrator", "No PC session available. Stopping.")
                        break
            else:
                log(GREEN, "orchestrator", "All work completed!")
                break

        for msg in handoffs:
            role = msg.to_role
            session = find_session_for_role(db, corps_id, role)

            if not session:
                log(RED, "orchestrator", f"No active session for role '{role}' — skipping")
                acknowledge_message(db, msg.id)
                continue

            tree = _build_tree_summary(db, root_coord_id)
            task_desc = (
                f"Root segment ID: {root_coord_id}\n"
                f"Message from {msg.from_role}: {msg.subject}\n"
            )
            if msg.body:
                task_desc += f"\nDetails:\n{msg.body}\n"
            if msg.segment_id:
                task_desc += f"\nSegment ID: {msg.segment_id}\n"
            task_desc += (
                f"\nCURRENT TREE STATE:\n{tree}\n"
                f"\nNOTE: corps_id and from_role are auto-injected in tool calls — do NOT include them."
            )

            result = run_agent_for_role(db, role, session, llm_client, tool_executor, task_desc, corps_id)
            total_agents_run += 1

            # Acknowledge the message after processing
            acknowledge_message(db, msg.id)

            if result.status == "failed":
                log(RED, "orchestrator", f"Agent {role} failed — continuing with remaining work")

        # Brief pause between rounds
        time.sleep(0.5)

    log(MAGENTA, "orchestrator", f"Orchestration complete: {total_agents_run} agents dispatched over {round_num} rounds")
    return total_agents_run


def _build_tree_summary(db, root_coord_id) -> str:
    """Build a text summary of the segment tree with IDs."""
    from backend.services.segment_service import get_children, get_segment
    from backend.services.rep_service import get_reps_for_segment

    lines = []

    def _walk(cid, indent=0):
        coord = get_segment(db, cid)
        if not coord:
            return
        prefix = "  " * indent
        lines.append(f"{prefix}{coord.type.value}: {coord.title} [id={coord.id}, status={coord.status.value}]")
        reps = get_reps_for_segment(db, cid)
        for rep in reps:
            lines.append(f"{prefix}  rep [id={rep.id}, status={rep.status.value}]")
        for child in get_children(db, cid):
            _walk(child.id, indent + 1)

    _walk(root_coord_id)
    return "\n".join(lines) if lines else "(empty tree)"


def _check_pending_work(db, root_coord_id) -> int:
    """Count pending work: reps not in terminal state + leaf segments with no reps."""
    from backend.models.rep import RepStatus
    from backend.models.segment import SegmentType
    from backend.services.segment_service import get_children, get_segment
    from backend.services.rep_service import get_reps_for_segment

    pending_count = 0
    coords_to_check = [root_coord_id]
    checked = set()

    while coords_to_check:
        cid = coords_to_check.pop()
        if cid in checked:
            continue
        checked.add(cid)

        children = get_children(db, cid)
        for child in children:
            coords_to_check.append(child.id)

        coord = get_segment(db, cid)
        reps = get_reps_for_segment(db, cid)

        if reps:
            for rep in reps:
                if rep.status not in (RepStatus.COMPLETED, RepStatus.FAILED):
                    pending_count += 1
        elif coord and coord.status.value == "pending" and not children:
            # Leaf segment with no reps — needs work
            pending_count += 1

    return pending_count


def print_final_summary(db, root_coord_id):
    """Print the final segment tree and rep results."""
    from backend.services.segment_service import get_children
    from backend.services.rep_service import get_reps_for_segment

    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{BOLD}  FINAL STATE{NC}")
    print(f"{'='*60}")

    def print_tree(coord_id, indent=0):
        from backend.services.segment_service import get_segment
        coord = get_segment(db, coord_id)
        if not coord:
            return

        status_color = GREEN if coord.status.value == "completed" else RED if coord.status.value == "failed" else YELLOW
        prefix = "  " * indent
        print(f"{prefix}{status_color}{coord.type.value}: {coord.title} [{coord.status.value}]{NC}")

        reps = get_reps_for_segment(db, coord_id)
        for rep in reps:
            rep_color = GREEN if rep.status.value == "completed" else RED if rep.status.value == "failed" else YELLOW
            print(f"{prefix}  {rep_color}rep [{rep.status.value}]{NC}")
            if rep.result:
                result_preview = rep.result[:200]
                print(f"{prefix}    {DIM}{result_preview}{NC}")
            if rep.error:
                print(f"{prefix}    {RED}error: {rep.error}{NC}")

        children = get_children(db, coord_id)
        for child in children:
            print_tree(child.id, indent + 1)

    print_tree(root_coord_id)


def run_drill(task_description: str, max_rounds: int = 50):
    """Create a show, activate it, and run the full swarm."""
    from backend.database import Base, create_db_engine, create_session_factory
    from backend.services.show_service import create_show, activate_show
    from backend.services.agent_runtime import run_agent
    from backend.tools import create_tool_registry
    from backend.services.tool_executor import ToolExecutor

    # Setup
    engine = create_db_engine()
    Base.metadata.create_all(engine)
    DBSession = create_session_factory(engine)
    db = DBSession()

    llm_client = build_llm_client()
    registry = create_tool_registry()
    if os.environ.get("DCI_DRY_RUN"):
        from backend.services.simulation import DryRunToolExecutor
        tool_executor = DryRunToolExecutor(registry)
    else:
        tool_executor = ToolExecutor(registry)

    try:
        # Create and activate show
        log(BOLD, "drill", f"Task: {task_description}")
        show = create_show(db, title=f"Drill: {task_description[:60]}", description=task_description)
        log(GREEN, "drill", f"Show created: {show.id}")

        show = activate_show(db, show.id)
        log(GREEN, "drill", f"Show activated. Corps: {show.corps_id}, Root coord: {show.segment_root_id}")

        # Phase 1: Run Executive Director
        ed_session = find_session_for_role(db, show.corps_id, "executive_director")
        if not ed_session:
            log(RED, "drill", "No active ED session found!")
            return None

        log(GREEN, "drill", f"Phase 1: Executive Director (session: {ed_session.id[:8]}...)")
        print(f"\n{'='*60}")

        start = time.time()
        ed_result = run_agent(
            db=db,
            session_id=ed_session.id,
            llm_client=llm_client,
            tool_executor=tool_executor,
            task_description=(
                f"The show has been activated. The root segment ID is {show.segment_root_id}. "
                f"Task: {task_description}\n\n"
                f"Design the show structure: create MOVEMENT segments under the root, "
                f"then hand off to the program_coordinator. "
                f"Do NOT include corps_id or from_role in tool calls — they are auto-injected."
            ),
            on_event=on_event,
            keep_alive=True,
        )
        elapsed = time.time() - start

        ed_color = GREEN if ed_result.status == "completed" else RED
        log(ed_color, "drill",
            f"ED: {ed_result.status} | {ed_result.iterations} iters | {len(ed_result.tool_calls_made)} tools | {elapsed:.1f}s")

        if ed_result.status == "failed":
            log(RED, "drill", f"ED failed: {ed_result.error}")
            print_final_summary(db, show.segment_root_id)
            return ed_result

        # Phase 2: Orchestration loop — dispatch downstream agents
        log(GREEN, "drill", "Phase 2: Orchestration loop")
        total_start = time.time()
        agents_run = run_orchestration_loop(
            db, show.corps_id, show.segment_root_id, llm_client, tool_executor, max_rounds
        )
        total_elapsed = time.time() - total_start

        log(BOLD, "drill", f"Total: {agents_run + 1} agents | {total_elapsed:.1f}s total")

        # Final summary
        print_final_summary(db, show.segment_root_id)

        # Print dry-run summary if applicable
        if os.environ.get("DCI_DRY_RUN") and hasattr(tool_executor, 'get_summary'):
            print(f"\n{BOLD}{'='*60}{NC}")
            print(f"{BOLD}  DRY-RUN SUMMARY{NC}")
            print(f"{'='*60}")
            print(tool_executor.get_summary())

        return ed_result

    finally:
        db.close()


def run_calibration_loop(problem_ids: list[int], max_rounds: int = 50):
    """Run multiple problems in sequence as a calibration sweep."""
    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{BOLD}  DCI SWARM CALIBRATION — {len(problem_ids)} problems{NC}")
    print(f"{BOLD}{'='*60}{NC}\n")

    results = []
    for pid in problem_ids:
        desc = EULER_PROBLEMS.get(pid, f"Project Euler problem #{pid}")
        print(f"\n{BOLD}--- Problem #{pid} ---{NC}")
        result = run_drill(desc, max_rounds=max_rounds)
        results.append({"problem": pid, "status": result.status if result else "error",
                        "iterations": result.iterations if result else 0,
                        "tool_calls": len(result.tool_calls_made) if result else 0})
        print()

    # Summary
    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{BOLD}  CALIBRATION SUMMARY{NC}")
    print(f"{BOLD}{'='*60}{NC}")
    for r in results:
        status_color = GREEN if r["status"] == "completed" else RED
        print(f"  Problem #{r['problem']:>3}  {status_color}{r['status']:>15}{NC}  "
              f"iters={r['iterations']}  tools={r['tool_calls']}")


def main():
    parser = argparse.ArgumentParser(description="DCI Swarm Drill — CLI calibration tool")
    parser.add_argument("task", nargs="?", help="Task description")
    parser.add_argument("--problem", "-p", type=int, help="Project Euler problem number (1-10)")
    parser.add_argument("--loop", "-l", help="Comma-separated problem IDs for calibration loop")
    parser.add_argument("--max-rounds", "-r", type=int, default=50, help="Max orchestration rounds (default 50)")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run mode: simulate agent behavior without real execution")
    args = parser.parse_args()

    if args.dry_run:
        os.environ["DCI_DRY_RUN"] = "1"
        log(YELLOW, "drill", "DRY-RUN MODE — tools will return synthetic results")

    if args.loop:
        ids = [int(x.strip()) for x in args.loop.split(",")]
        run_calibration_loop(ids, max_rounds=args.max_rounds)
    elif args.problem:
        desc = EULER_PROBLEMS.get(args.problem, f"Solve Project Euler problem #{args.problem}")
        run_drill(desc, max_rounds=args.max_rounds)
    elif args.task:
        run_drill(args.task, max_rounds=args.max_rounds)
    else:
        parser.print_help()
        print(f"\n{BOLD}Available Project Euler problems:{NC}")
        for pid, desc in EULER_PROBLEMS.items():
            print(f"  {pid:>3}. {desc}")


if __name__ == "__main__":
    main()
