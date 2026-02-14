"""Agent runtime. Connects LLM calls to tool execution and session lifecycle.

The runtime manages the agent loop:
1. Load context (definition prompt + optional snapshot warm-up)
2. Send messages to LLM
3. If LLM requests tool use -> check permissions -> execute -> feed result back
4. Repeat until LLM returns end_turn or max iterations reached
5. Save context snapshot on completion

Enhanced with: failure fingerprinting, agent phases, verification gates,
work logging, message bus events, and task manifest injection.
"""

import enum
import json
import logging
import sys
from dataclasses import dataclass, field
from typing import Callable, Optional

from sqlalchemy.orm import Session

from backend.models.agent_definition import AgentDefinition
from backend.models.agent_session import AgentSession
from backend.services.agent_lifecycle import (
    complete_session,
    fail_session,
)
from backend.services.session_guard import SyncSessionGuard
from backend.services.agent_phases import AgentPhase, PhaseController
from backend.services.failure_fingerprint import FailureFingerprint, FailureRegistry
from backend.services.llm_client import LLMClient, LLMMessage, LLMResponse
from backend.services.message_bus import get_message_bus, AgentPhaseChanged, AgentCompleted
from backend.services.tool_executor import ToolExecutor, ToolPermissionDenied, ToolNotFound
from backend.services.memory_bank import get_memory_bank
from backend.services.verification import VerificationEngine
from backend.utils.snapshot import parse_snapshot

logger = logging.getLogger(__name__)

from backend.services.runtime_config import get_runtime_config as _get_runtime_config

MAX_ITERATIONS = _get_runtime_config()["max_iterations"]


class RunStatus(str, enum.Enum):
    """Status of an agent runtime execution."""
    COMPLETED = "completed"
    FAILED = "failed"
    MAX_ITERATIONS = "max_iterations"


@dataclass
class RunResult:
    """Result of an agent runtime execution."""
    session_id: str
    final_response: str = ""
    tool_calls_made: list[dict] = field(default_factory=list)
    iterations: int = 0
    status: str = RunStatus.COMPLETED
    error: Optional[str] = None
    phase_state: Optional[dict] = None
    model_spec_id: Optional[str] = None
    task_category: Optional[str] = None


# ---- task category inference ----

_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("frontend", ["react", "component", "jsx", "tsx", "css", "html", "ui", "layout", "style", "vite", "tailwind"]),
    ("backend", ["api", "endpoint", "database", "query", "sql", "fastapi", "route", "model", "migration", "server"]),
    ("testing", ["test", "spec", "assert", "pytest", "vitest", "coverage", "mock", "fixture"]),
    ("architecture", ["design", "architecture", "system", "refactor", "pattern", "structure", "module"]),
    ("documentation", ["document", "readme", "docstring", "comment", "explain", "guide"]),
    ("image_gen", ["image", "comfyui", "stable diffusion", "generate image", "logo", "artwork"]),
]


def infer_task_category(description: str, role: str = "") -> str:
    """Infer a task category from description text and agent role.

    Uses simple keyword matching. Returns the category with the most
    keyword hits, defaulting to "general".
    """
    text = f"{description} {role}".lower()
    best_cat = "general"
    best_count = 0

    for category, keywords in _CATEGORY_KEYWORDS:
        count = sum(1 for kw in keywords if kw in text)
        if count > best_count:
            best_count = count
            best_cat = category

    return best_cat


def _get_critique_context(definition: AgentDefinition, db: Session) -> str:
    """Get recent critique action items for this agent's corps + role.

    Takes the caller's DB session instead of creating a private engine (was a leak).
    """
    try:
        from backend.models.critique_session import CritiqueSession, CritiqueStatus

        critiques = db.query(CritiqueSession).filter(
            CritiqueSession.corps_id == definition.corps_id,
            CritiqueSession.status == CritiqueStatus.COMPLETED,
            CritiqueSession.action_items.isnot(None),
        ).order_by(CritiqueSession.completed_at.desc()).limit(3).all()

        if not critiques:
            return ""

        items = []
        for c in critiques:
            if c.action_items:
                items.append(f"[{c.judge_type}] {c.action_items[:300]}")

        if items:
            return "## Recent Critique Feedback\nIn your last performance, judges noted:\n" + "\n".join(items) + "\nFocus on addressing these points."
        return ""
    except Exception:
        return ""


