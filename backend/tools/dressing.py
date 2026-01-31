"""Dressing — alignment check with adjacent work.

When a performer completes a rep, dressing checks that the output
aligns with related segments and sets. Like dressing the form
in a drill — making sure your work lines up with your neighbors.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class AlignmentResult:
    aligned: bool
    checks: list[dict] = field(default_factory=list)
    summary: str = ""


class Dressing:
    """Configurable alignment checker.

    Register alignment checks that compare an artifact against
    related artifacts or specifications. Each check receives the
    primary artifact and a list of related artifacts.
    """

    def __init__(self):
        self._checks: list[tuple[str, Callable]] = []

    def add_check(
        self,
        name: str,
        check_fn: Callable[[str, list[str]], Optional[str]],
    ) -> None:
        """Register an alignment check.

        check_fn receives (artifact, related_artifacts) and returns
        None if aligned, or a description of the misalignment.
        """
        self._checks.append((name, check_fn))

    def check_alignment(
        self, artifact: str, related_artifacts: list[str]
    ) -> AlignmentResult:
        """Run all alignment checks against an artifact and its neighbors."""
        results = []
        all_aligned = True

        for name, check_fn in self._checks:
            try:
                error = check_fn(artifact, related_artifacts)
                if error is None:
                    results.append({"check": name, "aligned": True})
                else:
                    results.append({"check": name, "aligned": False, "issue": error})
                    all_aligned = False
            except Exception as e:
                results.append({"check": name, "aligned": False, "issue": str(e)})
                all_aligned = False

        aligned_count = sum(1 for r in results if r["aligned"])
        total = len(results)

        return AlignmentResult(
            aligned=all_aligned,
            checks=results,
            summary=f"{aligned_count}/{total} alignment checks passed",
        )
