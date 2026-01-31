"""Register service-layer tools that agents can call.

These wrap the actual service functions (create_segment, create_rep, etc.)
so agents can manipulate the domain model through tool use.
"""

from backend.services.tool_executor import ToolRegistry


def register_service_tools(registry: ToolRegistry) -> None:
    """Register domain tools that wrap service layer functions.

    Tools receive a `db` argument injected by the tool executor.
    """

    def create_segment(db, type: str, title: str, description: str = "", parent_id: str = "", caption: str = ""):
        from backend.models.segment import SegmentType
        from backend.services.segment_service import create_segment as _create
        coord = _create(
            db,
            type=SegmentType(type),
            title=title,
            description=description or None,
            parent_id=parent_id or None,
            caption=caption or None,
        )
        return {"id": coord.id, "type": coord.type.value, "title": coord.title, "status": coord.status.value}

    def create_rep(db, segment_id: str):
        from backend.services.rep_service import create_rep as _create
        rep = _create(db, segment_id=segment_id)
        return {"id": rep.id, "status": rep.status.value, "segment_id": rep.segment_id}

    def transition_rep(db, rep_id: str, new_status: str, assigned_to: str = "", result: str = "", error: str = ""):
        from backend.models.rep import RepStatus
        from backend.services.rep_service import transition_rep as _transition
        rep = _transition(
            db,
            rep_id=rep_id,
            new_status=RepStatus(new_status),
            assigned_to=assigned_to or None,
            result=result or None,
            error=error or None,
        )
        return {"id": rep.id, "status": rep.status.value}

    def send_message(db, corps_id: str, from_role: str, to_role: str, type: str, subject: str, body: str = "", priority: str = "normal", segment_id: str = ""):
        from backend.models.message import MessageType, MessagePriority
        from backend.services.message_service import send_message as _send
        msg = _send(
            db,
            corps_id=corps_id,
            from_role=from_role,
            to_role=to_role,
            type=MessageType(type),
            subject=subject,
            body=body or None,
            priority=MessagePriority(priority),
            segment_id=segment_id or None,
        )
        return {"id": msg.id, "type": msg.type.value, "subject": msg.subject}

    def handoff(db, corps_id: str, from_role: str, to_role: str, subject: str, body: str = "", segment_id: str = ""):
        from backend.services.corps_service import handoff as _handoff
        _handoff(
            db,
            corps_id=corps_id,
            from_role=from_role,
            to_role=to_role,
            subject=subject,
            body=body or None,
            segment_id=segment_id or None,
        )
        return {"status": "handed_off", "from": from_role, "to": to_role}

    def get_segment_children(db, segment_id: str):
        from backend.services.segment_service import get_children
        children = get_children(db, segment_id)
        return [{"id": c.id, "type": c.type.value, "title": c.title, "status": c.status.value} for c in children]

    def get_segment(db, segment_id: str):
        from backend.services.segment_service import get_segment as _get
        coord = _get(db, segment_id)
        if not coord:
            return {"error": "not found"}
        return {"id": coord.id, "type": coord.type.value, "title": coord.title, "status": coord.status.value, "description": coord.description}

    def get_reps_for_segment(db, segment_id: str):
        from backend.services.rep_service import get_reps_for_segment as _get
        reps = _get(db, segment_id)
        return [{"id": r.id, "status": r.status.value, "assigned_to": r.assigned_to, "result": r.result} for r in reps]

    def submit_work(db, rep_id: str, result: str):
        """Convenience: transition a rep to review with a result."""
        from backend.models.rep import RepStatus
        from backend.services.rep_service import transition_rep as _transition
        rep = _transition(db, rep_id=rep_id, new_status=RepStatus.REVIEW, result=result)
        return {"id": rep.id, "status": rep.status.value}

    def verify_work(db, rep_id: str, segment_id: str = ""):
        """Run verification gates on a rep's result before completion."""
        from backend.models.rep import Rep
        from backend.models.segment import Segment
        from backend.services.verification import get_verification_engine
        rep = db.get(Rep, rep_id)
        if not rep:
            return {"error": "Rep not found"}
        if not rep.result:
            return {"passed": False, "summary": "Rep has no result to verify."}
        engine = get_verification_engine()
        cid = segment_id or rep.segment_id
        coord = db.get(Segment, cid) if cid else None
        segment_type = coord.type.value if coord and coord.type else None
        vr = engine.verify(rep_id=rep_id, result=rep.result, segment_id=cid, segment_type=segment_type)
        return {"passed": vr.passed, "summary": vr.summary, "gates": [
            {"gate": g.gate_name, "passed": g.passed, "message": g.message} for g in vr.gates
        ]}

    # --- Register all tools ---

    registry.register("create_segment", create_segment, {
        "name": "create_segment",
        "description": "Create a new segment (work unit) in the hierarchy. Types: show, movement, set, segment. Must specify parent_id for non-show types.",
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["show", "movement", "set", "segment"], "description": "Segment type"},
                "title": {"type": "string", "description": "Title of the segment"},
                "description": {"type": "string", "description": "Description of what this segment covers"},
                "parent_id": {"type": "string", "description": "Parent segment ID (required for non-show types)"},
                "caption": {"type": "string", "description": "Caption/section (e.g. brass, percussion, guard, visual)"},
            },
            "required": ["type", "title"],
        },
    })

    registry.register("create_rep", create_rep, {
        "name": "create_rep",
        "description": "Create a new rep (rehearsal attempt) for a segment. The rep starts in PENDING status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "segment_id": {"type": "string", "description": "The segment to create a rep for"},
            },
            "required": ["segment_id"],
        },
    })

    registry.register("transition_rep", transition_rep, {
        "name": "transition_rep",
        "description": "Transition a rep to a new status. Valid transitions: pending->assigned, assigned->in_progress, in_progress->review/failed, review->completed/failed/in_progress.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rep_id": {"type": "string"},
                "new_status": {"type": "string", "enum": ["pending", "assigned", "in_progress", "review", "completed", "failed"]},
                "assigned_to": {"type": "string", "description": "Session ID to assign to"},
                "result": {"type": "string", "description": "Work result (for review/completed)"},
                "error": {"type": "string", "description": "Error message (for failed)"},
            },
            "required": ["rep_id", "new_status"],
        },
    })

    registry.register("send_message", send_message, {
        "name": "send_message",
        "description": "Send a message to another role in the corps hierarchy. corps_id and from_role are auto-injected.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to_role": {"type": "string", "description": "Target role to send the message to"},
                "type": {"type": "string", "enum": ["handoff", "escalation", "flag", "status", "directive", "feedback"]},
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "priority": {"type": "string", "enum": ["critical", "high", "normal", "low"]},
                "segment_id": {"type": "string"},
            },
            "required": ["to_role", "type", "subject"],
        },
    })

    registry.register("handoff", handoff, {
        "name": "handoff",
        "description": "Hand off work to a downstream role. Must follow the handoff chain. corps_id and from_role are auto-injected.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to_role": {"type": "string", "description": "Role to hand off to (e.g. program_coordinator, brass_caption_head)"},
                "subject": {"type": "string", "description": "Brief description of the handoff"},
                "body": {"type": "string", "description": "Detailed instructions for the receiving role"},
                "segment_id": {"type": "string", "description": "Segment ID related to this handoff"},
            },
            "required": ["to_role", "subject"],
        },
    })

    registry.register("get_segment", get_segment, {
        "name": "get_segment",
        "description": "Get details about a specific segment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "segment_id": {"type": "string"},
            },
            "required": ["segment_id"],
        },
    })

    registry.register("get_segment_children", get_segment_children, {
        "name": "get_segment_children",
        "description": "Get the child segments of a parent segment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "segment_id": {"type": "string"},
            },
            "required": ["segment_id"],
        },
    })

    registry.register("get_reps_for_segment", get_reps_for_segment, {
        "name": "get_reps_for_segment",
        "description": "Get all reps for a segment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "segment_id": {"type": "string"},
            },
            "required": ["segment_id"],
        },
    })

    registry.register("submit_work", submit_work, {
        "name": "submit_work",
        "description": "Submit completed work for a rep. Transitions it to review status with the result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rep_id": {"type": "string"},
                "result": {"type": "string", "description": "The completed work output"},
            },
            "required": ["rep_id", "result"],
        },
    })

    registry.register("verify_work", verify_work, {
        "name": "verify_work",
        "description": "Run verification gates on a rep's result. Returns pass/fail with gate details.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rep_id": {"type": "string", "description": "The rep to verify"},
                "segment_id": {"type": "string", "description": "Optional segment ID for custom gates"},
            },
            "required": ["rep_id"],
        },
    })