def build_initial_messages(
    definition: AgentDefinition,
    task_description: str,
    context_snapshot: Optional[str] = None,
    phase_guidance: str = "",
    manifest_context: str = "",
    corps_context: str = "",
    db: Optional[Session] = None,
) -> list[LLMMessage]:
    """Build the initial message list for an agent session.

    Includes system prompt from definition, optional warm-up context
    from a previous session's snapshot, phase guidance, corps context
    (status + rehearsal mode guidance), and task manifest.
    """
    system_content = definition.system_prompt
    if phase_guidance:
        system_content += f"\n\n{phase_guidance}"
    if corps_context:
        system_content += f"\n\n{corps_context}"

    # Inject recent critique action items
    if db is not None:
        critique_context = _get_critique_context(definition, db)
        if critique_context:
            system_content += f"\n\n{critique_context}"

    messages = [
        LLMMessage(role="system", content=system_content),
    ]

    if context_snapshot:
        messages.append(
            LLMMessage(
                role="user",
                content=f"Context from previous session:\n{context_snapshot}",
            )
        )
        messages.append(
            LLMMessage(
                role="assistant",
                content="Understood. I have the context from the previous session and will continue from where it left off.",
            )
        )

    # Inject relevant memories from memory bank
    memory_bank = get_memory_bank()
    if memory_bank.available and definition.role:
        agent_identity = definition.nickname or definition.role
        memory_context = memory_bank.get_context_for_task(agent_identity, task_description)
        if memory_context:
            messages.append(
                LLMMessage(role="user", content=memory_context)
            )
            messages.append(
                LLMMessage(role="assistant", content="I'll use these memories to inform my work.")
            )

    task_content = task_description
    if manifest_context:
        task_content += f"\n\n{manifest_context}"

    messages.append(
        LLMMessage(role="user", content=task_content),
    )

    return messages


def _write_work_log(db: Session, event: dict, corps_id: str = "", phase: str = "") -> None:
    """Write an event to the WorkLog table."""
    try:
        from backend.models.work_log import WorkLog
        log_entry = WorkLog(
            session_id=event.get("session_id", ""),
            corps_id=corps_id,
            role=event.get("role", ""),
            event_type=event.get("type", ""),
            phase=phase,
            details=json.dumps({k: v for k, v in event.items()
                                if k not in ("type", "role", "session_id")}),
        )
        db.add(log_entry)
        db.commit()
    except Exception:
        logger.debug("Work log write failed", exc_info=True)


