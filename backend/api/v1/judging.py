"""V1 API — Judging routes.

Uses JudgesTape model for judge feedback records.
"""

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _validate_id, _get_db_session

router = APIRouter(prefix="/api/v1")


@router.get("/judging/tapes")
def v1_list_judging_tapes(corps_id: str = None, limit: int = 50):
    """List judging tapes (consolidated judge feedback per competition)."""
    from backend.models.judges_tape import JudgesTape
    db = _get_db_session()
    try:
        q = db.query(JudgesTape)
        if corps_id:
            _validate_id(corps_id, "corps_id")
            q = q.filter(JudgesTape.corps_id == corps_id)
        tapes = q.order_by(JudgesTape.created_at.desc()).limit(limit).all()
        return [{
            "id": t.id,
            "corps_id": t.corps_id,
            "competition_id": t.competition_id,
            "overall_assessment": t.overall_assessment,
            "caption_feedbacks": t.caption_feedbacks,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        } for t in tapes]
    finally:
        db.close()


@router.get("/judging/tapes/{tape_id}")
def v1_get_judging_tape(tape_id: str):
    """Get a single judging tape."""
    from backend.models.judges_tape import JudgesTape
    db = _get_db_session()
    try:
        tape = db.query(JudgesTape).filter(JudgesTape.id == tape_id).first()
        if not tape:
            raise HTTPException(404, "Tape not found")
        return {
            "id": tape.id,
            "corps_id": tape.corps_id,
            "competition_id": tape.competition_id,
            "overall_assessment": tape.overall_assessment,
            "caption_feedbacks": tape.caption_feedbacks,
            "created_at": tape.created_at.isoformat() if tape.created_at else None,
        }
    finally:
        db.close()


@router.get("/judging/corps/{corps_id}/actions")
def v1_critique_actions(corps_id: str):
    """Get critique action items for a corps from judge feedback."""
    _validate_id(corps_id, "corps_id")
    from backend.models.judges_tape import JudgesTape
    db = _get_db_session()
    try:
        tapes = (
            db.query(JudgesTape)
            .filter(JudgesTape.corps_id == corps_id)
            .order_by(JudgesTape.created_at.desc())
            .limit(10)
            .all()
        )
        actions = []
        for tape in tapes:
            for caption, info in (tape.caption_feedbacks or {}).items():
                if info.get("feedback"):
                    actions.append({
                        "competition_id": tape.competition_id,
                        "caption": caption,
                        "score": info.get("value", 0),
                        "feedback": info["feedback"],
                        "created_at": tape.created_at.isoformat() if tape.created_at else None,
                    })
        return actions
    finally:
        db.close()


@router.get("/judging/corps/{corps_id}/tapes/{tape_id}/export")
def v1_export_judge_tape(corps_id: str, tape_id: str):
    """Export a judging tape as markdown."""
    _validate_id(corps_id, "corps_id")
    from backend.models.judges_tape import JudgesTape
    from backend.services.judge_service import export_tape_markdown
    db = _get_db_session()
    try:
        tape = db.query(JudgesTape).filter(
            JudgesTape.id == tape_id,
            JudgesTape.corps_id == corps_id,
        ).first()
        if not tape:
            raise HTTPException(404, "Tape not found")
        return {"markdown": export_tape_markdown(tape)}
    finally:
        db.close()
