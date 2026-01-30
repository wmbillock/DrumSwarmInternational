"""Gock Block — isolated performance check.

Agents invoke the gock block to verify timing and performance
characteristics of an artifact in isolation. Runs the artifact
through a set of performance benchmarks and returns pass/fail
with measurements.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class BenchmarkResult:
    passed: bool
    benchmarks: list[dict] = field(default_factory=list)
    summary: str = ""


class GockBlock:
    """Configurable performance checker. Register benchmarks, then run them against artifacts."""

    def __init__(self):
        self._benchmarks: list[tuple[str, Callable, Optional[float]]] = []

    def add_benchmark(
        self,
        name: str,
        bench_fn: Callable[[str], float],
        threshold: Optional[float] = None,
    ) -> None:
        """Register a benchmark.

        bench_fn receives artifact content, returns a numeric measurement.
        If threshold is set, the benchmark fails when the measurement exceeds it.
        """
        self._benchmarks.append((name, bench_fn, threshold))

    def run(self, artifact: str) -> BenchmarkResult:
        """Run all registered benchmarks against an artifact."""
        results = []
        all_passed = True

        for name, bench_fn, threshold in self._benchmarks:
            try:
                measurement = bench_fn(artifact)
                passed = threshold is None or measurement <= threshold
                entry = {
                    "benchmark": name,
                    "passed": passed,
                    "measurement": measurement,
                }
                if threshold is not None:
                    entry["threshold"] = threshold
                if not passed:
                    all_passed = False
                results.append(entry)
            except Exception as e:
                results.append({"benchmark": name, "passed": False, "error": str(e)})
                all_passed = False

        passed_count = sum(1 for r in results if r["passed"])
        total = len(results)

        return BenchmarkResult(
            passed=all_passed,
            benchmarks=results,
            summary=f"{passed_count}/{total} benchmarks passed",
        )
