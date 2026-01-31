from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.problem import Problem, ProblemSeverity, ProblemStatus


class InvalidProblemTransition(Exception):
    pass


def report_problem(
    db: Session,
    segment_id: str,
    corps_id: str,
    reported_by_role: str,
    title: str,
    description: Optional[str] = None,
    severity: ProblemSeverity = ProblemSeverity.MEDIUM,
    reported_by_session_id: Optional[str] = None,
) -> Problem:
    problem = Problem(
        segment_id=segment_id,
        corps_id=corps_id,
        reported_by_role=reported_by_role,
        reported_by_session_id=reported_by_session_id,
        title=title,
        description=description,
        severity=severity,
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return problem


def acknowledge_problem(db: Session, problem_id: str) -> Problem:
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise ValueError(f"Problem {problem_id} not found")
    if problem.status != ProblemStatus.OPEN:
        raise InvalidProblemTransition(
            f"Cannot acknowledge problem in {problem.status.value} state"
        )
    problem.status = ProblemStatus.ACKNOWLEDGED
    db.commit()
    db.refresh(problem)
    return problem


def resolve_problem(
    db: Session,
    problem_id: str,
    resolved_by_role: str,
    resolution: Optional[str] = None,
) -> Problem:
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise ValueError(f"Problem {problem_id} not found")
    if problem.status == ProblemStatus.RESOLVED:
        raise InvalidProblemTransition("Problem is already resolved")
    problem.status = ProblemStatus.RESOLVED
    problem.resolved_by_role = resolved_by_role
    problem.resolution = resolution
    problem.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(problem)
    return problem


def get_open_problems(
    db: Session,
    segment_id: Optional[str] = None,
    corps_id: Optional[str] = None,
) -> list[Problem]:
    query = db.query(Problem).filter(Problem.status != ProblemStatus.RESOLVED)
    if segment_id is not None:
        query = query.filter(Problem.segment_id == segment_id)
    if corps_id is not None:
        query = query.filter(Problem.corps_id == corps_id)
    return query.order_by(Problem.created_at).all()
