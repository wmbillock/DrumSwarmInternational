"""Tuner — on-demand validation tool.

Agents invoke the tuner to verify their output is "in tune":
correct, well-formed, and meeting standards. Runs a set of
validation checks against an artifact and returns pass/fail
with details.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class ValidationResult:
    passed: bool
    checks: list[dict] = field(default_factory=list)
    summary: str = ""


class Tuner:
    """Configurable validator. Register check functions, then run them against artifacts."""

    def __init__(self):
        self._checks: list[tuple[str, Callable]] = []

    def add_check(self, name: str, check_fn: Callable[[str], Optional[str]]) -> None:
        """Register a check. check_fn receives artifact content, returns None if ok or error string."""
        self._checks.append((name, check_fn))

    def validate(self, artifact: str) -> ValidationResult:
        """Run all registered checks against an artifact."""
        results = []
        all_passed = True

        for name, check_fn in self._checks:
            try:
                error = check_fn(artifact)
                if error is None:
                    results.append({"check": name, "passed": True})
                else:
                    results.append({"check": name, "passed": False, "error": error})
                    all_passed = False
            except Exception as e:
                results.append({"check": name, "passed": False, "error": str(e)})
                all_passed = False

        passed_count = sum(1 for r in results if r["passed"])
        total = len(results)

        return ValidationResult(
            passed=all_passed,
            checks=results,
            summary=f"{passed_count}/{total} checks passed",
        )
