"""Background task manager for running agent sessions asynchronously.

Wraps synchronous run_agent() calls in asyncio.to_thread() and broadcasts
events via WebSocket ConnectionManager. Also runs the metronome on a timer.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Optional

from backend.database import create_db_engine, create_session_factory
from backend.services.agent_runtime import run_agent
from backend.services.autoscaler import AutoScaler
from backend.services.llm_client import LLMClient
from backend.services.message_bus import get_message_bus
from backend.services.tool_executor import ToolExecutor

if TYPE_CHECKING:
    from backend.api.app import ConnectionManager

logger = logging.getLogger(__name__)

METRONOME_INTERVAL_SECONDS = 30


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
                    .filter(Corps.status.in_([CorpsStatus.REHEARSAL, CorpsStatus.TOUR]))
                    .all()
                )
                results = []
                for corps in active_corps:
                    met_result = tick(db, corps.id)
                    merge_result = merge_monitor_check(db, corps.id)
                    results.append({
                        "corps_id": corps.id,
                        "metronome": {
                            "checked": met_result.checked,
                            "reclaimed": met_result.reclaimed,
                            "reclaimed_rep_ids": met_result.reclaimed_rep_ids,
                        },
                        "merge": {
                            "checked": merge_result.checked,
                            "merged": merge_result.merged,
                            "conflicts": merge_result.conflicts,
                        },
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
            # Feed health summary to timing_judge if issues detected
            for r in results:
                corps_id = r["corps_id"]
                met = r["metronome"]
                merge = r["merge"]
                if met["reclaimed"] > 0 or merge["conflicts"] > 0:
                    judge_session = self.get_session_for_role(
                        self._session_factory(), corps_id, "timing_judge"
                    )
                    if judge_session and not self.is_active(judge_session):
                        health_summary = (
                            f"Metronome tick results for corps {corps_id}:\n"
                            f"- Reps checked: {met['checked']}, reclaimed: {met['reclaimed']}\n"
                            f"- Merge checked: {merge['checked']}, merged: {merge['merged']}, conflicts: {merge['conflicts']}\n"
                            f"Review and escalate any issues."
                        )
                        self.start_agent(
                            session_id=judge_session,
                            task_description=health_summary,
                            corps_id=corps_id,
                        )
        except Exception:
            logger.exception("Metronome broadcast error")

    def start_agent(
        self,
        session_id: str,
        task_description: str,
        corps_id: str,
        context_snapshot: Optional[str] = None,
    ) -> None:
        """Start an agent session as a background asyncio task."""
        if session_id in self.active_tasks and not self.active_tasks[session_id].done():
            logger.warning("Session %s already has an active task", session_id)
            return

        task = asyncio.create_task(
            self._run_agent_task(session_id, task_description, corps_id, context_snapshot)
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
                await self.connection_manager.broadcast(corps_id, {
                    "type": "agent_response",
                    "corps_id": corps_id,
                    "session_id": session_id,
                    "role": role,
                    "nickname": nickname,
                    "from_role": role,
                    "content": result.final_response,
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

    def _on_task_done(self, session_id: str, task: asyncio.Task) -> None:
        self.active_tasks.pop(session_id, None)
        if task.exception():
            logger.error("Background task for %s raised: %s", session_id, task.exception())

    def is_active(self, session_id: str) -> bool:
        task = self.active_tasks.get(session_id)
        return task is not None and not task.done()

    def get_session_for_role(self, db, corps_id: str, role: str) -> Optional[str]:
        """Find the session_id for a given role in a corps. Respawns completed sessions."""
        from backend.models.agent_session import AgentSession, SessionStatus
        from backend.models.agent_definition import AgentDefinition
        from backend.services.agent_lifecycle import spawn_session

        # Try active first
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
            return active.id

        # Find most recent completed/failed session and respawn
        old = (
            db.query(AgentSession)
            .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
            .filter(
                AgentSession.corps_id == corps_id,
                AgentDefinition.role == role,
            )
            .order_by(AgentSession.started_at.desc())
            .first()
        )
        if old:
            new_session = spawn_session(
                db, definition_id=old.definition_id,
                corps_id=corps_id, parent_session_id=old.parent_session_id,
            )
            logger.info("Respawned session for role %s: %s -> %s", role, old.id, new_session.id)
            return new_session.id

        return None
