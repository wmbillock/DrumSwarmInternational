"""Verification gates — automated quality checks before work completion.

Gates run before a rep transitions to COMPLETED. Built-in checks include
non-empty result, minimum length, JSON validity, and custom validators.
"""

import json
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class GateResult:
    """Result of a single verification gate."""
    gate_name: str
    passed: bool
    message: str = ""


@dataclass
class VerificationResult:
    """Aggregate result of all verification gates for a rep."""
    rep_id: str
    passed: bool
    gates: list[GateResult] = field(default_factory=list)

    @property
    def failed_gates(self) -> list[GateResult]:
        return [g for g in self.gates if not g.passed]

    @property
    def summary(self) -> str:
        if self.passed:
            return f"All {len(self.gates)} verification gates passed."
        failed = self.failed_gates
        return (
            f"{len(failed)}/{len(self.gates)} verification gates failed: "
            + "; ".join(f"{g.gate_name}: {g.message}" for g in failed)
        )


# --- Built-in Gates ---

def gate_non_empty(result: str, **kwargs) -> GateResult:
    """Check that the result is not empty."""
    passed = bool(result and result.strip())
    return GateResult(
        gate_name="non_empty",
        passed=passed,
        message="" if passed else "Result is empty.",
    )


def gate_minimum_length(result: str, min_length: int = 10, **kwargs) -> GateResult:
    """Check that the result meets a minimum length."""
    passed = len(result.strip()) >= min_length
    return GateResult(
        gate_name="minimum_length",
        passed=passed,
        message="" if passed else f"Result is {len(result.strip())} chars, minimum is {min_length}.",
    )


def gate_json_valid(result: str, **kwargs) -> GateResult:
    """Check that the result is valid JSON (only when result looks like JSON)."""
    stripped = result.strip()
    if not stripped or stripped[0] not in ('{', '['):
        return GateResult(gate_name="json_valid", passed=True, message="Not JSON, skipped.")
    try:
        json.loads(stripped)
        return GateResult(gate_name="json_valid", passed=True)
    except json.JSONDecodeError as e:
        return GateResult(gate_name="json_valid", passed=False, message=f"Invalid JSON: {e}")


def gate_brown_m_and_m(result: str, canary_phrase: str = "", **kwargs) -> GateResult:
    """Brown M&M canary: check that a verification phrase appears in the result."""
    if not canary_phrase:
        return GateResult(gate_name="brown_m_and_m", passed=True, message="No canary phrase set.")
    passed = canary_phrase.lower() in result.lower()
    return GateResult(
        gate_name="brown_m_and_m",
        passed=passed,
        message="" if passed else f"Canary phrase '{canary_phrase}' not found in result.",
    )


# Default gate chain
DEFAULT_GATES = [gate_non_empty, gate_minimum_length, gate_json_valid]

# Gate configurations per coordinate type — maps type name to gate overrides
COORDINATE_TYPE_GATES: dict[str, dict] = {
    "show": {"min_length": 50},
    "movement": {"min_length": 20},
    "set": {"min_length": 10},
    "coordinate": {"min_length": 10},
}


class VerificationEngine:
    """Runs verification gates on rep results before completion."""

    def __init__(self):
        self._gates: list[Callable] = list(DEFAULT_GATES)
        self._custom_gates: dict[str, list[Callable]] = {}  # coordinate_id -> custom gates
        self._type_gates: dict[str, list[Callable]] = {}  # coordinate_type -> extra gates
        self._type_kwargs: dict[str, dict] = dict(COORDINATE_TYPE_GATES)

    def add_gate(self, gate_func: Callable) -> None:
        """Add a global verification gate."""
        self._gates.append(gate_func)

    def add_custom_gate(self, coordinate_id: str, gate_func: Callable) -> None:
        """Add a custom gate for a specific coordinate."""
        self._custom_gates.setdefault(coordinate_id, []).append(gate_func)

    def add_type_gate(self, coordinate_type: str, gate_func: Callable) -> None:
        """Add a gate for all coordinates of a given type."""
        self._type_gates.setdefault(coordinate_type, []).append(gate_func)

    def set_type_kwargs(self, coordinate_type: str, **kwargs) -> None:
        """Set gate keyword overrides for a coordinate type."""
        self._type_kwargs.setdefault(coordinate_type, {}).update(kwargs)

    def verify(
        self,
        rep_id: str,
        result: str,
        coordinate_id: Optional[str] = None,
        coordinate_type: Optional[str] = None,
        canary_phrase: str = "",
    ) -> VerificationResult:
        """Run all applicable gates on a result."""
        gate_results = []
        # Merge type-specific kwargs
        kwargs = {"canary_phrase": canary_phrase}
        if coordinate_type and coordinate_type in self._type_kwargs:
            kwargs.update(self._type_kwargs[coordinate_type])

        # Run global gates
        for gate in self._gates:
            gate_results.append(gate(result, **kwargs))

        # Run brown M&M if canary is set
        if canary_phrase:
            gate_results.append(gate_brown_m_and_m(result, **kwargs))

        # Run type-specific gates
        if coordinate_type and coordinate_type in self._type_gates:
            for gate in self._type_gates[coordinate_type]:
                gate_results.append(gate(result, **kwargs))

        # Run custom gates for coordinate
        if coordinate_id and coordinate_id in self._custom_gates:
            for gate in self._custom_gates[coordinate_id]:
                gate_results.append(gate(result, **kwargs))

        all_passed = all(g.passed for g in gate_results)
        return VerificationResult(rep_id=rep_id, passed=all_passed, gates=gate_results)


class VerificationError(Exception):
    """Raised when verification gates fail on rep completion."""
    def __init__(self, verification_result: VerificationResult):
        self.result = verification_result
        super().__init__(verification_result.summary)


# Module-level singleton
_engine: Optional[VerificationEngine] = None


def get_verification_engine() -> VerificationEngine:
    """Get or create the global verification engine."""
    global _engine
    if _engine is None:
        _engine = VerificationEngine()
    return _engine
