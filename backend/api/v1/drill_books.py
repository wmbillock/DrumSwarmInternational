"""V1 Drill Books API — CRUD + state machine endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.v1.helpers import _get_db_session, _validate_id

router = APIRouter(prefix="/api/v1/drill-books", tags=["drill-books"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class CreateBookRequest(BaseModel):
    title: str
    description: str = ""
    book_type: str = "linear"
    parent_id: Optional[str] = None
    corps_id: Optional[str] = None
    role: Optional[str] = None


class AddStepRequest(BaseModel):
    action_type: str
    description: str = ""
    depends_on: Optional[list[str]] = None
    sequence: Optional[int] = None


class AssignBookRequest(BaseModel):
    performer_id: Optional[str] = None
    session_id: Optional[str] = None


class CompleteStepRequest(BaseModel):
    result: Optional[dict] = None
    evidence_content: Optional[str] = None
    evidence_type: str = "command_output"


class FailStepRequest(BaseModel):
    error: str = ""


class AddEvidenceRequest(BaseModel):
    evidence_type: str
    content: str = ""
    step_id: Optional[str] = None
    metadata: Optional[dict] = None


class SpawnChildRequest(BaseModel):
    title: str
    role: Optional[str] = None
    steps: Optional[list[dict]] = None


# ---------------------------------------------------------------------------
# Book endpoints
# ---------------------------------------------------------------------------


@router.get("")
def list_books(
    corps_id: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    parent_id: Optional[str] = None,
):
    from backend.services.drill_book_service import list_books as _list
    from backend.models.drill_book import BookStatus

    db = _get_db_session()
    try:
        status_enum = BookStatus(status) if status else None
        books = _list(db, corps_id=corps_id, role=role, status=status_enum, parent_id=parent_id)
        return [_book_to_dict(b) for b in books]
    finally:
        db.close()


@router.post("")
def create_book(req: CreateBookRequest):
    from backend.services.drill_book_service import create_book as _create

    db = _get_db_session()
    try:
        book = _create(
            db, title=req.title, description=req.description,
            book_type=req.book_type, parent_id=req.parent_id,
            corps_id=req.corps_id, role=req.role,
        )
        return _book_to_dict(book)
    finally:
        db.close()


@router.get("/{book_id}")
def get_book(book_id: str):
    _validate_id(book_id, "book_id")
    from backend.services.drill_book_service import get_book as _get

    db = _get_db_session()
    try:
        book = _get(db, book_id)
        if book is None:
            raise HTTPException(404, f"Book {book_id} not found")
        return _book_to_dict(book)
    finally:
        db.close()


@router.post("/{book_id}/assign")
def assign_book(book_id: str, req: AssignBookRequest):
    _validate_id(book_id, "book_id")
    from backend.services.drill_book_service import assign_book as _assign

    db = _get_db_session()
    try:
        book = _assign(db, book_id, performer_id=req.performer_id, session_id=req.session_id)
        return _book_to_dict(book)
    except ValueError as e:
        raise HTTPException(404, str(e))
    finally:
        db.close()


@router.post("/{book_id}/start")
def start_book(book_id: str):
    _validate_id(book_id, "book_id")
    from backend.services.drill_book_service import start_book as _start, InvalidBookTransition

    db = _get_db_session()
    try:
        book = _start(db, book_id)
        return _book_to_dict(book)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except InvalidBookTransition as e:
        raise HTTPException(409, str(e))
    finally:
        db.close()


@router.post("/{book_id}/complete")
def complete_book(book_id: str):
    _validate_id(book_id, "book_id")
    from backend.services.drill_book_service import complete_book as _complete, InvalidBookTransition

    db = _get_db_session()
    try:
        book = _complete(db, book_id)
        return _book_to_dict(book)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except InvalidBookTransition as e:
        raise HTTPException(409, str(e))
    finally:
        db.close()


@router.post("/{book_id}/fail")
def fail_book(book_id: str, error: str = ""):
    _validate_id(book_id, "book_id")
    from backend.services.drill_book_service import fail_book as _fail, InvalidBookTransition

    db = _get_db_session()
    try:
        book = _fail(db, book_id, error=error)
        return _book_to_dict(book)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except InvalidBookTransition as e:
        raise HTTPException(409, str(e))
    finally:
        db.close()


@router.post("/{book_id}/abandon")
def abandon_book(book_id: str, reason: str = ""):
    _validate_id(book_id, "book_id")
    from backend.services.drill_book_service import abandon_book as _abandon, InvalidBookTransition

    db = _get_db_session()
    try:
        book = _abandon(db, book_id, reason=reason)
        return _book_to_dict(book)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except InvalidBookTransition as e:
        raise HTTPException(409, str(e))
    finally:
        db.close()


@router.get("/{book_id}/context")
def get_resumption_context(book_id: str):
    _validate_id(book_id, "book_id")
    from backend.services.drill_book_service import get_resumption_context as _ctx

    db = _get_db_session()
    try:
        return _ctx(db, book_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    finally:
        db.close()


@router.get("/{book_id}/next-steps")
def get_next_steps(book_id: str):
    _validate_id(book_id, "book_id")
    from backend.services.drill_book_service import get_next_steps as _next

    db = _get_db_session()
    try:
        steps = _next(db, book_id)
        return [_step_to_dict(s) for s in steps]
    except ValueError as e:
        raise HTTPException(404, str(e))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Step endpoints
# ---------------------------------------------------------------------------


@router.post("/{book_id}/steps")
def add_step(book_id: str, req: AddStepRequest):
    _validate_id(book_id, "book_id")
    from backend.services.drill_book_service import add_step as _add

    db = _get_db_session()
    try:
        step = _add(
            db, book_id, action_type=req.action_type,
            description=req.description, depends_on=req.depends_on,
            sequence=req.sequence,
        )
        return _step_to_dict(step)
    except ValueError as e:
        raise HTTPException(404, str(e))
    finally:
        db.close()


@router.post("/steps/{step_id}/start")
def start_step(step_id: str, session_id: Optional[str] = None):
    _validate_id(step_id, "step_id")
    from backend.services.drill_book_service import start_step as _start, InvalidStepTransition

    db = _get_db_session()
    try:
        step = _start(db, step_id, session_id=session_id)
        return _step_to_dict(step)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except InvalidStepTransition as e:
        raise HTTPException(409, str(e))
    finally:
        db.close()


@router.post("/steps/{step_id}/complete")
def complete_step(step_id: str, req: CompleteStepRequest):
    _validate_id(step_id, "step_id")
    from backend.services.drill_book_service import complete_step as _complete, InvalidStepTransition

    db = _get_db_session()
    try:
        step = _complete(
            db, step_id, result=req.result,
            evidence_content=req.evidence_content,
            evidence_type=req.evidence_type,
        )
        return _step_to_dict(step)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except InvalidStepTransition as e:
        raise HTTPException(409, str(e))
    finally:
        db.close()


@router.post("/steps/{step_id}/fail")
def fail_step(step_id: str, req: FailStepRequest):
    _validate_id(step_id, "step_id")
    from backend.services.drill_book_service import fail_step as _fail, InvalidStepTransition

    db = _get_db_session()
    try:
        step = _fail(db, step_id, error=req.error)
        return _step_to_dict(step)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except InvalidStepTransition as e:
        raise HTTPException(409, str(e))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Evidence endpoints
# ---------------------------------------------------------------------------


@router.post("/{book_id}/evidence")
def add_evidence(book_id: str, req: AddEvidenceRequest):
    _validate_id(book_id, "book_id")
    from backend.services.drill_book_service import add_evidence as _add

    db = _get_db_session()
    try:
        ev = _add(
            db, book_id, evidence_type=req.evidence_type,
            content=req.content, step_id=req.step_id,
            metadata=req.metadata,
        )
        return {"id": ev.id, "evidence_type": ev.evidence_type, "created_at": str(ev.created_at)}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Child book endpoints
# ---------------------------------------------------------------------------


@router.post("/{book_id}/children")
def spawn_child(book_id: str, req: SpawnChildRequest):
    _validate_id(book_id, "book_id")
    from backend.services.drill_book_service import spawn_child_book as _spawn

    db = _get_db_session()
    try:
        child = _spawn(db, book_id, title=req.title, role=req.role, steps=req.steps)
        return _book_to_dict(child)
    except ValueError as e:
        raise HTTPException(404, str(e))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------


def _book_to_dict(book: "DrillBook") -> dict:
    return {
        "id": book.id,
        "parent_id": book.parent_id,
        "corps_id": book.corps_id,
        "assigned_performer_id": book.assigned_performer_id,
        "assigned_role": book.assigned_role,
        "title": book.title,
        "description": book.description,
        "book_type": book.book_type,
        "status": book.status.value,
        "created_at": str(book.created_at) if book.created_at else None,
        "updated_at": str(book.updated_at) if book.updated_at else None,
        "completed_at": str(book.completed_at) if book.completed_at else None,
        "context_summary": book.context_summary,
        "step_count": len(book.steps) if book.steps else 0,
        "child_count": len(book.children) if book.children else 0,
    }


def _step_to_dict(step: "DrillStep") -> dict:
    return {
        "id": step.id,
        "book_id": step.book_id,
        "sequence": step.sequence,
        "action_type": step.action_type,
        "description": step.description,
        "status": step.status.value,
        "depends_on": step.depends_on,
        "assigned_session_id": step.assigned_session_id,
        "started_at": str(step.started_at) if step.started_at else None,
        "completed_at": str(step.completed_at) if step.completed_at else None,
        "result": step.result,
        "error": step.error,
    }
