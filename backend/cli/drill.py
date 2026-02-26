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
import re
import sys
import os
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv

load_dotenv()  # Load .env file if present


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


# --- Euler answer verification ---

_euler_answer_cache: Optional[dict[int, str]] = None


def fetch_euler_answers() -> dict[int, str]:
    """Fetch known Euler answers from Nayuki's published answer list.

    Project Euler doesn't publish answers publicly. Nayuki's GitHub repo
    maintains a verified Answers.txt with one answer per line (line N = problem N).
    https://github.com/nayuki/Project-Euler-solutions/blob/master/Answers.txt
    """
    url = "https://raw.githubusercontent.com/nayuki/Project-Euler-solutions/master/Answers.txt"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "dci-swarm-drill/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            lines = resp.read().decode().strip().split("\n")
        return {i + 1: line.strip() for i, line in enumerate(lines) if line.strip()}
    except Exception:
        return {}


def get_euler_answer(problem_id: int) -> Optional[str]:
    global _euler_answer_cache
    if _euler_answer_cache is None:
        _euler_answer_cache = fetch_euler_answers()
    return _euler_answer_cache.get(problem_id)


@dataclass
class DrillVerdict:
    passed: bool
    answer_correct: Optional[bool]
    expected_answer: Optional[str]
    found_answer: Optional[str]
    reps_total: int
    reps_verified: int
    reps_passed_gates: int
    gate_failures: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)


def verify_drill(db, root_id: str, problem_id: Optional[int] = None) -> DrillVerdict:
    """Verify drill results: run verification gates and check Euler answer."""
    from backend.services.tree_service import build_tree_dict
    from backend.services.verification import get_verification_engine

    tree = build_tree_dict(db, root_id)
    engine = get_verification_engine()

    # Collect all completed rep results
    all_results = []
    _collect_rep_results(tree, all_results)

    reps_total = len(all_results)
    reps_verified = 0
    reps_passed = 0
    gate_failures = []

    for rep_info in all_results:
        result_text = rep_info.get("result", "") or ""
        rep_id = rep_info.get("id", "?")
        vr = engine.verify(rep_id=rep_id, result=result_text)
        reps_verified += 1
        if vr.passed:
            reps_passed += 1
        else:
            for g in vr.failed_gates:
                gate_failures.append(f"rep {rep_id[:8]}: {g.gate_name} — {g.message or 'failed'}")

    # Check Euler answer
    expected = get_euler_answer(problem_id) if problem_id else None
    found_answer = None
    answer_correct = None

    if expected:
        # Search all rep results for the expected numeric answer
        all_text = " ".join(r.get("result", "") or "" for r in all_results)
        # Extract all numbers from rep results
        numbers = re.findall(r'\b\d+\b', all_text)
        if expected in numbers:
            found_answer = expected
            answer_correct = True
        elif numbers:
            # Report the largest number found as a candidate
            found_answer = max(numbers, key=lambda x: len(x))
            answer_correct = False
        else:
            answer_correct = False

    passed = (reps_passed > 0 and answer_correct is True) if expected else (reps_passed > 0)

    return DrillVerdict(
        passed=passed,
        answer_correct=answer_correct,
        expected_answer=expected,
        found_answer=found_answer,
        reps_total=reps_total,
        reps_verified=reps_verified,
        reps_passed_gates=reps_passed,
        gate_failures=gate_failures,
        details=[],
    )


def _collect_rep_results(node: dict, results: list):
    """Recursively collect rep result dicts from a tree dict."""
    for rep in node.get("reps", []):
        results.append(rep)
    for child in node.get("children", []):
        _collect_rep_results(child, results)


def print_verdict(verdict: DrillVerdict):
    """Print a color-coded PASS/FAIL verdict."""
    print(f"\n{'='*60}")
    if verdict.passed:
        print(f"  {GREEN}{BOLD}PASS{NC}")
    else:
        print(f"  {RED}{BOLD}FAIL{NC}")
    print(f"{'='*60}")

    if verdict.expected_answer:
        print(f"  Expected: {CYAN}{verdict.expected_answer}{NC} (from Nayuki's verified list)")
        if verdict.found_answer:
            match = f"{GREEN}✓{NC}" if verdict.answer_correct else f"{RED}✗{NC}"
            print(f"  Found:    {CYAN}{verdict.found_answer}{NC} {match}")
        else:
            print(f"  Found:    {RED}NOT FOUND{NC}")

    print(f"  Reps: {verdict.reps_passed_gates}/{verdict.reps_verified} passed gates (of {verdict.reps_total} total)")

    if verdict.gate_failures:
        print(f"  Gate failures:")
        for f in verdict.gate_failures[:10]:
            print(f"    {RED}• {f}{NC}")

    print()


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
        from backend.services.agent_runtime import RunStatus
        color = GREEN if status in ("running", RunStatus.COMPLETED) else RED if status == RunStatus.FAILED else YELLOW
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
        elif os.environ.get("ANTHROPIC_SDK_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"):
            inner = AnthropicLLMClient()
        log(YELLOW, "drill", "Dry-run: using SimulationLLMClient")
        return SimulationLLMClient(inner)

    clients = []

    if shutil.which("claude"):
        clients.append(("claude_cli", ClaudeCLIClient()))
    if os.environ.get("ANTHROPIC_SDK_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"):
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
    """Find or create an active agent session for a role in a corps."""
    from backend.services.session_lookup import find_or_respawn_session
    session = find_or_respawn_session(db, corps_id, role)
    if session:
        log(DIM, "orchestrator", f"Session for {role}: {session.id[:8]}...")
    return session


