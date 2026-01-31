"""Background task manager for running agent sessions asynchronously.

Wraps synchronous run_agent() calls in asyncio.to_thread() and broadcasts
events via WebSocket ConnectionManager. Also runs the metronome on a timer.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Optional

from backend.database import create_db_engine, create_session_factory
from backend.services.agent_runtime import RunStatus, run_agent
from backend.services.autoscaler import AutoScaler
from backend.services.llm_client import LLMClient
from backend.services.message_bus import get_message_bus
from backend.services.session_lookup import find_or_respawn_session
from backend.services.tool_executor import ToolExecutor

if TYPE_CHECKING:
    from backend.api.app import ConnectionManager

logger = logging.getLogger(__name__)

METRONOME_INTERVAL_SECONDS = 30
MAX_AUTO_RETRIES = 3
AUTO_RETRY_ROLES = {"executive_director", "program_coordinator", "drum_major"}


class TaskManager:
    """Manages background agent tasks keyed by session_id."""

    def __init__(self, connection_manager: "ConnectionManager", llm_client: LLMClient, tool_executor: ToolExecutor):
        self.connection_manager = connection_manager
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.active_tasks: dict[str, asyncio.Task] = {}
        self._engine = create_db_engine()
        self._session_factory = create_session_factory(self._engine)
        self._metronome_task: Optional[asyncio.Task] = None
        self._stopped = False
        self.autoscaler = AutoScaler()
        self.message_bus = get_message_bus()
        self._retry_counts: dict[str, int] = {}

    def start_metronome(self) -> None:
        """Start the automatic metronome tick loop."""
        if self._metronome_task is None or self._metronome_task.done():
            self._metronome_task = asyncio.create_task(self._metronome_loop())
            logger.info("Metronome started (every %ds)", METRONOME_INTERVAL_SECONDS)

    def stop(self) -> None:
        """Stop the metronome and all background tasks."""
        self._stopped = True
        if self._metronome_task and not self._metronome_task.done():
            self._metronome_task.cancel()

    async def _metronome_loop(self) -> None:
        """Periodically tick the metronome for all active corps."""
        while not self._stopped:
            try:
                await asyncio.sleep(METRONOME_INTERVAL_SECONDS)
                self.autoscaler.adjust_limits()
                await self._tick_all_corps()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Metronome tick error")

    async def _tick_all_corps(self) -> None:
        """Run metronome tick for every active corps and broadcast results."""
        def _do_tick():
            from backend.models.corps import Corps, CorpsStatus
            from backend.tools.metronome import tick
            from backend.services.corps_service import merge_monitor_check

            db = self._session_factory()
            try:
                active_corps = (
                    db.query(Corps)
                    .filter(Corps.status.in_([CorpsStatus.WINTER_CAMPS, CorpsStatus.ON_TOUR]))
                    .all()
                )
                results = []
                for corps in active_corps:
                    met_result = tick(db, corps.id)
                    merge_result = merge_monitor_check(db, corps.id)

                    # Auto-progression for WINTER_CAMPS corps
                    advancement = None
                    if corps.status == CorpsStatus.WINTER_CAMPS:
                        from backend.services.rehearsal_progression import check_and_advance
                        advancement = check_and_advance(db, corps.id)

                    results.append({
                        "corps_id": corps.id,
                        "corps_status": corps.status.value,
                        "rehearsal_mode": corps.rehearsal_mode.value if corps.rehearsal_mode else None,
                        "metronome": {
                            "checked": met_result.checked,
                            "reclaimed": met_result.reclaimed,
                            "reclaimed_rep_ids": met_result.reclaimed_rep_ids,
                            "idle_kicked": met_result.idle_kicked,
                            "idle_kicked_rep_ids": met_result.idle_kicked_rep_ids,
                        },
                        "merge": {
                            "checked": merge_result.checked,
                            "merged": merge_result.merged,
                            "conflicts": merge_result.conflicts,
                        },
                        "watchdog_respawned": met_result.watchdog_respawned,
                        "rehearsal_advanced": advancement.value if advancement else None,
                    })
                return results
            finally:
                db.close()

        try:
            results = await asyncio.to_thread(_do_tick)
            for r in results:
                corps_id = r["corps_id"]
                met = r["metronome"]
                merge = r["merge"]
                if met["reclaimed"] > 0 or merge["merged"] > 0 or merge["conflicts"] > 0:
                    await self.connection_manager.broadcast(corps_id, {
                        "type": "metronome_tick",
                        "corps_id": corps_id,
                        **met,
                    })
                    if merge["merged"] > 0 or merge["conflicts"] > 0:
                        await self.connection_manager.broadcast(corps_id, {
                            "type": "merge_check",
                            "corps_id": corps_id,
                            **merge,
                        })
            # Broadcast rehearsal advancement
            for r in results:
                if r.get("rehearsal_advanced"):
                    await self.connection_manager.broadcast(r["corps_id"], {
                        "type": "rehearsal_advanced",
                        "corps_id": r["corps_id"],
                        "mode": r["rehearsal_advanced"],
                    })

            # Respawn dead watchdog chain roles
            for r in results:
                corps_id = r["corps_id"]
                for dead_role in r.get("watchdog_respawned", []):
                    db = self._session_factory()
                    try:
                        new_session = self.get_session_for_role(db, corps_id, dead_role)
                        if new_session and not self.is_active(new_session):
                            self.start_agent(
                                session_id=new_session,
                                task_description=f"You are being respawned by the watchdog chain. Resume monitoring duties for role {dead_role}.",
                                corps_id=corps_id,
                            )
                            logger.info("Watchdog respawned %s in corps %s", dead_role, corps_id)
                    finally:
                        db.close()

            # Process orphaned handoff messages for all active corps
            for r in results:
                await self._process_pending_handoffs(r["corps_id"])

            # Feed health summary to timing_judge if issues detected
            for r in results:
                corps_id = r["corps_id"]
                met = r["metronome"]
                merge = r["merge"]
                if met["reclaimed"] > 0 or merge["conflicts"] > 0 or met.get("idle_kicked", 0) > 0:
                    judge_session = self.get_session_for_role(
                        self._session_factory(), corps_id, "timing_judge"
                    )
                    if judge_session and not self.is_active(judge_session):
                        health_summary = (
                            f"Metronome tick results for corps {corps_id}:\n"
                            f"- Reps checked: {met['checked']}, reclaimed: {met['reclaimed']}\n"
                            f"- GUPP idle kicked: {met.get('idle_kicked', 0)}\n"
                            f"- Merge checked: {merge['checked']}, merged: {merge['merged']}, conflicts: {merge['conflicts']}\n"
                            f"Review and escalate any issues."
                        )
                        self.start_agent(
                            session_id=judge_session,
                            task_description=health_summary,
                            corps_id=corps_id,
                        )
            # Ping the DCI admin ED with swarm-wide status
            await self._ping_admin_ed(results)

        except Exception:
            logger.exception("Metronome broadcast error")

    def start_agent(
        self,
        session_id: str,
        task_description: str,
        corps_id: str,
        context_snapshot: Optional[str] = None,
        keep_alive: bool = False,
        reply_to_user: bool = False,
    ) -> None:
        """Start an agent session as a background asyncio task.

        For singleton roles (executive_director), prevents spawning a duplicate
        if one is already running for this corps.

        If keep_alive is True, the agent session stays ACTIVE after completing
        so it can be re-dispatched (e.g. on the next metronome ping).

        If reply_to_user is True, the agent's final response will be persisted
        to the Message table as a user-facing chat reply.
        """
        if session_id in self.active_tasks and not self.active_tasks[session_id].done():
            logger.warning("Session %s already has an active task", session_id)
            return

        # Singleton guard: check if this role already has a running task in this corps
        role, nickname = self._get_agent_identity(session_id)
        if role in self.SINGLETON_ROLES:
            for other_sid, other_task in self.active_tasks.items():
                if other_sid == session_id or other_task.done():
                    continue
                other_role, _ = self._get_agent_identity(other_sid)
                if other_role == role:
                    # Check if same corps
                    db = self._session_factory()
                    try:
                        from backend.models.agent_session import AgentSession
                        other_session = db.get(AgentSession, other_sid)
                        if other_session and other_session.corps_id == corps_id:
                            logger.warning(
                                "Singleton role %s already running in corps %s (session %s), skipping %s",
                                role, corps_id, other_sid, session_id,
                            )
                            return
                    finally:
                        db.close()

        task = asyncio.create_task(
            self._run_agent_task(session_id, task_description, corps_id, context_snapshot, keep_alive, reply_to_user)
        )
        self.active_tasks[session_id] = task
        task.add_done_callback(lambda t: self._on_task_done(session_id, t))

    def _get_agent_identity(self, session_id: str) -> tuple[str, str]:
        """Look up role and nickname for a session. Returns (role, nickname)."""
        db = self._session_factory()
        try:
            from backend.models.agent_session import AgentSession
            from backend.models.agent_definition import AgentDefinition
            session = db.get(AgentSession, session_id)
            if session:
                defn = db.get(AgentDefinition, session.definition_id)
                if defn:
                    return defn.role, defn.nickname or defn.role
            return "unknown", "unknown"
        finally:
            db.close()

    async def _run_agent_task(
        self,
        session_id: str,
        task_description: str,
        corps_id: str,
        context_snapshot: Optional[str] = None,
        keep_alive: bool = False,
        reply_to_user: bool = False,
    ) -> None:
        """Run an agent in a thread and broadcast status events."""
        role, nickname = self._get_agent_identity(session_id)

        await self.connection_manager.broadcast(corps_id, {
            "type": "agent_status",
            "corps_id": corps_id,
            "session_id": session_id,
            "role": role,
            "nickname": nickname,
            "status": "started",
        })

        # Collect events from the sync runtime
        pending_events: list[dict] = []

        def _run():
            db = self._session_factory()
            try:
                def on_event(event: dict):
                    event.setdefault("corps_id", corps_id)
                    event.setdefault("session_id", session_id)
                    event.setdefault("role", role)
                    event.setdefault("nickname", nickname)
                    pending_events.append(event)

                result = run_agent(
                    db=db,
                    session_id=session_id,
                    llm_client=self.llm_client,
                    tool_executor=self.tool_executor,
                    task_description=task_description,
                    context_snapshot=context_snapshot,
                    on_event=on_event,
                    keep_alive=keep_alive,
                )
                return result
            finally:
                db.close()

        try:
            result = await asyncio.to_thread(_run)

            # Broadcast any pending events
            for event in pending_events:
                await self.connection_manager.broadcast(corps_id, event)

            # Broadcast completion
            await self.connection_manager.broadcast(corps_id, {
                "type": "agent_status",
                "corps_id": corps_id,
                "session_id": session_id,
                "role": role,
                "nickname": nickname,
                "status": result.status,
                "final_response": result.final_response,
            })

            if result.final_response:
                # Persist user-facing chat replies to the Message table
                msg_id = None
                if reply_to_user:
                    msg_id = await asyncio.to_thread(
                        self._persist_agent_response, corps_id, session_id, role, result.final_response
                    )
                await self.connection_manager.broadcast(corps_id, {
                    "type": "agent_response",
                    "corps_id": corps_id,
                    "session_id": session_id,
                    "role": role,
                    "nickname": nickname,
                    "from_role": role,
                    "content": result.final_response,
                    "message_id": msg_id,
                })

            # Process pending handoff messages: dispatch receiving agents
            await self._process_pending_handoffs(corps_id)

            # Auto-retry critical roles on failure
            if result.status == RunStatus.FAILED and role in AUTO_RETRY_ROLES:
                retry_count = self._retry_counts.get(session_id, 0)
                if retry_count < MAX_AUTO_RETRIES:
                    self._retry_counts[session_id] = retry_count + 1
                    logger.info(
                        "Auto-retrying %s (attempt %d/%d) for session %s",
                        role, retry_count + 1, MAX_AUTO_RETRIES, session_id,
                    )
                    new_session_id = self.get_session_for_role(
                        self._session_factory(), corps_id, role
                    )
                    if new_session_id:
                        retry_desc = (
                            f"You are resuming after a failure (attempt {retry_count + 2}). "
                            f"Previous error: {result.error or 'unknown'}. "
                            f"Try a different approach if the same strategy failed before.\n\n"
                            f"{task_description}"
                        )
                        self.start_agent(
                            session_id=new_session_id,
                            task_description=retry_desc,
                            corps_id=corps_id,
                            context_snapshot=context_snapshot,
                        )
                        await self.connection_manager.broadcast(corps_id, {
                            "type": "agent_status",
                            "corps_id": corps_id,
                            "session_id": new_session_id,
                            "role": role,
                            "nickname": nickname,
                            "status": "auto_retry",
                            "attempt": retry_count + 2,
                        })

        except Exception as e:
            logger.exception("Agent task failed for session %s", session_id)
            await self.connection_manager.broadcast(corps_id, {
                "type": "agent_status",
                "corps_id": corps_id,
                "session_id": session_id,
                "role": role,
                "nickname": nickname,
                "status": "failed",
                "error": str(e),
            })

    def _persist_agent_response(self, corps_id: str, session_id: str, role: str, content: str) -> Optional[str]:
        """Save an agent response to the Message table so chat history persists across reconnects."""
        try:
            from backend.services.message_service import send_message
            from backend.models.message import MessageType, MessagePriority
            db = self._session_factory()
            try:
                msg = send_message(
                    db, corps_id=corps_id, from_role=role,
                    to_role="user", type=MessageType.STATUS,
                    subject=content[:100], body=content,
                    priority=MessagePriority.NORMAL,
                    from_session_id=session_id,
                )
                return msg.id
            finally:
                db.close()
        except Exception:
            logger.exception("Failed to persist agent response for session %s", session_id)
            return None

    def _on_task_done(self, session_id: str, task: asyncio.Task) -> None:
        self.active_tasks.pop(session_id, None)
        if task.exception():
            logger.error("Background task for %s raised: %s", session_id, task.exception())

    def is_active(self, session_id: str) -> bool:
        task = self.active_tasks.get(session_id)
        return task is not None and not task.done()

    async def _ping_admin_ed(self, tick_results: list[dict]) -> None:
        """Ping the DCI admin ED with swarm-wide status after each metronome cycle.

        The admin ED stays alive and receives periodic status pings. It then
        issues status requests to each corps ED to understand what needs attention.
        """
        def _build_status_and_dispatch():
            from backend.services.corps_service import get_or_create_admin_corps, ADMIN_CORPS_NAME
            from backend.models.corps import Corps, CorpsStatus
            from backend.models.agent_session import AgentSession, SessionStatus
            from backend.models.agent_definition import AgentDefinition
            from backend.models.rep import Rep, RepStatus

            db = self._session_factory()
            try:
                admin_corps = get_or_create_admin_corps(db)

                # Gather swarm-wide status
                active_corps = (
                    db.query(Corps)
                    .filter(
                        Corps.status.in_([CorpsStatus.WINTER_CAMPS, CorpsStatus.ON_TOUR]),
                        Corps.name != ADMIN_CORPS_NAME,
                    )
                    .all()
                )

                if not active_corps and not tick_results:
                    return None  # Nothing to report

                lines = ["METRONOME STATUS PING — Swarm-wide summary:\n"]

                for corps in active_corps:
                    # Count sessions by status
                    sessions = (
                        db.query(AgentSession)
                        .filter(AgentSession.corps_id == corps.id)
                        .all()
                    )
                    active_count = sum(1 for s in sessions if s.status == SessionStatus.ACTIVE)
                    completed_count = sum(1 for s in sessions if s.status == SessionStatus.COMPLETED)
                    failed_count = sum(1 for s in sessions if s.status == SessionStatus.FAILED)

                    # Count reps by status
                    from backend.models.segment import Segment
                    reps = (
                        db.query(Rep)
                        .join(Segment, Rep.segment_id == Segment.id)
                        .filter(Segment.show_id.isnot(None))  # rough filter
                        .all()
                    )
                    # Actually just get reps for this corps via segments
                    # Simpler: count all reps that belong to segments in shows tied to this corps
                    from backend.models.show import Show
                    show = db.query(Show).filter(Show.corps_id == corps.id).first()
                    rep_summary = ""
                    if show and show.segment_root_id:
                        all_reps = db.query(Rep).all()
                        corps_reps = [r for r in all_reps if r.segment_id]
                        pending_reps = sum(1 for r in corps_reps if r.status == RepStatus.PENDING)
                        in_progress_reps = sum(1 for r in corps_reps if r.status == RepStatus.IN_PROGRESS)
                        completed_reps = sum(1 for r in corps_reps if r.status == RepStatus.COMPLETED)
                        failed_reps = sum(1 for r in corps_reps if r.status == RepStatus.FAILED)
                        rep_summary = (
                            f"    Reps: {pending_reps} pending, {in_progress_reps} in-progress, "
                            f"{completed_reps} completed, {failed_reps} failed"
                        )

                    lines.append(
                        f"  Corps '{corps.name}' ({corps.id[:8]}...) [{corps.status.value}]:\n"
                        f"    Sessions: {active_count} active, {completed_count} completed, {failed_count} failed"
                    )
                    if rep_summary:
                        lines.append(rep_summary)

                    # Include tick results for this corps
                    for tr in tick_results:
                        if tr["corps_id"] == corps.id:
                            met = tr["metronome"]
                            if met["reclaimed"] > 0 or met.get("idle_kicked", 0) > 0:
                                lines.append(
                                    f"    Metronome: reclaimed {met['reclaimed']}, "
                                    f"GUPP kicked {met.get('idle_kicked', 0)}"
                                )

                if not active_corps:
                    lines.append("  No active corps currently running.")

                lines.append(
                    "\nReview this status. If any corps needs attention (stuck work, failures, "
                    "idle agents), send a message to the appropriate corps executive_director "
                    "requesting a status update or corrective action. If all corps are healthy, "
                    "acknowledge the status ping briefly."
                )

                status_text = "\n".join(lines)

                # Find or get the admin ED session
                ed_session_id = self.get_session_for_role(db, admin_corps.id, "executive_director")
                if not ed_session_id:
                    return None

                return (ed_session_id, admin_corps.id, status_text)
            finally:
                db.close()

        try:
            result = await asyncio.to_thread(_build_status_and_dispatch)
            if result is None:
                return

            session_id, admin_corps_id, status_text = result

            # Don't ping if the admin ED is already running
            if self.is_active(session_id):
                logger.debug("Admin ED already active, skipping status ping")
                return

            self.start_agent(
                session_id=session_id,
                task_description=status_text,
                corps_id=admin_corps_id,
                keep_alive=True,
            )
            logger.info("Pinged admin ED with swarm status")

        except Exception:
            logger.exception("Error pinging admin ED")

    async def _process_pending_handoffs(self, corps_id: str) -> None:
        """Check for unacknowledged handoff messages and dispatch receiving agents.

        Mode-aware dispatch:
        - WINTER_CAMPS + BASICS: Only dispatch ED and roles it hands off to
        - WINTER_CAMPS + SECTIONALS+: Dispatch within sections
        - ON_TOUR: Full dispatch (all roles)
        """
        def _find_and_dispatch():
            from backend.services.message_service import poll_messages, acknowledge_message, MessageType
            from backend.models.corps import Corps, CorpsStatus, RehearsalMode
            db = self._session_factory()
            try:
                # Check corps mode for dispatch filtering
                corps = db.get(Corps, corps_id)
                basics_only = (
                    corps
                    and corps.status == CorpsStatus.WINTER_CAMPS
                    and corps.rehearsal_mode == RehearsalMode.BASICS
                )
                basics_roles = {"executive_director", "program_coordinator"}

                # Get all unacknowledged messages for this corps
                pending = poll_messages(db, corps_id, unacknowledged_only=True)
                dispatches = []
                for msg in pending:
                    if msg.type != MessageType.HANDOFF or not msg.to_role:
                        continue
                    target_role = msg.to_role

                    # In BASICS mode, only dispatch to ED and PC
                    if basics_only and target_role not in basics_roles:
                        continue
                    session_id = self.get_session_for_role(db, corps_id, target_role)
                    if session_id and not self.is_active(session_id):
                        # Build task description from handoff message
                        task_desc = (
                            f"You have received a handoff from {msg.from_role}.\n\n"
                            f"Subject: {msg.subject}\n"
                        )
                        if msg.body:
                            task_desc += f"\n{msg.body}\n"
                        if msg.segment_id:
                            task_desc += f"\nSegment ID: {msg.segment_id}\n"
                        task_desc += (
                            "\nProcess this handoff by executing the required work. "
                            "Use your tools to inspect the segments and create/complete reps as needed."
                        )
                        acknowledge_message(db, msg.id)
                        dispatches.append((session_id, task_desc, target_role))
                return dispatches
            finally:
                db.close()

        try:
            dispatches = await asyncio.to_thread(_find_and_dispatch)
            for session_id, task_desc, target_role in dispatches:
                logger.info("Dispatching %s for handoff in corps %s", target_role, corps_id)
                self.start_agent(
                    session_id=session_id,
                    task_description=task_desc,
                    corps_id=corps_id,
                )
        except Exception:
            logger.exception("Error processing handoff messages for corps %s", corps_id)

    # Singleton roles: only one active session per corps at a time.
    # New sessions for these roles require the old one to be completed/failed first.
    SINGLETON_ROLES = {"executive_director"}

    def get_session_for_role(self, db, corps_id: str, role: str) -> Optional[str]:
        """Find the session_id for a given role in a corps. Respawns completed sessions."""
        session = find_or_respawn_session(db, corps_id, role)
        if session is None:
            return None
        if role in self.SINGLETON_ROLES and self.is_active(session.id):
            logger.debug("Singleton role %s already active in corps %s", role, corps_id)
        return session.id
