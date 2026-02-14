"""Operation tracking service for long-running async tasks.

Usage:
    op = create_operation(db, "advance_round", target_type="season", target_id="s1",
                          label="Advancing season s1 round 3")
    try:
        start_operation(db, op.id)
        result = do_the_work()
        complete_operation(db, op.id, result=json.dumps(result))
    except Exception as e:
        fail_operation(db, op.id, error=str(e))
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.operation import Operation, OperationStatus

logger = logging.getLogger(__name__)


def create_operation(
    db: Session,
    operation_type: str,
    *,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    label: Optional[str] = None,
) -> Operation:
    """Create a new pending operation."""
    op = Operation(
        operation_type=operation_type,
        target_type=target_type,
        target_id=target_id,
        label=label,
        status=OperationStatus.PENDING,
    )
    db.add(op)
    db.commit()
    db.refresh(op)
    logger.info("Operation created: %s (%s) target=%s/%s", op.id, operation_type, target_type, target_id)
    return op


def start_operation(db: Session, operation_id: str) -> None:
    """Mark an operation as running."""
    op = db.get(Operation, operation_id)
    if op:
        op.status = OperationStatus.RUNNING
        op.started_at = datetime.now(timezone.utc)
        db.commit()


def complete_operation(db: Session, operation_id: str, *, result: Optional[str] = None) -> None:
    """Mark an operation as completed with optional result JSON."""
    op = db.get(Operation, operation_id)
    if op:
        op.status = OperationStatus.COMPLETED
        op.completed_at = datetime.now(timezone.utc)
        if result:
            op.result = result
        db.commit()
        logger.info("Operation completed: %s", operation_id)


def fail_operation(db: Session, operation_id: str, *, error: str) -> None:
    """Mark an operation as failed."""
    op = db.get(Operation, operation_id)
    if op:
        op.status = OperationStatus.FAILED
        op.completed_at = datetime.now(timezone.utc)
        op.error = error
        db.commit()
        logger.warning("Operation failed: %s — %s", operation_id, error)
