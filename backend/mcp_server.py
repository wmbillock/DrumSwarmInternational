"""MCP Server exposing DCI Swarm tools to Claude CLI.

Usage:
    python -m backend.mcp_server --role executive_director --corps-id <uuid>

The Claude CLI connects to this via --mcp-config. Each agent session
spawns its own MCP server filtered to the role's allowed tools.
"""

import argparse
import json
import sys
import os

from mcp.server import FastMCP

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.database import Base, create_db_engine, create_session_factory
from backend.services.corps_service import ROLE_TOOLS

# Parse args before creating server (need role for tool filtering)
_parser = argparse.ArgumentParser()
_parser.add_argument("--role", default="executive_director")
_parser.add_argument("--corps-id", default="")
_parser.add_argument("--session-id", default="")
_args, _ = _parser.parse_known_args()

_role = _args.role
_corps_id = _args.corps_id
_session_id = _args.session_id
_allowed_tools = set(ROLE_TOOLS.get(_role, []))

# DB setup
_engine = create_db_engine()
Base.metadata.create_all(_engine)
_SessionFactory = create_session_factory(_engine)

mcp = FastMCP(f"dci-{_role}")


def _get_db():
    return _SessionFactory()


# --- Tool implementations ---

if "create_segment" in _allowed_tools:
    @mcp.tool()
    def create_segment(type: str, title: str, description: str = "", parent_id: str = "", caption: str = "") -> str:
        """Create a new segment (work unit). Types: show, movement, set, segment. Must specify parent_id for non-show types."""
        from backend.models.segment import SegmentType
        from backend.services.segment_service import create_segment as _create
        db = _get_db()
        try:
            coord = _create(db, type=SegmentType(type), title=title,
                          description=description or None, parent_id=parent_id or None,
                          caption=caption or None)
            return json.dumps({"id": coord.id, "type": coord.type.value, "title": coord.title, "status": coord.status.value})
        finally:
            db.close()


if "create_rep" in _allowed_tools:
    @mcp.tool()
    def create_rep(segment_id: str) -> str:
        """Create a new rep (work attempt) for a segment. Starts in PENDING status."""
        from backend.services.rep_service import create_rep as _create
        db = _get_db()
        try:
            rep = _create(db, segment_id=segment_id)
            return json.dumps({"id": rep.id, "status": rep.status.value, "segment_id": rep.segment_id})
        finally:
            db.close()


if "transition_rep" in _allowed_tools:
    @mcp.tool()
    def transition_rep(rep_id: str, new_status: str, assigned_to: str = "", result: str = "", error: str = "") -> str:
        """Transition a rep to a new status. Valid: pending->assigned, assigned->in_progress, in_progress->review/failed, review->completed/failed."""
        from backend.models.rep import RepStatus
        from backend.services.rep_service import transition_rep as _transition
        db = _get_db()
        try:
            rep = _transition(db, rep_id=rep_id, new_status=RepStatus(new_status),
                            assigned_to=assigned_to or None, result=result or None, error=error or None)
            return json.dumps({"id": rep.id, "status": rep.status.value})
        finally:
            db.close()


if "send_message" in _allowed_tools:
    @mcp.tool()
    def send_message(from_role: str, to_role: str, type: str, subject: str, body: str = "", priority: str = "normal", segment_id: str = "") -> str:
        """Send a message to another role. Types: handoff, escalation, flag, status, directive, feedback."""
        from backend.models.message import MessageType, MessagePriority
        from backend.services.message_service import send_message as _send
        db = _get_db()
        try:
            msg = _send(db, corps_id=_corps_id, from_role=from_role, to_role=to_role,
                       type=MessageType(type), subject=subject, body=body or None,
                       priority=MessagePriority(priority), segment_id=segment_id or None)
            return json.dumps({"id": msg.id, "type": msg.type.value, "subject": msg.subject})
        finally:
            db.close()


if "handoff" in _allowed_tools:
    @mcp.tool()
    def handoff(from_role: str, to_role: str, subject: str, body: str = "", segment_id: str = "") -> str:
        """Hand off work to a downstream role with instructions."""
        from backend.services.corps_service import handoff as _handoff
        db = _get_db()
        try:
            _handoff(db, corps_id=_corps_id, from_role=from_role, to_role=to_role,
                    subject=subject, body=body or None, segment_id=segment_id or None)
            return json.dumps({"status": "handed_off", "from": from_role, "to": to_role})
        finally:
            db.close()


if "get_segment" in _allowed_tools:
    @mcp.tool()
    def get_segment(segment_id: str) -> str:
        """Get details about a specific segment."""
        from backend.services.segment_service import get_segment as _get
        db = _get_db()
        try:
            coord = _get(db, segment_id)
            if not coord:
                return json.dumps({"error": "not found"})
            return json.dumps({"id": coord.id, "type": coord.type.value, "title": coord.title,
                             "status": coord.status.value, "description": coord.description})
        finally:
            db.close()


if "get_segment_children" in _allowed_tools:
    @mcp.tool()
    def get_segment_children(segment_id: str) -> str:
        """Get the child segments of a parent segment."""
        from backend.services.segment_service import get_children
        db = _get_db()
        try:
            children = get_children(db, segment_id)
            return json.dumps([{"id": c.id, "type": c.type.value, "title": c.title, "status": c.status.value} for c in children])
        finally:
            db.close()


if "get_reps_for_segment" in _allowed_tools:
    @mcp.tool()
    def get_reps_for_segment(segment_id: str) -> str:
        """Get all reps for a segment."""
        from backend.services.rep_service import get_reps_for_segment as _get
        db = _get_db()
        try:
            reps = _get(db, segment_id)
            return json.dumps([{"id": r.id, "status": r.status.value, "assigned_to": r.assigned_to, "result": r.result} for r in reps])
        finally:
            db.close()


if "submit_work" in _allowed_tools:
    @mcp.tool()
    def submit_work(rep_id: str, result: str) -> str:
        """Submit completed work for a rep. Transitions to review status."""
        from backend.models.rep import RepStatus
        from backend.services.rep_service import transition_rep as _transition
        db = _get_db()
        try:
            rep = _transition(db, rep_id=rep_id, new_status=RepStatus.REVIEW, result=result)
            return json.dumps({"id": rep.id, "status": rep.status.value})
        finally:
            db.close()


if __name__ == "__main__":
    mcp.run(transport="stdio")
