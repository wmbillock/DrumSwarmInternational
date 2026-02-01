"""Subprocess-based tests for persistent-artifact CLI commands.

Every mutating test uses a temp dir via DCI_PROJECT_ROOT so the real repo is never touched.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True
).strip()


def run_cli(*args: str, root: str | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if root:
        env["DCI_PROJECT_ROOT"] = root
    return subprocess.run(
        [sys.executable, "-m", "backend.cli.main", *args],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=30,
        env=env,
    )


# ---------------------------------------------------------------------------
# pool init
# ---------------------------------------------------------------------------

class TestPoolInit:
    def test_pool_init_plan(self, tmp_path):
        result = run_cli("pool", "init", "--plan", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        assert "ledger.yaml" in result.stdout
        assert "agents" in result.stdout
        # No files written
        assert not (tmp_path / "talent_pool").exists()

    def test_pool_init_yes(self, tmp_path):
        result = run_cli("pool", "init", "--yes", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        assert (tmp_path / "talent_pool" / "ledger.yaml").is_file()
        assert (tmp_path / "talent_pool" / "agents").is_dir()

    def test_pool_init_idempotent(self, tmp_path):
        r1 = run_cli("pool", "init", "--yes", root=str(tmp_path))
        r2 = run_cli("pool", "init", "--yes", root=str(tmp_path))
        assert r1.returncode == 0
        assert r2.returncode == 0
        assert (tmp_path / "talent_pool" / "ledger.yaml").is_file()


# ---------------------------------------------------------------------------
# pool list
# ---------------------------------------------------------------------------

class TestPoolList:
    def test_pool_list_empty(self, tmp_path):
        run_cli("pool", "init", "--yes", root=str(tmp_path))
        result = run_cli("pool", "list", root=str(tmp_path))
        assert result.returncode == 0, result.stderr

    def test_pool_list_instrument_filter(self, tmp_path):
        # Set up pool with one agent
        run_cli("pool", "init", "--yes", root=str(tmp_path))
        agent = {
            "agent_id": "test-1",
            "display_name": "Test Agent",
            "primary_instrument": "brass_tech",
            "availability": "active",
        }
        (tmp_path / "talent_pool" / "agents" / "test-1.yaml").write_text(
            yaml.safe_dump(agent)
        )
        ledger = {"agents": [
            {"agent_id": "test-1", "display_name": "Test Agent",
             "primary_instrument": "brass_tech", "availability": "active"},
        ]}
        (tmp_path / "talent_pool" / "ledger.yaml").write_text(
            yaml.safe_dump(ledger)
        )
        result = run_cli("pool", "list", "--instrument", "brass_tech", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        assert "test-1" in result.stdout


# ---------------------------------------------------------------------------
# corps init
# ---------------------------------------------------------------------------

class TestCorpsInit:
    def test_corps_init_plan(self, tmp_path):
        result = run_cli("corps", "init", "test-corps", "--plan", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        assert "corps.yaml" in result.stdout
        assert not (tmp_path / "corps" / "test-corps").exists()

    def test_corps_init_yes(self, tmp_path):
        result = run_cli("corps", "init", "test-corps", "--yes", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        corps_dir = tmp_path / "corps" / "test-corps"
        assert (corps_dir / "corps.yaml").is_file()
        assert (corps_dir / "roster.yaml").is_file()

    def test_corps_init_idempotent(self, tmp_path):
        r1 = run_cli("corps", "init", "test-corps", "--yes", root=str(tmp_path))
        r2 = run_cli("corps", "init", "test-corps", "--yes", root=str(tmp_path))
        assert r1.returncode == 0
        assert r2.returncode == 0


# ---------------------------------------------------------------------------
# show create
# ---------------------------------------------------------------------------

class TestShowCreate:
    def test_show_create_plan(self, tmp_path):
        result = run_cli("show", "create", "my-show", "--title", "My Show",
                         "--plan", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        assert "my-show" in result.stdout
        assert not (tmp_path / "shows" / "my-show").exists()

    def test_show_create_yes(self, tmp_path):
        result = run_cli("show", "create", "my-show", "--title", "My Show",
                         "--yes", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        status_file = tmp_path / "shows" / "my-show" / "status.yaml"
        assert status_file.is_file()
        data = yaml.safe_load(status_file.read_text())
        assert data["status"] == "draft"


# ---------------------------------------------------------------------------
# show status
# ---------------------------------------------------------------------------

class TestShowStatus:
    def test_show_status(self, tmp_path):
        run_cli("show", "create", "my-show", "--title", "My Show",
                "--yes", root=str(tmp_path))
        result = run_cli("show", "status", "my-show", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        assert "draft" in result.stdout


# ---------------------------------------------------------------------------
# show approve
# ---------------------------------------------------------------------------

class TestShowApprove:
    def _create_show(self, tmp_path):
        run_cli("show", "create", "my-show", "--title", "My Show",
                "--yes", root=str(tmp_path))

    def test_show_approve_plan(self, tmp_path):
        self._create_show(tmp_path)
        result = run_cli("show", "approve", "my-show", "--plan", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        assert "approved" in result.stdout
        # Status should still be draft
        data = yaml.safe_load(
            (tmp_path / "shows" / "my-show" / "status.yaml").read_text()
        )
        assert data["status"] == "draft"

    def test_show_approve_yes(self, tmp_path):
        self._create_show(tmp_path)
        result = run_cli("show", "approve", "my-show", "--yes", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        data = yaml.safe_load(
            (tmp_path / "shows" / "my-show" / "status.yaml").read_text()
        )
        assert data["status"] == "approved"

    def test_show_approve_no_flag(self, tmp_path):
        self._create_show(tmp_path)
        result = run_cli("show", "approve", "my-show", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        assert "--yes" in result.stdout
        # Status unchanged
        data = yaml.safe_load(
            (tmp_path / "shows" / "my-show" / "status.yaml").read_text()
        )
        assert data["status"] == "draft"
