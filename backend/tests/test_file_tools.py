"""Tests for file I/O tools: read_file, list_files, write_artifact, write_file.

Tests exercise the tool functions directly (no subprocess needed) against
a tmp_path project root.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _make_project(tmp_path: Path) -> Path:
    """Create a minimal project layout for file tool testing."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n")
    (tmp_path / "shows" / "demo").mkdir(parents=True)
    (tmp_path / "shows" / "demo" / "status.yaml").write_text("status: draft\n")
    (tmp_path / "seasons" / "s1").mkdir(parents=True)
    (tmp_path / "corps" / "bd").mkdir(parents=True)
    (tmp_path / "docs" / "outputs").mkdir(parents=True)
    (tmp_path / "backend" / "services").mkdir(parents=True)
    (tmp_path / "backend" / "__init__.py").write_text("")
    (tmp_path / "backend" / "services" / "corps_service.py").write_text("# service\n")
    (tmp_path / ".env").write_text("SECRET=hunter2\n")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]\n")
    (tmp_path / "frontend" / "src").mkdir(parents=True)
    (tmp_path / "frontend" / "src" / "App.tsx").write_text("export default App;\n")
    return tmp_path


@pytest.fixture
def project(tmp_path):
    return _make_project(tmp_path)


@pytest.fixture
def db():
    return MagicMock()


# ---- Import helpers (patch project root) ----

def _get_tools(project_root: Path):
    """Import and build the file tool functions bound to a specific project root."""
    from backend.services.file_tools import make_file_tools
    return make_file_tools(project_root)


# ===========================================================================
# read_file
# ===========================================================================

class TestReadFile:
    def test_read_valid_file(self, project, db):
        tools = _get_tools(project)
        result = tools["read_file"](db, file_path="pyproject.toml")
        assert "content" in result
        assert "test" in result["content"]
        assert result["path"] == "pyproject.toml"

    def test_read_nested_file(self, project, db):
        tools = _get_tools(project)
        result = tools["read_file"](db, file_path="frontend/src/App.tsx")
        assert "App" in result["content"]

    def test_traversal_blocked(self, project, db):
        tools = _get_tools(project)
        result = tools["read_file"](db, file_path="../../../etc/passwd")
        assert "error" in result
        assert "traversal" in result["error"].lower() or "denied" in result["error"].lower()

    def test_dotdot_in_middle_blocked(self, project, db):
        tools = _get_tools(project)
        result = tools["read_file"](db, file_path="shows/../../etc/passwd")
        assert "error" in result

    def test_blocklist_env(self, project, db):
        tools = _get_tools(project)
        result = tools["read_file"](db, file_path=".env")
        assert "error" in result
        assert "denied" in result["error"].lower() or "blocked" in result["error"].lower()

    def test_blocklist_git_config(self, project, db):
        tools = _get_tools(project)
        result = tools["read_file"](db, file_path=".git/config")
        assert "error" in result

    def test_truncation(self, project, db):
        # Write a file larger than 50KB
        big = "x" * (60 * 1024)
        (project / "bigfile.txt").write_text(big)
        tools = _get_tools(project)
        result = tools["read_file"](db, file_path="bigfile.txt")
        assert len(result["content"]) <= 50 * 1024 + 100  # small margin for truncation message
        assert result.get("truncated") is True

    def test_file_not_found(self, project, db):
        tools = _get_tools(project)
        result = tools["read_file"](db, file_path="nonexistent.txt")
        assert "error" in result


# ===========================================================================
# list_files
# ===========================================================================

class TestListFiles:
    def test_list_basic(self, project, db):
        tools = _get_tools(project)
        result = tools["list_files"](db, directory="shows")
        assert "files" in result
        assert any("demo" in f for f in result["files"])

    def test_list_with_glob(self, project, db):
        tools = _get_tools(project)
        result = tools["list_files"](db, directory="frontend/src", pattern="*.tsx")
        assert any("App.tsx" in f for f in result["files"])

    def test_list_capped(self, project, db):
        # Create 150 files
        d = project / "many"
        d.mkdir()
        for i in range(150):
            (d / f"f{i}.txt").write_text("")
        tools = _get_tools(project)
        result = tools["list_files"](db, directory="many")
        assert len(result["files"]) <= 100
        assert result.get("capped") is True

    def test_traversal_blocked(self, project, db):
        tools = _get_tools(project)
        result = tools["list_files"](db, directory="../../")
        assert "error" in result


