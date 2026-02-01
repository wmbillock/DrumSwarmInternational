"""File I/O tools for agent use — read_file, list_files, write_artifact, write_file.

All paths are relative to project root. Security boundaries:
- Path traversal blocked via normpath + startswith check
- Sensitive file blocklist for reads
- write_artifact restricted to artifact dirs (shows/, seasons/, corps/, docs/outputs/)
- write_file gated behind DSI_ENABLE_CODE_WRITES=1 env var + denylist
"""

import fnmatch
import os
from pathlib import Path
from typing import Callable

MAX_READ_BYTES = 50 * 1024  # 50KB truncation limit
MAX_LIST_ENTRIES = 100

# Patterns blocked from reading
READ_BLOCKLIST = (
    ".env",
    ".git/config",
    "credentials.json",
    "secrets.yaml",
    "secrets.json",
    "*.pem",
    "*.key",
)

# Directories where write_artifact is allowed
ARTIFACT_ALLOWLIST = (
    "shows/",
    "seasons/",
    "corps/",
    "docs/outputs/",
)

# Paths where write_file is NEVER allowed (even with env flag)
WRITE_DENYLIST = (
    "backend/services/",
    "backend/models/",
    "backend/api/",
    "backend/cli/",
    "backend/database.py",
    "alembic/",
    ".git/",
    ".env",
)


def _resolve_safe(project_root: Path, rel_path: str) -> Path | None:
    """Resolve a relative path safely, returning None if traversal detected."""
    normed = os.path.normpath(rel_path)
    if normed.startswith("..") or os.path.isabs(normed):
        return None
    full = (project_root / normed).resolve()
    if not str(full).startswith(str(project_root.resolve())):
        return None
    return full


def _is_blocklisted(rel_path: str) -> bool:
    """Check if a relative path matches the read blocklist."""
    normed = os.path.normpath(rel_path)
    for pattern in READ_BLOCKLIST:
        if fnmatch.fnmatch(normed, pattern):
            return True
        if fnmatch.fnmatch(os.path.basename(normed), pattern):
            return True
        if normed == pattern or normed.startswith(pattern):
            return True
    return False


def _in_allowlist(rel_path: str, allowlist: tuple[str, ...]) -> bool:
    """Check if a relative path starts with one of the allowed prefixes."""
    normed = os.path.normpath(rel_path)
    # Normalize to forward slashes for comparison
    normed_fwd = normed.replace(os.sep, "/")
    return any(normed_fwd.startswith(prefix.rstrip("/")) for prefix in allowlist)


def _in_denylist(rel_path: str) -> bool:
    """Check if a relative path is in the write denylist."""
    normed = os.path.normpath(rel_path).replace(os.sep, "/")
    for pattern in WRITE_DENYLIST:
        if normed == pattern.rstrip("/") or normed.startswith(pattern):
            return True
    return False


def make_file_tools(project_root: Path) -> dict[str, Callable]:
    """Build file tool functions bound to a specific project root.

    Returns a dict of {tool_name: callable} ready for registration.
    """
    root = Path(project_root).resolve()

    def read_file(db, file_path: str) -> dict:
        full = _resolve_safe(root, file_path)
        if full is None:
            return {"error": "Access denied: path traversal blocked"}
        rel = os.path.normpath(file_path)
        if _is_blocklisted(rel):
            return {"error": f"Access denied: '{rel}' is blocked"}
        if not full.is_file():
            return {"error": f"File not found: {rel}"}
        try:
            content = full.read_text(errors="replace")
        except Exception as e:
            return {"error": f"Read failed: {e}"}
        truncated = len(content) > MAX_READ_BYTES
        if truncated:
            content = content[:MAX_READ_BYTES] + "\n... [truncated at 50KB]"
        return {
            "content": content,
            "path": rel,
            "size": full.stat().st_size,
            "truncated": truncated,
        }

    def list_files(db, directory: str = "", pattern: str = "") -> dict:
        full = _resolve_safe(root, directory or ".")
        if full is None:
            return {"error": "Access denied: path traversal blocked"}
        if not full.is_dir():
            return {"error": f"Not a directory: {directory}"}
        try:
            entries = []
            for item in sorted(full.iterdir()):
                rel = str(item.relative_to(root))
                if pattern and not fnmatch.fnmatch(item.name, pattern):
                    continue
                suffix = "/" if item.is_dir() else ""
                entries.append(rel + suffix)
                if len(entries) >= MAX_LIST_ENTRIES:
                    return {"files": entries, "capped": True}
            return {"files": entries, "capped": False}
        except Exception as e:
            return {"error": f"List failed: {e}"}

    def write_artifact(db, file_path: str, content: str) -> dict:
        full = _resolve_safe(root, file_path)
        if full is None:
            return {"error": "Access denied: path traversal blocked"}
        rel = os.path.normpath(file_path)
        if not _in_allowlist(rel, ARTIFACT_ALLOWLIST):
            return {"error": f"Access denied: writes only allowed under {', '.join(ARTIFACT_ALLOWLIST)}"}
        try:
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content)
            return {"success": True, "path": rel, "bytes_written": len(content.encode())}
        except Exception as e:
            return {"error": f"Write failed: {e}"}

    def write_file(db, file_path: str, content: str) -> dict:
        if os.environ.get("DSI_ENABLE_CODE_WRITES") != "1":
            return {"error": "write_file is disabled. Set DSI_ENABLE_CODE_WRITES=1 to enable."}
        full = _resolve_safe(root, file_path)
        if full is None:
            return {"error": "Access denied: path traversal blocked"}
        rel = os.path.normpath(file_path)
        if _in_denylist(rel):
            return {"error": f"Access denied: '{rel}' is in the write denylist"}
        try:
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content)
            return {"success": True, "path": rel, "bytes_written": len(content.encode())}
        except Exception as e:
            return {"error": f"Write failed: {e}"}

    return {
        "read_file": read_file,
        "list_files": list_files,
        "write_artifact": write_artifact,
        "write_file": write_file,
    }
