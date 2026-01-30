#!/usr/bin/env python3
"""DCI Swarm CLI Calibration Tool — `./dci drill`

Creates a show, activates it, and runs the executive director agent
synchronously so you can watch the swarm work on a problem.

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
        # Print first 500 chars indented
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
        output = json.dumps(result.get("output", result.get("error", "")), indent=None)[:200]
        log(color, role, f"  -> {output}")


def run_drill(task_description: str, model_tier_override: str = None):
    """Create a show, activate it, and run the ED agent."""
    from backend.database import Base, create_db_engine, create_session_factory
    from backend.services.show_service import create_show, activate_show
    from backend.services.agent_runtime import run_agent
    from backend.services.llm_client import AnthropicLLMClient, MockLLMClient
    from backend.tools import create_tool_registry
    from backend.services.tool_executor import ToolExecutor

    # Setup
    engine = create_db_engine()
    Base.metadata.create_all(engine)
    DBSession = create_session_factory(engine)
    db = DBSession()

    import shutil
    from backend.services.llm_client import ClaudeCLIClient, ChatGPTCLIClient, OpenAIClient

    if shutil.which("claude"):
        llm_client = ClaudeCLIClient()
        log(GREEN, "drill", "Using Claude CLI")
    elif shutil.which("chatgpt"):
        llm_client = ChatGPTCLIClient()
        log(GREEN, "drill", "Using ChatGPT CLI")
    elif os.environ.get("ANTHROPIC_API_KEY"):
        llm_client = AnthropicLLMClient(os.environ["ANTHROPIC_API_KEY"])
        log(GREEN, "drill", "Using Anthropic API")
    elif os.environ.get("OPENAI_API_KEY"):
        llm_client = OpenAIClient()
        log(GREEN, "drill", "Using OpenAI API")
    else:
        llm_client = MockLLMClient()
        log(YELLOW, "drill", "No LLM client available — using mock")

    registry = create_tool_registry()
    tool_executor = ToolExecutor(registry)

    try:
        # Create and activate show
        log(BOLD, "drill", f"Task: {task_description}")
        show = create_show(db, title=f"Drill: {task_description[:60]}", description=task_description)
        log(GREEN, "drill", f"Show created: {show.id}")

        show = activate_show(db, show.id)
        log(GREEN, "drill", f"Show activated. Corps: {show.corps_id}, Root coord: {show.coordinate_root_id}")

        # Find the ED session
        from backend.models.agent_session import AgentSession, SessionStatus
        from backend.models.agent_definition import AgentDefinition

        ed_session = (
            db.query(AgentSession)
            .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
            .filter(
                AgentSession.corps_id == show.corps_id,
                AgentDefinition.role == "executive_director",
                AgentSession.status == SessionStatus.ACTIVE,
            )
            .first()
        )

        if not ed_session:
            log(RED, "drill", "No active ED session found!")
            return None

        log(GREEN, "drill", f"Running Executive Director (session: {ed_session.id[:8]}...)")
        print(f"\n{'='*60}")

        start = time.time()
        result = run_agent(
            db=db,
            session_id=ed_session.id,
            llm_client=llm_client,
            tool_executor=tool_executor,
            task_description=(
                f"The show has been activated. The root coordinate ID is {show.coordinate_root_id}. "
                f"The corps ID is {show.corps_id}. "
                f"Task: {task_description}\n\n"
                f"Design the show structure: create MOVEMENT coordinates under the root, "
                f"then hand off to the program_coordinator."
            ),
            on_event=on_event,
        )
        elapsed = time.time() - start

        print(f"{'='*60}\n")
        log(GREEN if result.status == "completed" else RED, "drill",
            f"Result: {result.status} | {result.iterations} iterations | {len(result.tool_calls_made)} tool calls | {elapsed:.1f}s")

        if result.final_response:
            print(f"\n{BOLD}Final Response:{NC}")
            print(result.final_response[:2000])

        if result.error:
            print(f"\n{RED}Error: {result.error}{NC}")

        # Show what was created
        from backend.services.coordinate_service import get_children
        children = get_children(db, show.coordinate_root_id)
        if children:
            print(f"\n{BOLD}Coordinates created:{NC}")
            for c in children:
                print(f"  {c.type.value}: {c.title} [{c.status.value}]")
                sub = get_children(db, c.id)
                for s in sub:
                    print(f"    {s.type.value}: {s.title} [{s.status.value}]")

        return result

    finally:
        db.close()


def run_calibration_loop(problem_ids: list[int]):
    """Run multiple problems in sequence as a calibration sweep."""
    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{BOLD}  DCI SWARM CALIBRATION — {len(problem_ids)} problems{NC}")
    print(f"{BOLD}{'='*60}{NC}\n")

    results = []
    for pid in problem_ids:
        desc = EULER_PROBLEMS.get(pid, f"Project Euler problem #{pid}")
        print(f"\n{BOLD}--- Problem #{pid} ---{NC}")
        result = run_drill(desc)
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
    args = parser.parse_args()

    if args.loop:
        ids = [int(x.strip()) for x in args.loop.split(",")]
        run_calibration_loop(ids)
    elif args.problem:
        desc = EULER_PROBLEMS.get(args.problem, f"Solve Project Euler problem #{args.problem}")
        run_drill(desc)
    elif args.task:
        run_drill(args.task)
    else:
        parser.print_help()
        print(f"\n{BOLD}Available Project Euler problems:{NC}")
        for pid, desc in EULER_PROBLEMS.items():
            print(f"  {pid:>3}. {desc}")


if __name__ == "__main__":
    main()