# ===========================================================================
# write_artifact
# ===========================================================================

class TestWriteArtifact:
    def test_write_under_shows(self, project, db):
        tools = _get_tools(project)
        result = tools["write_artifact"](db, file_path="shows/demo/notes.md", content="hello")
        assert result.get("success") is True
        assert (project / "shows" / "demo" / "notes.md").read_text() == "hello"

    def test_write_under_seasons(self, project, db):
        tools = _get_tools(project)
        result = tools["write_artifact"](db, file_path="seasons/s1/output.txt", content="data")
        assert result.get("success") is True

    def test_write_under_corps(self, project, db):
        tools = _get_tools(project)
        result = tools["write_artifact"](db, file_path="corps/bd/notes.md", content="info")
        assert result.get("success") is True

    def test_write_under_docs_outputs(self, project, db):
        tools = _get_tools(project)
        result = tools["write_artifact"](db, file_path="docs/outputs/report.md", content="report")
        assert result.get("success") is True

    def test_write_outside_allowlist_blocked(self, project, db):
        tools = _get_tools(project)
        result = tools["write_artifact"](db, file_path="backend/services/corps_service.py", content="pwned")
        assert "error" in result
        # Original file untouched
        assert (project / "backend" / "services" / "corps_service.py").read_text() == "# service\n"

    def test_write_similar_prefix_blocked(self, project, db):
        tools = _get_tools(project)
        result = tools["write_artifact"](db, file_path="shows_backup/notes.md", content="nope")
        assert "error" in result
        assert not (project / "shows_backup" / "notes.md").exists()

    def test_write_traversal_blocked(self, project, db):
        tools = _get_tools(project)
        result = tools["write_artifact"](db, file_path="shows/../../etc/passwd", content="bad")
        assert "error" in result

    def test_write_creates_parent_dirs(self, project, db):
        tools = _get_tools(project)
        result = tools["write_artifact"](db, file_path="shows/demo/sub/deep/file.txt", content="ok")
        assert result.get("success") is True
        assert (project / "shows" / "demo" / "sub" / "deep" / "file.txt").read_text() == "ok"


# ===========================================================================
# write_file (gated behind DSI_ENABLE_CODE_WRITES)
# ===========================================================================

class TestWriteFile:
    def test_gated_off_by_default(self, project, db):
        os.environ.pop("DSI_ENABLE_CODE_WRITES", None)
        tools = _get_tools(project)
        result = tools["write_file"](db, file_path="frontend/src/new.tsx", content="code")
        assert "error" in result
        assert "DSI_ENABLE_CODE_WRITES" in result["error"]

    def test_gated_on_allows_write(self, project, db):
        os.environ["DSI_ENABLE_CODE_WRITES"] = "1"
        try:
            tools = _get_tools(project)
            result = tools["write_file"](db, file_path="frontend/src/new.tsx", content="code")
            assert result.get("success") is True
            assert (project / "frontend" / "src" / "new.tsx").read_text() == "code"
        finally:
            os.environ.pop("DSI_ENABLE_CODE_WRITES", None)

    def test_denylist_backend_services(self, project, db):
        os.environ["DSI_ENABLE_CODE_WRITES"] = "1"
        try:
            tools = _get_tools(project)
            result = tools["write_file"](db, file_path="backend/services/corps_service.py", content="pwned")
            assert "error" in result
            assert (project / "backend" / "services" / "corps_service.py").read_text() == "# service\n"
        finally:
            os.environ.pop("DSI_ENABLE_CODE_WRITES", None)

    def test_traversal_blocked(self, project, db):
        os.environ["DSI_ENABLE_CODE_WRITES"] = "1"
        try:
            tools = _get_tools(project)
            result = tools["write_file"](db, file_path="../../../etc/passwd", content="bad")
            assert "error" in result
        finally:
            os.environ.pop("DSI_ENABLE_CODE_WRITES", None)