def run_agent_for_role(db, role, session, llm_client, tool_executor, task_desc, corps_id):
    """Run a single agent and return the result."""
    from backend.services.agent_runtime import run_agent

    log(MAGENTA, "orchestrator", f"Dispatching {role} (session: {session.id[:8]}...)")
    print(f"\n{'-'*40}")

    # Load previous context snapshot for continuity
    context_snapshot = session.context_snapshot

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

    from backend.services.agent_runtime import RunStatus
    status_color = GREEN if result.status == RunStatus.COMPLETED else RED
    log(status_color, role,
        f"Done: {result.status} | {result.iterations} iters | {len(result.tool_calls_made)} tools | {elapsed:.1f}s")

    if result.error:
        log(RED, role, f"Error: {result.error}")

    return result


def run_orchestration_loop(db, corps_id, root_coord_id, llm_client, tool_executor, max_rounds=50):
    """Poll for handoff messages and dispatch agents until all work is done."""
    from backend.services.agent_runtime import RunStatus
    from backend.services.message_service import poll_messages, acknowledge_message
    from backend.models.message import MessageType
    from backend.models.rep import RepStatus
    from backend.models.corps import Corps
    from backend.models.rehearsal_mode import RehearsalMode
    from backend.services.rep_service import get_reps_for_segment
    from backend.services.segment_service import get_children
    from backend.services.rehearsal_progression import check_and_advance

    BASICS_ROLES = {"executive_director", "program_coordinator"}
    SECTIONALS_ROLES = BASICS_ROLES | {"caption_head_music", "caption_head_visual", "caption_head_movement"}

    print(f"\n{BOLD}{'='*60}{NC}")
    log(MAGENTA, "orchestrator", "Starting orchestration loop")
    print(f"{'='*60}")

    total_agents_run = 0

    for round_num in range(1, max_rounds + 1):
        # Check rehearsal mode and auto-advance
        corps = db.get(Corps, corps_id)
        current_mode = corps.rehearsal_mode if corps else None
        new_mode = check_and_advance(db, corps_id)
        if new_mode and new_mode != current_mode:
            log(CYAN, "orchestrator", f"Rehearsal mode advanced: {current_mode} → {new_mode}")

        log(MAGENTA, "orchestrator", f"--- Round {round_num}/{max_rounds} (mode: {corps.rehearsal_mode if corps else '?'}) ---")

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
                        if result.status == RunStatus.FAILED:
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

            # Mode-aware dispatch: skip agents not allowed in current rehearsal mode
            corps = db.get(Corps, corps_id)
            mode = corps.rehearsal_mode if corps else None
            if mode == RehearsalMode.BASICS and role not in BASICS_ROLES:
                log(DIM, "orchestrator", f"Skipping {role} — not allowed in BASICS mode")
                acknowledge_message(db, msg.id)
                continue
            if mode == RehearsalMode.SECTIONALS and role not in SECTIONALS_ROLES:
                log(DIM, "orchestrator", f"Skipping {role} — not allowed in SECTIONALS mode")
                acknowledge_message(db, msg.id)
                continue

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

            if result.status == RunStatus.FAILED:
                log(RED, "orchestrator", f"Agent {role} failed — continuing with remaining work")

        # Brief pause between rounds
        time.sleep(0.5)

    log(MAGENTA, "orchestrator", f"Orchestration complete: {total_agents_run} agents dispatched over {round_num} rounds")
    return total_agents_run


def _build_tree_summary(db, root_coord_id) -> str:
    """Build a text summary of the segment tree with IDs."""
    from backend.services.tree_service import build_tree_summary
    return build_tree_summary(db, root_coord_id)


def _check_pending_work(db, root_coord_id) -> int:
    """Count pending work: reps not in terminal state + leaf segments with no reps."""
    from backend.services.tree_service import count_pending_work
    return count_pending_work(db, root_coord_id)


