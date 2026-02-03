"""Local CI watcher — file-change detection, test runner, coverage reporter.

Monitors file changes in the project, runs tests on change, and reports
results to the agent runtime. Agents can use CI status as a gate for
completing reps (work isn't "done" until CI is green).

Two-tier testing:
  1. Fast: Run only the relevant test file(s) for changed code
  2. Full: If fast passes, run the complete test suite
  3. Coverage: Generate coverage report after full suite passes

Results are written to a well-known path per corps for agent tool access.
"""

import json
import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
CI_STATUS_DIR = PROJECT_ROOT / ".ci"
DEBOUNCE_SECONDS = 3.0
COVERAGE_DIR = PROJECT_ROOT / ".ci" / "coverage"


@dataclass
class CIResult:
    """Result of a CI run."""
    timestamp: str = ""
    trigger: str = ""  # "file_change", "manual", "agent_request"
    changed_files: list[str] = field(default_factory=list)
    fast_test_passed: bool = False
    fast_test_output: str = ""
    fast_test_duration_s: float = 0.0
    full_test_passed: bool = False
    full_test_output: str = ""
    full_test_duration_s: float = 0.0
    coverage_percent: Optional[float] = None
    coverage_report_path: Optional[str] = None
    status: str = "pending"  # "pending", "running", "green", "red", "error"

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class CIWatcher:
    """Watches for file changes and runs tests automatically."""

    def __init__(self, project_root: Optional[Path] = None):
        self._root = project_root or PROJECT_ROOT
        self._status_dir = self._root / ".ci"
        self._status_dir.mkdir(exist_ok=True)
        self._coverage_dir = self._status_dir / "coverage"
        self._coverage_dir.mkdir(exist_ok=True)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_result: Optional[CIResult] = None
        self._lock = threading.Lock()
        self._pending_changes: list[str] = []
        self._debounce_timer: Optional[threading.Timer] = None

    def notify_change(self, filepath: str) -> None:
        """Called when a file changes. Debounces and triggers CI run."""
        with self._lock:
            self._pending_changes.append(filepath)
            if self._debounce_timer:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(DEBOUNCE_SECONDS, self._run_ci)
            self._debounce_timer.start()

    def _run_ci(self) -> None:
        """Execute the CI pipeline: fast tests -> full tests -> coverage."""
        with self._lock:
            changes = list(self._pending_changes)
            self._pending_changes.clear()

        if not changes:
            return

        result = CIResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            trigger="file_change",
            changed_files=changes,
            status="running",
        )
        self._write_status(result)

        # Phase 1: Fast tests — find relevant test files for changed code
        test_files = self._find_relevant_tests(changes)
        if test_files:
            start = time.monotonic()
            passed, output = self._run_pytest(test_files)
            result.fast_test_duration_s = time.monotonic() - start
            result.fast_test_passed = passed
            result.fast_test_output = output[-2000:]  # truncate
            if not passed:
                result.status = "red"
                self._last_result = result
                self._write_status(result)
                logger.info("CI fast tests FAILED for %d changed files", len(changes))
                return
        else:
            result.fast_test_passed = True

        # Phase 2: Full test suite
        start = time.monotonic()
        passed, output = self._run_pytest(["backend/tests/"])
        result.full_test_duration_s = time.monotonic() - start
        result.full_test_passed = passed
        result.full_test_output = output[-2000:]

        if not passed:
            result.status = "red"
            self._last_result = result
            self._write_status(result)
            logger.info("CI full tests FAILED")
            return

        # Phase 3: Coverage report
        coverage_pct, report_path = self._run_coverage()
        result.coverage_percent = coverage_pct
        result.coverage_report_path = report_path
        result.status = "green"
        self._last_result = result
        self._write_status(result)
        logger.info("CI GREEN — coverage: %.1f%%", coverage_pct or 0)

    def _find_relevant_tests(self, changed_files: list[str]) -> list[str]:
        """Map changed source files to their test files."""
        test_files = []
        for f in changed_files:
            p = Path(f)
            # If it's already a test file, include it directly
            if p.name.startswith("test_"):
                test_files.append(str(p))
                continue
            # Try to find matching test file
            if "backend/" in f and p.suffix == ".py":
                module_name = p.stem
                candidates = [
                    self._root / "backend" / "tests" / f"test_{module_name}.py",
                    self._root / "backend" / "tests" / f"test_{p.parent.name}_{module_name}.py",
                ]
                for c in candidates:
                    if c.exists():
                        test_files.append(str(c))
        return list(set(test_files))

    def _run_pytest(self, targets: list[str], with_coverage: bool = False) -> tuple[bool, str]:
        """Run pytest on given targets. Returns (passed, output)."""
        cmd = ["python", "-m", "pytest", "-v", "--tb=short", "-q"]
        if with_coverage:
            cmd.extend(["--cov=backend", "--cov-report=json:" + str(self._coverage_dir / "coverage.json")])
        cmd.extend(targets)

        try:
            from backend.services.process_registry import run_tracked_process
            proc = run_tracked_process(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self._root),
            )
            return proc.returncode == 0, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired:
            return False, "Test suite timed out after 300s"
        except Exception as e:
            return False, f"Test execution error: {e}"

    def _run_coverage(self) -> tuple[Optional[float], Optional[str]]:
        """Run full suite with coverage. Returns (percent, report_path)."""
        passed, _ = self._run_pytest(["backend/tests/"], with_coverage=True)
        if not passed:
            return None, None

        report_path = self._coverage_dir / "coverage.json"
        if report_path.exists():
            try:
                data = json.loads(report_path.read_text())
                total = data.get("totals", {})
                pct = total.get("percent_covered", 0.0)

                # Also generate HTML report
                html_dir = self._coverage_dir / "html"
                from backend.services.process_registry import run_tracked_process
                run_tracked_process(
                    ["python", "-m", "coverage", "html", "-d", str(html_dir)],
                    capture_output=True,
                    timeout=60,
                    cwd=str(self._root),
                )

                return pct, str(report_path)
            except Exception as e:
                logger.warning("Coverage parse error: %s", e)

        return None, None

    def _write_status(self, result: CIResult) -> None:
        """Write CI status to disk for agent tools to read."""
        status_file = self._status_dir / "status.json"
        try:
            status_file.write_text(json.dumps(result.to_dict(), indent=2))
        except OSError as e:
            logger.warning("Failed to write CI status: %s", e)

    def run_manual(self, trigger: str = "manual") -> CIResult:
        """Run CI pipeline manually (not file-triggered). Returns result."""
        result = CIResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            trigger=trigger,
            status="running",
        )
        self._write_status(result)

        # Full suite
        start = time.monotonic()
        passed, output = self._run_pytest(["backend/tests/"])
        result.full_test_duration_s = time.monotonic() - start
        result.full_test_passed = passed
        result.full_test_output = output[-2000:]
        result.fast_test_passed = passed

        if passed:
            coverage_pct, report_path = self._run_coverage()
            result.coverage_percent = coverage_pct
            result.coverage_report_path = report_path
            result.status = "green"
        else:
            result.status = "red"

        self._last_result = result
        self._write_status(result)
        return result

    def get_status(self) -> dict:
        """Get current CI status for API."""
        status_file = self._status_dir / "status.json"
        if status_file.exists():
            try:
                return json.loads(status_file.read_text())
            except Exception:
                pass
        return {"status": "unknown", "message": "No CI runs yet"}

    def get_coverage_for_show(self, show_slug: str) -> Optional[dict]:
        """Get coverage report for a specific show (from its last competition run)."""
        show_coverage = self._coverage_dir / f"{show_slug}.json"
        if show_coverage.exists():
            try:
                return json.loads(show_coverage.read_text())
            except Exception:
                pass
        return None

    def save_show_coverage(self, show_slug: str, coverage_data: dict) -> str:
        """Persist a coverage snapshot for a completed show (for scoring/judging)."""
        show_coverage = self._coverage_dir / f"{show_slug}.json"
        show_coverage.write_text(json.dumps(coverage_data, indent=2))
        return str(show_coverage)


# Singleton
_watcher: Optional[CIWatcher] = None


def get_ci_watcher() -> CIWatcher:
    global _watcher
    if _watcher is None:
        _watcher = CIWatcher()
    return _watcher
