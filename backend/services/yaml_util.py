"""Shared YAML utilities — atomic writes and consistent formatting."""

import os
import tempfile
from pathlib import Path

import yaml


def atomic_write(path: Path, content: str) -> None:
    """Write content to path atomically via tmp+rename."""
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        os.write(fd, content.encode())
        os.close(fd)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def safe_dump_yaml(data, **kw) -> str:
    """Dump YAML with consistent formatting."""
    kw.setdefault("default_flow_style", False)
    kw.setdefault("sort_keys", False)
    kw.setdefault("allow_unicode", True)
    return yaml.safe_dump(data, **kw)
