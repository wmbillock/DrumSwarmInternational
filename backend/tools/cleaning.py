"""Cleaning — continuous quality sweep.

A background process that reviews completed artifacts for style,
consistency, and standards compliance. Like cleaning the drill —
polishing what's already learned to bring it up to performance quality.
Flags issues to caption heads for review.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

from sqlalchemy.orm import Session

from backend.models.rep import Rep, RepStatus


@dataclass
class CleaningIssue:
    rep_id: str
    rule: str
    description: str


@dataclass
class CleaningResult:
    """Result of a cleaning sweep."""
    swept: int = 0
    issues_found: int = 0
    issues: list[CleaningIssue] = field(default_factory=list)


class CleaningRule:
    """A single cleaning rule that checks completed rep artifacts."""

    def __init__(self, name: str, check_fn: Callable[[str], Optional[str]]):
        self.name = name
        self.check_fn = check_fn


class Cleaning:
    """Configurable quality sweeper. Register rules, then sweep completed reps."""

    def __init__(self):
        self._rules: list[CleaningRule] = []

    def add_rule(self, name: str, check_fn: Callable[[str], Optional[str]]) -> None:
        """Register a cleaning rule.

        check_fn receives artifact content, returns None if clean
        or a description of the issue found.
        """
        self._rules.append(CleaningRule(name, check_fn))

    def sweep(self, db: Session, segment_id: str) -> CleaningResult:
        """Sweep all completed reps for a segment, applying registered rules."""
        result = CleaningResult()

        completed_reps = (
            db.query(Rep)
            .filter(
                Rep.segment_id == segment_id,
                Rep.status == RepStatus.COMPLETED,
            )
            .all()
        )

        for rep in completed_reps:
            result.swept += 1
            artifact = rep.result or ""

            for rule in self._rules:
                try:
                    issue_desc = rule.check_fn(artifact)
                    if issue_desc is not None:
                        result.issues_found += 1
                        result.issues.append(
                            CleaningIssue(
                                rep_id=rep.id,
                                rule=rule.name,
                                description=issue_desc,
                            )
                        )
                except Exception as e:
                    result.issues_found += 1
                    result.issues.append(
                        CleaningIssue(
                            rep_id=rep.id,
                            rule=rule.name,
                            description=f"Rule error: {e}",
                        )
                    )

        return result
