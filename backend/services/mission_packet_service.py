from sqlalchemy.orm import Session

from backend.models.mission_packet import MissionPacket


class MissionScopeViolation(Exception):
    pass


TARGET_ARGUMENT_KEYS = {
    "rep": ["rep_id", "target_id"],
    "rehearsal_block": ["rehearsal_block_id", "block_id", "target_id"],
    "critique_adjustment": ["critique_adjustment_id", "adjustment_id", "target_id"],
    "judging_assignment": ["judging_assignment_id", "target_id"],
}


def create_mission_packet(
    db: Session,
    *,
    session_id: str,
    corps_id: str,
    role: str,
    phase: str,
    target_type: str,
    target_id: str,
    allowed_tools: list[str],
    forbidden_scope: list[str],
    completion_criteria: str,
    handoff_target: str | None,
) -> MissionPacket:
    if not allowed_tools:
        raise ValueError("allowed_tools must not be empty")
    if not completion_criteria.strip():
        raise ValueError("completion_criteria is required")

    packet = MissionPacket(
        session_id=session_id,
        corps_id=corps_id,
        role=role,
        phase=phase,
        target_type=target_type,
        target_id=target_id,
        allowed_tools=allowed_tools,
        forbidden_scope=forbidden_scope,
        completion_criteria=completion_criteria,
        handoff_target=handoff_target,
    )
    db.add(packet)
    db.commit()
    db.refresh(packet)
    return packet


def get_mission_packet(db: Session, *, session_id: str) -> MissionPacket | None:
    return db.query(MissionPacket).filter(MissionPacket.session_id == session_id).one_or_none()


def assert_tool_call_in_scope(
    db: Session,
    *,
    session_id: str,
    tool_name: str,
    arguments: dict,
) -> None:
    packet = get_mission_packet(db, session_id=session_id)
    if packet is None:
        return

    if tool_name not in packet.allowed_tools:
        raise MissionScopeViolation(f"Tool {tool_name} is not allowed for this mission.")

    argument_target = _extract_target_argument(packet.target_type, arguments)
    if argument_target is not None and argument_target != packet.target_id:
        raise MissionScopeViolation(f"Target {argument_target} is outside mission scope.")


def render_mission_packet(packet: MissionPacket) -> str:
    return (
        "MISSION PACKET\n"
        f"Role: {packet.role}\n"
        f"Phase: {packet.phase}\n"
        f"Target: {packet.target_type}:{packet.target_id}\n"
        f"Allowed tools: {', '.join(packet.allowed_tools)}\n"
        f"Forbidden scope: {', '.join(packet.forbidden_scope)}\n"
        f"Completion criteria: {packet.completion_criteria}\n"
        f"Handoff target: {packet.handoff_target or 'none'}\n"
        "Do not create new objectives. Do not work outside the target. "
        "When completion criteria are satisfied, stop and hand off exactly as directed."
    )


def _extract_target_argument(target_type: str, arguments: dict) -> str | None:
    for key in TARGET_ARGUMENT_KEYS.get(target_type, ["target_id"]):
        if key in arguments:
            return str(arguments[key])
    return None
