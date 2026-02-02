"""V1 API — Judging routes."""

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _validate_id, _get_db_session

router = APIRouter(prefix="/api/v1")


@router.get("/judging/tapes")
def v1_list_judging_tapes(corps_id: str = None, limit: int = 50):
    """List judging tapes (score records)."""
    from backend.models.reputation import Reputation
    db = _get_db_session()
    try:
        q = db.query(Reputation)
        if corps_id:
            q = q.filter(Reputation.corps_id == corps_id)
        tapes = q.order_by(Reputation.created_at.desc()).limit(limit).all()
        return [{
            "id": t.id,
            "corps_id": t.corps_id,
            "agent_id": t.agent_id,
            "dimension": t.dimension,
            "score": t.score,
            "critique": t.critique,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        } for t in tapes]
    finally:
        db.close()


@router.get("/judging/tapes/{tape_id}")
def v1_get_judging_tape(tape_id: str):
    """Get a single judging tape."""
    from backend.models.reputation import Reputation
    db = _get_db_session()
    try:
        tape = db.query(Reputation).filter(Reputation.id == tape_id).first()
        if not tape:
            raise HTTPException(404, "Tape not found")
        return {
            "id": tape.id,
            "corps_id": tape.corps_id,
            "agent_id": tape.agent_id,
            "dimension": tape.dimension,
            "score": tape.score,
            "critique": tape.critique,
            "created_at": tape.created_at.isoformat() if tape.created_at else None,
        }
    finally:
        db.close()


@router.get("/judging/corps/{corps_id}/actions")
def v1_critique_actions(corps_id: str):
    """Get critique action items for a corps."""
    from backend.models.reputation import Reputation
    db = _get_db_session()
    try:
        reps = (
            db.query(Reputation)
            .filter(Reputation.corps_id == corps_id)
            .filter(Reputation.critique.isnot(None))
            .order_by(Reputation.created_at.desc())
            .limit(20)
            .all()
        )
        return [{
            "id": r.id,
            "agent_id": r.agent_id,
            "dimension": r.dimension,
            "score": r.score,
            "critique": r.critique,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in reps]
    finally:
        db.close()


@router.get("/judging/corps/{corps_id}/tapes/{rep_id}/export")
def v1_export_judge_tape(corps_id: str, rep_id: str):
    """Export a judging tape as markdown."""
    from backend.models.reputation import Reputation
    db = _get_db_session()
    try:
        rep = db.query(Reputation).filter(
            Reputation.id == rep_id,
            Reputation.corps_id == corps_id,
        ).first()
        if not rep:
            raise HTTPException(404, "Tape not found")
        md = f"# Judging Tape: {rep.id}\n\n"
        md += f"**Corps:** {rep.corps_id}\n"
        md += f"**Agent:** {rep.agent_id}\n"
        md += f"**Dimension:** {rep.dimension}\n"
        md += f"**Score:** {rep.score}\n\n"
        md += f"## Critique\n\n{rep.critique or 'No critique recorded.'}\n"
        return {"markdown": md}
    finally:
        db.close()