def print_final_summary(db, root_coord_id):
    """Print the final segment tree and rep results."""
    from backend.services.segment_service import get_children
    from backend.services.rep_service import get_reps_for_segment

    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{BOLD}  FINAL STATE{NC}")
    print(f"{'='*60}")

    def print_tree(coord_id, indent=0):
        from backend.services.segment_service import get_segment
        from backend.models.segment import SegmentStatus
        from backend.models.rep import RepStatus
        coord = get_segment(db, coord_id)
        if not coord:
            return

        status_color = GREEN if coord.status == SegmentStatus.COMPLETED else RED if coord.status == SegmentStatus.FAILED else YELLOW
        prefix = "  " * indent
        print(f"{prefix}{status_color}{coord.type.value}: {coord.title} [{coord.status.value}]{NC}")

        reps = get_reps_for_segment(db, coord_id)
        for rep in reps:
            rep_color = GREEN if rep.status == RepStatus.COMPLETED else RED if rep.status == RepStatus.FAILED else YELLOW
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

        from backend.services.agent_runtime import RunStatus
        ed_color = GREEN if ed_result.status == RunStatus.COMPLETED else RED
        log(ed_color, "drill",
            f"ED: {ed_result.status} | {ed_result.iterations} iters | {len(ed_result.tool_calls_made)} tools | {elapsed:.1f}s")

        if ed_result.status == RunStatus.FAILED:
            log(RED, "drill", f"ED failed: {ed_result.error}")
            print_final_summary(db, show.segment_root_id)
            return ed_result

        # ED recovery: check if segments were actually created
        from backend.services.segment_service import get_children
        children = get_children(db, show.segment_root_id)
        ed_retries = 0
        while not children and ed_retries < 2:
            ed_retries += 1
            log(YELLOW, "drill", f"ED produced no segments — retry {ed_retries}/2 with corrective guidance")
            ed_session = find_session_for_role(db, show.corps_id, "executive_director")
            if not ed_session:
                break
            ed_result = run_agent(
                db=db,
                session_id=ed_session.id,
                llm_client=llm_client,
                tool_executor=tool_executor,
                task_description=(
                    f"Root segment ID: {show.segment_root_id}. Task: {task_description}\n\n"
                    f"You MUST call create_segment to create MOVEMENT segments under root ID {show.segment_root_id}, "
                    f"then call handoff to hand off to program_coordinator. "
                    f"Do NOT include corps_id or from_role in tool calls — they are auto-injected."
                ),
                on_event=on_event,
                keep_alive=True,
            )
            children = get_children(db, show.segment_root_id)

        if not children:
            log(RED, "drill", "ED failed to create any segments after retries")
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

        # Verification: check results against expected answer
        problem_id = _extract_problem_id(task_description)
        verdict = verify_drill(db, show.segment_root_id, problem_id)
        print_verdict(verdict)

        return verdict

    finally:
        db.close()


def _extract_problem_id(task_description: str) -> Optional[int]:
    """Try to extract a Project Euler problem number from the task description."""
    for pid, desc in EULER_PROBLEMS.items():
        if desc in task_description:
            return pid
    m = re.search(r'[Ee]uler\s*#?\s*(\d+)', task_description)
    if m:
        return int(m.group(1))
    return None


def run_calibration_loop(problem_ids: list[int], max_rounds: int = 50):
    """Run multiple problems in sequence as a calibration sweep."""
    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{BOLD}  DCI SWARM CALIBRATION — {len(problem_ids)} problems{NC}")
    print(f"{BOLD}{'='*60}{NC}\n")

    results = []
    for pid in problem_ids:
        desc = EULER_PROBLEMS.get(pid, f"Project Euler problem #{pid}")
        print(f"\n{BOLD}--- Problem #{pid} ---{NC}")
        verdict = run_drill(desc, max_rounds=max_rounds)
        if isinstance(verdict, DrillVerdict):
            results.append({
                "problem": pid,
                "passed": verdict.passed,
                "expected": verdict.expected_answer,
                "found": verdict.found_answer,
                "answer_correct": verdict.answer_correct,
                "reps_verified": verdict.reps_verified,
                "reps_total": verdict.reps_total,
                "reps_passed": verdict.reps_passed_gates,
            })
        else:
            results.append({
                "problem": pid, "passed": False,
                "expected": get_euler_answer(pid), "found": None,
                "answer_correct": None, "reps_verified": 0,
                "reps_total": 0, "reps_passed": 0,
            })
        print()

    # Summary
    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{BOLD}  CALIBRATION SUMMARY{NC}")
    print(f"{BOLD}{'='*60}{NC}")
    for r in results:
        status_color = GREEN if r["passed"] else RED
        status = "PASS" if r["passed"] else "FAIL"
        expected = r.get("expected", "?")
        found = r.get("found") or "NOT FOUND"
        match = "✓" if r.get("answer_correct") else "✗" if r.get("answer_correct") is False else "?"
        print(f"  Problem #{r['problem']:>3}  {status_color}{status:>4}{NC}  "
              f"Expected: {expected}  Found: {found} {match}  "
              f"Reps: {r['reps_passed']}/{r['reps_verified']} verified")


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