def run_agent(
    db: Session,
    session_id: str,
    llm_client: LLMClient,
    tool_executor: ToolExecutor,
    task_description: str,
    context_snapshot: Optional[str] = None,
    max_iterations: int = MAX_ITERATIONS,
    on_event: Optional[Callable[[dict], None]] = None,
    keep_alive: bool = False,
    verification_engine: Optional[VerificationEngine] = None,
    manifest_context: str = "",
) -> RunResult:
    """Execute the agent loop for a session.

    Returns a RunResult with the final response, tool calls made, and status.
    """
    def _emit(event: dict) -> None:
        if on_event:
            on_event(event)
        # Persist to WorkLog
        try:
            from backend.models.work_log import WorkLog
            log = WorkLog(
                session_id=session_id,
                corps_id=event.get("corps_id", ""),
                role=event.get("role", ""),
                event_type=event.get("type", "unknown"),
                phase=event.get("phase"),
                details=str(event.get("detail", event.get("content", "")))[:2000] or None,
            )
            db.add(log)
            db.commit()
        except Exception:
            logger.debug("Work log write failed", exc_info=True)

    # RAII guard: guarantees session cleanup + child cascade on unhandled crash.
    # The guard is a safety net — run_agent still calls complete_session/fail_session
    # explicitly on happy/error paths. The guard only fires if those are never reached.
    guard = SyncSessionGuard(db, session_id, cascade_children=True)

    agent_session = db.get(AgentSession, session_id)
    if agent_session is None:
        raise ValueError(f"Session {session_id} not found")

    definition = db.get(AgentDefinition, agent_session.definition_id)
    if definition is None:
        raise ValueError(f"Definition {agent_session.definition_id} not found")

    # Initialize phase controller and failure registry from snapshot
    snap = parse_snapshot(context_snapshot)
    phase_controller = PhaseController()
    if "phase_state" in snap:
        phase_controller = PhaseController.from_state(snap["phase_state"])

    failure_registry = FailureRegistry()
    if "failure_fingerprints" in snap:
        failure_registry.load_fingerprints(snap["failure_fingerprints"])

    corps_id = agent_session.corps_id or ""
    bus = get_message_bus()

    # Look up corps context (status + rehearsal mode guidance)
    corps_context_str = ""
    if corps_id:
        try:
            from backend.services.corps_service import get_corps_context
            corps_context_str = get_corps_context(db, corps_id, role=definition.role)
        except Exception:
            logger.debug("Failed to load corps context", exc_info=True)

    # Load drill book context for this agent's corps + role
    drill_context_str = ""
    if corps_id:
        try:
            from backend.services.drill_book_service import list_books, get_resumption_context
            from backend.services.vector_store import search_drill_context
            from backend.models.drill_book import BookStatus

            active_books = list_books(db, corps_id=corps_id, role=definition.role)
            active_books = [b for b in active_books if b.status not in (
                BookStatus.COMPLETED, BookStatus.VERIFIED,
                BookStatus.FAILED, BookStatus.ABANDONED,
            )]

            if active_books:
                parts = ["## Active Drill Books"]
                for book in active_books[:3]:  # Cap at 3 to avoid prompt bloat
                    ctx = get_resumption_context(db, book.id)
                    status_label = ctx['status']
                    if status_label == "blocked":
                        status_label = "BLOCKED — investigate why and escalate if needed"
                    parts.append(
                        f"### {ctx['title']} (status: {status_label})\n"
                        f"{ctx['description']}\n"
                        f"Progress: {ctx['progress']['completed']}/{ctx['progress']['total']} steps done\n"
                        f"Next steps: {', '.join(ctx['next_step_ids'][:3]) or 'none'}"
                    )
                    if ctx.get("context_summary"):
                        parts.append(f"Context: {ctx['context_summary'][:300]}")
                    # Deserialize context_snapshot for cold-resume data
                    if ctx.get("context_snapshot"):
                        snap_data = ctx["context_snapshot"]
                        if isinstance(snap_data, dict):
                            snap_keys = [k for k in snap_data.keys() if k not in ("phase_state", "failure_fingerprints")]
                            if snap_keys:
                                snap_summary = ", ".join(f"{k}: {str(snap_data[k])[:80]}" for k in snap_keys[:5])
                                parts.append(f"Snapshot: {snap_summary}")
                drill_context_str = "\n".join(parts)

            # Search vector store for relevant prior drill outcomes
            similar = search_drill_context(
                task_description[:200], top_k=3, corps_id=corps_id, role=definition.role
            )
            if similar:
                prior_parts = ["## Prior Drill Outcomes"]
                for hit in similar:
                    prior_parts.append(f"- {hit['document'][:200]}")
                drill_context_str += "\n" + "\n".join(prior_parts) if drill_context_str else "\n".join(prior_parts)
        except Exception:
            logger.debug("Failed to load drill book context", exc_info=True)

    # Merge drill context into manifest_context
    if drill_context_str:
        manifest_context = f"{manifest_context}\n\n{drill_context_str}" if manifest_context else drill_context_str

    from backend.models.work_log import WorkLogEventType

    _emit({
        "type": "agent_status",
        "role": definition.role,
        "session_id": session_id,
        "status": "running",
        "phase": phase_controller.current_phase.value,
    })
    _write_work_log(db, {
        "type": WorkLogEventType.AGENT_START, "role": definition.role,
        "session_id": session_id, "task": task_description[:500],
    }, corps_id, phase_controller.current_phase.value)

    messages = build_initial_messages(
        definition, task_description, context_snapshot,
        phase_guidance=phase_controller.get_guidance(),
        manifest_context=manifest_context,
        corps_context=corps_context_str,
        db=db,
    )
    tool_schemas = tool_executor.registry.get_schemas_for_session(db, session_id)

    # --- Model spec selection ---
    task_category = infer_task_category(task_description, definition.role)
    model_override: Optional[str] = None
    selected_spec_id: Optional[str] = None

    try:
        from backend.services.model_spec_selector import select_model_spec
        spec = select_model_spec(db, corps_id or None, task_category, definition)
        if spec is not None:
            model_override = spec.model_id
            selected_spec_id = spec.id
            logger.debug(
                "Selected model spec %s (%s) for task category %s",
                spec.name, spec.model_id, task_category,
            )
    except Exception:
        logger.debug("Model spec selection failed, using default tier", exc_info=True)

    result = RunResult(
        session_id=session_id,
        model_spec_id=selected_spec_id,
        task_category=task_category,
    )
    guard.__enter__()

    try:
        for i in range(max_iterations):
            result.iterations = i + 1

            _write_work_log(db, {
                "type": WorkLogEventType.LLM_REQUEST, "role": definition.role,
                "session_id": session_id, "iteration": i + 1,
                "message_count": len(messages),
            }, corps_id, phase_controller.current_phase.value)

            chat_kwargs: dict = {"session_id": session_id}
            if model_override:
                chat_kwargs["model_override"] = model_override

            response = llm_client.chat(
                messages=messages,
                model_tier=definition.model_tier,
                tools=tool_schemas if tool_schemas else None,
                **chat_kwargs,
            )

            _write_work_log(db, {
                "type": WorkLogEventType.LLM_RESPONSE, "role": definition.role,
                "session_id": session_id, "iteration": i + 1,
                "stop_reason": response.stop_reason,
                "has_tool_use": response.wants_tool_use,
                "tool_count": len(response.tool_calls) if response.tool_calls else 0,
            }, corps_id, phase_controller.current_phase.value)

            if response.stop_reason == "error":
                result.final_response = response.content
                result.status = RunStatus.FAILED
                result.error = response.content
                _emit({
                    "type": "agent_response",
                    "role": definition.role,
                    "session_id": session_id,
                    "content": response.content,
                })
                break

            if not response.wants_tool_use:
                result.final_response = response.content
                result.status = RunStatus.COMPLETED

                _emit({
                    "type": "agent_response",
                    "role": definition.role,
                    "session_id": session_id,
                    "content": response.content,
                })

                # Advance to REPORT phase
                if phase_controller.current_phase not in (AgentPhase.REPORT, AgentPhase.COOL_DOWN):
                    old_phase = phase_controller.current_phase
                    phase_controller.set_phase(AgentPhase.REPORT)
                    bus.publish("agent.phase_changed", AgentPhaseChanged(
                        session_id=session_id, role=definition.role,
                        old_phase=old_phase.value, new_phase=AgentPhase.REPORT.value,
                        corps_id=corps_id,
                    ))
                break

            # Process tool calls
            for tool_call in response.tool_calls:
                # Phase detection from tool usage
                old_phase = phase_controller.current_phase
                phase_controller.detect_phase_from_tool(tool_call.tool_name)
                if phase_controller.current_phase != old_phase:
                    bus.publish("agent.phase_changed", AgentPhaseChanged(
                        session_id=session_id, role=definition.role,
                        old_phase=old_phase.value,
                        new_phase=phase_controller.current_phase.value,
                        corps_id=corps_id,
                    ))

                _emit({
                    "type": "tool_call",
                    "role": definition.role,
                    "session_id": session_id,
                    "tool": tool_call.tool_name,
                    "args": tool_call.arguments,
                    "phase": phase_controller.current_phase.value,
                })
                _write_work_log(db, {
                    "type": WorkLogEventType.TOOL_CALL, "role": definition.role,
                    "session_id": session_id, "tool": tool_call.tool_name,
                    "args": tool_call.arguments,
                }, corps_id, phase_controller.current_phase.value)

                # Check failure fingerprint before executing
                fp = FailureFingerprint(tool_name=tool_call.tool_name, args=tool_call.arguments, error="")
                guidance = None
                # Check if a similar call (same tool+args) has failed repeatedly
                for existing_key, existing_fp in failure_registry._fingerprints.items():
                    if existing_fp.tool_name == tool_call.tool_name and existing_fp.args == tool_call.arguments:
                        guidance = failure_registry.get_guidance(existing_fp)
                        break

                if guidance:
                    tool_result_data = {"success": False, "output": None, "error": guidance}
                    _emit({
                        "type": "tool_result",
                        "role": definition.role,
                        "session_id": session_id,
                        "tool": tool_call.tool_name,
                        "result": tool_result_data,
                        "blocked_by_fingerprint": True,
                    })
                else:
                    tool_result_data = _execute_tool_call(
                        db, session_id, tool_executor, tool_call.tool_name, tool_call.arguments
                    )

                    # Record failure fingerprint if tool failed
                    if not tool_result_data.get("success"):
                        error_msg = tool_result_data.get("error", "unknown error")
                        fp = FailureFingerprint(
                            tool_name=tool_call.tool_name,
                            args=tool_call.arguments,
                            error=error_msg,
                        )
                        failure_registry.record_failure(fp)

                result.tool_calls_made.append({
                    "tool": tool_call.tool_name,
                    "arguments": tool_call.arguments,
                    "result": tool_result_data,
                })

                _emit({
                    "type": "tool_result",
                    "role": definition.role,
                    "session_id": session_id,
                    "tool": tool_call.tool_name,
                    "result": tool_result_data,
                })
                _write_work_log(db, {
                    "type": WorkLogEventType.TOOL_SUCCESS if tool_result_data.get("success") else WorkLogEventType.TOOL_ERROR,
                    "role": definition.role,
                    "session_id": session_id, "tool": tool_call.tool_name,
                    "success": tool_result_data.get("success"),
                    "error": tool_result_data.get("error") if not tool_result_data.get("success") else None,
                }, corps_id, phase_controller.current_phase.value)

                # Feed tool result back into conversation
                messages.append(
                    LLMMessage(role="assistant", content=response.content or f"[tool_use: {tool_call.tool_name}]")
                )
                messages.append(
                    LLMMessage(
                        role="user",
                        content=f"Tool result for {tool_call.tool_name}: {json.dumps(tool_result_data)}",
                    )
                )
        else:
            result.status = RunStatus.MAX_ITERATIONS

        # Save snapshot with phase state and failure fingerprints
        result.phase_state = phase_controller.get_state()
        snapshot = json.dumps({
            "final_response": result.final_response,
            "tool_calls": result.tool_calls_made,
            "iterations": result.iterations,
            "phase_state": result.phase_state,
            "failure_fingerprints": failure_registry.get_all_fingerprints(),
        })
        if keep_alive:
            agent_session = db.get(AgentSession, session_id)
            if agent_session:
                agent_session.context_snapshot = snapshot
                db.commit()
        else:
            complete_session(db, session_id, context_snapshot=snapshot)

        guard.mark_completed()

        # Clean up CLI session so it doesn't pollute the user's resume list
        llm_client.cleanup_session(session_id)

        _emit({
            "type": "agent_status",
            "role": definition.role,
            "session_id": session_id,
            "status": result.status,
            "phase": phase_controller.current_phase.value,
        })
        _write_work_log(db, {
            "type": WorkLogEventType.AGENT_COMPLETE if result.status == RunStatus.COMPLETED else WorkLogEventType.AGENT_FAIL,
            "role": definition.role,
            "session_id": session_id, "status": result.status,
            "iterations": result.iterations,
            "tool_calls_count": len(result.tool_calls_made),
        }, corps_id, phase_controller.current_phase.value)

        bus.publish("agent.completed", AgentCompleted(
            session_id=session_id, role=definition.role,
            status=result.status, corps_id=corps_id,
        ))

        # Store session summary in memory bank
        try:
            memory_bank = get_memory_bank()
            if memory_bank.available and result.final_response:
                agent_identity = definition.nickname or definition.role
                summary = (
                    f"Task: {task_description[:500]}\n"
                    f"Result ({result.status}): {result.final_response[:1000]}\n"
                    f"Tools used: {len(result.tool_calls_made)}, Iterations: {result.iterations}"
                )
                memory_bank.store_session_summary(
                    agent_identity=agent_identity,
                    session_id=session_id,
                    role=definition.role,
                    summary=summary,
                    corps_id=corps_id,
                )
        except Exception:
            logger.debug("Memory bank storage failed", exc_info=True)

        # Index completed drill book outcomes in vector store
        if corps_id and result.status == RunStatus.COMPLETED:
            try:
                from backend.services.drill_book_service import list_books as _list_books
                from backend.services.vector_store import store_drill_context
                from backend.models.drill_book import BookStatus as _BookStatus

                completed_books = _list_books(db, corps_id=corps_id, role=definition.role, status=_BookStatus.COMPLETED)
                for book in completed_books[:5]:
                    store_drill_context(
                        book_id=book.id,
                        summary=f"{book.title}: {book.description[:300]}",
                        outcome=book.context_summary or result.final_response[:300],
                        corps_id=corps_id,
                        role=definition.role or "",
                    )
            except Exception:
                logger.debug("Drill book vector store indexing failed", exc_info=True)

        # Record model spec outcome for the feedback loop
        if selected_spec_id and task_category:
            try:
                from backend.services.model_spec_service import record_model_spec_outcome
                success = result.status == RunStatus.COMPLETED
                # Simple score: completed=80 base + iteration bonus, failed=20
                score = 80.0 + max(0, 10 - result.iterations) if success else 20.0
                record_model_spec_outcome(
                    db, selected_spec_id, task_category, score, success,
                    corps_id=corps_id or None,
                )
            except Exception:
                logger.debug("Model spec outcome recording failed", exc_info=True)

    except Exception as e:
        result.status = "failed"
        result.error = str(e)

        _emit({
            "type": "agent_status",
            "role": definition.role,
            "session_id": session_id,
            "status": "failed",
            "error": str(e),
        })
        _write_work_log(db, {
            "type": WorkLogEventType.AGENT_FAIL, "role": definition.role,
            "session_id": session_id, "status": "failed", "error": str(e),
            "iterations": result.iterations,
        }, corps_id, phase_controller.current_phase.value)

        # Store failure lesson in memory bank
        try:
            memory_bank = get_memory_bank()
            if memory_bank.available:
                agent_identity = definition.nickname or definition.role
                memory_bank.store_failure_lesson(
                    agent_identity=agent_identity,
                    session_id=session_id,
                    what_failed=task_description[:300],
                    lesson=f"Failed with error: {str(e)[:500]}. "
                           f"Tools attempted: {[tc['tool'] for tc in result.tool_calls_made]}",
                )
        except Exception:
            pass

        # Save snapshot on failure so respawned sessions get context
        try:
            result.phase_state = phase_controller.get_state()
            failure_snapshot = json.dumps({
                "final_response": result.final_response,
                "tool_calls": result.tool_calls_made,
                "iterations": result.iterations,
                "phase_state": result.phase_state,
                "failure_fingerprints": failure_registry.get_all_fingerprints(),
                "failed": True,
                "failure_reason": str(e),
                "task_description": task_description,
            })
            fail_session(db, session_id, error=str(e), context_snapshot=failure_snapshot)
        except Exception:
            try:
                fail_session(db, session_id, error=str(e))
            except Exception:
                pass  # Session may already be in terminal state

        guard.mark_failed()

        # Clean up CLI session on failure too
        llm_client.cleanup_session(session_id)

    finally:
        # Safety net: if guard wasn't marked, __exit__ will fail the session
        # and cascade-kill children. No-op if already marked.
        guard.__exit__(*sys.exc_info())

    return result


def _execute_tool_call(
    db: Session,
    session_id: str,
    tool_executor: ToolExecutor,
    tool_name: str,
    arguments: dict,
) -> dict:
    """Execute a single tool call, returning a result dict."""
    try:
        tool_result = tool_executor.execute(db, session_id, tool_name, arguments)
        return {"success": tool_result.success, "output": tool_result.output, "error": tool_result.error}
    except ToolPermissionDenied as e:
        return {"success": False, "output": None, "error": str(e)}
    except ToolNotFound as e:
        return {"success": False, "output": None, "error": str(e)}
