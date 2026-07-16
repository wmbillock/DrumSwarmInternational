"""Tool execution framework. Permission check -> execute -> return result.

Tools are registered callables. When an agent requests a tool invocation,
the executor checks the agent's definition for permission, then runs the tool.

Tools may accept a `db` parameter as their first argument. If the tool function
signature includes `db`, the executor injects the current database session.
"""

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from backend.services.agent_lifecycle import check_tool_permission
from backend.services.mission_packet_service import (
    MissionScopeViolation,
    assert_tool_call_in_scope,
)


@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: Optional[str] = None


class ToolNotFound(Exception):
    pass


class ToolPermissionDenied(Exception):
    pass


class ToolRegistry:
    """Registry of callable tools available to agents."""

    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._schemas: dict[str, dict] = {}

    def register(
        self,
        name: str,
        func: Callable,
        schema: Optional[dict] = None,
    ) -> None:
        self._tools[name] = func
        if schema:
            self._schemas[name] = schema

    def get_tool(self, name: str) -> Callable:
        if name not in self._tools:
            raise ToolNotFound(f"Tool '{name}' not registered")
        return self._tools[name]

    def get_schema(self, name: str) -> Optional[dict]:
        return self._schemas.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def get_schemas_for_session(
        self, db: Session, session_id: str
    ) -> list[dict]:
        """Return tool schemas for tools this session is allowed to use."""
        result = []
        for name in self._tools:
            if check_tool_permission(db, session_id, name):
                schema = self._schemas.get(name, {"name": name})
                result.append(schema)
        return result


class ToolExecutor:
    """Executes tool calls with permission checking."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def execute(
        self,
        db: Session,
        session_id: str,
        tool_name: str,
        arguments: dict,
    ) -> ToolResult:
        # Permission check
        if not check_tool_permission(db, session_id, tool_name):
            raise ToolPermissionDenied(
                f"Session {session_id} does not have permission to use '{tool_name}'"
            )

        try:
            assert_tool_call_in_scope(
                db,
                session_id=session_id,
                tool_name=tool_name,
                arguments=arguments,
            )
        except MissionScopeViolation as exc:
            return ToolResult(
                success=False,
                output={
                    "blocked": True,
                    "blocker_code": "mission_scope_violation",
                    "message": str(exc),
                },
                error=str(exc),
            )

        # Get and run the tool
        tool_func = self.registry.get_tool(tool_name)
        try:
            # Inject db if the tool function accepts it
            sig = inspect.signature(tool_func)
            params = list(sig.parameters.keys())

            # Auto-inject session context for tools that need it
            if "session_id" in params:
                arguments["session_id"] = session_id

            if "corps_id" in params or "from_role" in params:
                from backend.models.agent_session import AgentSession
                from backend.models.agent_definition import AgentDefinition
                session = db.get(AgentSession, session_id)
                if session:
                    if "corps_id" in params:
                        arguments["corps_id"] = session.corps_id
                    if "from_role" in params:
                        defn = db.get(AgentDefinition, session.definition_id)
                        if defn:
                            arguments["from_role"] = defn.role

            if params and params[0] == "db":
                output = tool_func(db, **arguments)
            else:
                output = tool_func(**arguments)
            return ToolResult(success=True, output=output)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
