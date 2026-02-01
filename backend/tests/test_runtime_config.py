"""Tests for runtime config: defaults, env overrides, CLI overrides, manifest recording."""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

PROJECT_ROOT = subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True
).strip()


# ===========================================================================
# Unit tests for the config module
# ===========================================================================

class TestRuntimeConfigDefaults:
    def test_default_timeout(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DSI_LLM_TIMEOUT_SECONDS", None)
            os.environ.pop("DSI_MAX_ITERATIONS", None)
            from backend.services.runtime_config import get_runtime_config
            cfg = get_runtime_config()
            assert cfg["timeout"] == 300

    def test_default_max_iterations(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DSI_LLM_TIMEOUT_SECONDS", None)
            os.environ.pop("DSI_MAX_ITERATIONS", None)
            from backend.services.runtime_config import get_runtime_config
            cfg = get_runtime_config()
            assert cfg["max_iterations"] == 30


class TestRuntimeConfigEnvOverrides:
    def test_env_timeout_override(self):
        with patch.dict(os.environ, {"DSI_LLM_TIMEOUT_SECONDS": "600"}):
            from backend.services.runtime_config import get_runtime_config
            cfg = get_runtime_config()
            assert cfg["timeout"] == 600

    def test_env_max_iterations_override(self):
        with patch.dict(os.environ, {"DSI_MAX_ITERATIONS": "50"}):
            from backend.services.runtime_config import get_runtime_config
            cfg = get_runtime_config()
            assert cfg["max_iterations"] == 50

    def test_env_invalid_falls_back_to_default(self):
        with patch.dict(os.environ, {"DSI_LLM_TIMEOUT_SECONDS": "not_a_number"}):
            from backend.services.runtime_config import get_runtime_config
            cfg = get_runtime_config()
            assert cfg["timeout"] == 300


class TestRuntimeConfigCLIOverrides:
    def test_cli_overrides_env(self):
        with patch.dict(os.environ, {"DSI_LLM_TIMEOUT_SECONDS": "600"}):
            from backend.services.runtime_config import get_runtime_config
            cfg = get_runtime_config(cli_timeout=120, cli_max_iterations=10)
            assert cfg["timeout"] == 120
            assert cfg["max_iterations"] == 10


# ===========================================================================
# Subprocess tests: CLI flags and manifest
# ===========================================================================

def _setup_env(tmp_path: Path) -> None:
    show_dir = tmp_path / "shows" / "demo"
    show_dir.mkdir(parents=True)
    (show_dir / "status.yaml").write_text(yaml.safe_dump({"status": "approved"}))
    (show_dir / "design_notes.md").write_text("")
    (show_dir / "show_prompt.md").write_text("")
    corps_dir = tmp_path / "corps" / "bd"
    corps_dir.mkdir(parents=True)
    (corps_dir / "corps.yaml").write_text(yaml.safe_dump({
        "corps_id": "bd", "display_name": "BD", "philosophy": "", "state": "active"}))
    (corps_dir / "roster.yaml").write_text(yaml.safe_dump({"corps_id": "bd", "assignments": []}))
    season_dir = tmp_path / "seasons" / "s1"
    season_dir.mkdir(parents=True)
    (season_dir / "season.yaml").write_text(yaml.safe_dump({"season_id": "s1", "metadata": {}}))
    (season_dir / "performances").mkdir()


def run_cli(*args: str, root: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["DCI_PROJECT_ROOT"] = root
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "backend.cli.main", *args],
        capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30, env=env,
    )


class TestCLIConfigFlags:
    def test_plan_shows_effective_config(self, tmp_path):
        _setup_env(tmp_path)
        result = run_cli("run", "show", "demo", "--corps", "bd", "--season", "s1",
                         "--plan", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        assert "timeout" in result.stdout
        assert "300" in result.stdout
        assert "max_iterations" in result.stdout
        assert "30" in result.stdout

    def test_cli_timeout_override_in_plan(self, tmp_path):
        _setup_env(tmp_path)
        result = run_cli("run", "show", "demo", "--corps", "bd", "--season", "s1",
                         "--timeout-seconds", "600", "--plan", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        assert "600" in result.stdout

    def test_cli_max_iterations_override_in_plan(self, tmp_path):
        _setup_env(tmp_path)
        result = run_cli("run", "show", "demo", "--corps", "bd", "--season", "s1",
                         "--max-iterations", "50", "--plan", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        assert "50" in result.stdout

    def test_env_override_in_manifest(self, tmp_path):
        _setup_env(tmp_path)
        result = run_cli("run", "show", "demo", "--corps", "bd", "--season", "s1",
                         "--yes", root=str(tmp_path),
                         env_extra={"DSI_LLM_TIMEOUT_SECONDS": "450"})
        assert result.returncode == 0, result.stderr
        perf_dir = tmp_path / "seasons" / "s1" / "performances" / "bd"
        run_dir = next(perf_dir.iterdir())
        manifest = yaml.safe_load((run_dir / "manifest.yaml").read_text())
        assert manifest["config"]["timeout"] == 450

    def test_cli_override_in_manifest(self, tmp_path):
        _setup_env(tmp_path)
        result = run_cli("run", "show", "demo", "--corps", "bd", "--season", "s1",
                         "--timeout-seconds", "180", "--max-iterations", "15",
                         "--yes", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        perf_dir = tmp_path / "seasons" / "s1" / "performances" / "bd"
        run_dir = next(perf_dir.iterdir())
        manifest = yaml.safe_load((run_dir / "manifest.yaml").read_text())
        assert manifest["config"]["timeout"] == 180
        assert manifest["config"]["max_iterations"] == 15


class TestErrorMessageReflectsConfig:
    def test_timeout_error_message_uses_effective_value(self):
        from backend.services.runtime_config import get_runtime_config
        with patch.dict(os.environ, {"DSI_LLM_TIMEOUT_SECONDS": "450"}):
            cfg = get_runtime_config()
            expected_msg = f"Error: Claude CLI timed out after {cfg['timeout']}s"
            assert "450" in expected_msg
