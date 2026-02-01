"""Subprocess-based tests for `dci doctor` CLI command."""

import json
import subprocess
import sys

import pytest

PROJECT_ROOT = subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True
).strip()


def run_doctor(*extra_args: str, global_args: tuple[str, ...] = ()) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "backend.cli.main", *global_args, "doctor", *extra_args],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=30,
    )


class TestDoctorCLI:
    def test_doctor_exits_zero(self):
        result = run_doctor()
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "PASS" in result.stdout

    def test_doctor_json_flag(self):
        result = run_doctor("--json")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert "ok" in data

    def test_doctor_verbose_flag(self):
        brief = run_doctor()
        verbose = run_doctor(global_args=("--verbose",))
        assert verbose.returncode == 0, f"stderr: {verbose.stderr}"
        assert len(verbose.stdout) >= len(brief.stdout)

    def test_doctor_json_has_checks_array(self):
        result = run_doctor("--json")
        data = json.loads(result.stdout)
        assert isinstance(data["checks"], list)
        assert len(data["checks"]) > 0
        first = data["checks"][0]
        assert "name" in first
        assert "passed" in first
