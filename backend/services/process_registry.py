"""Process registry — tracks subprocess PIDs spawned by LLM clients.

Provides a singleton registry so the app shutdown hook and parade-rest
can reliably kill all child processes. Persists PID list to disk for
external cleanup tools (e.g. `./dci parade-rest`).
"""

import atexit
import json
import logging
import os
import signal
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PID_FILE = Path("/tmp/dci-swarm-pids.json")
WARN_THRESHOLD = int(os.environ.get("DSI_PROCESS_WARN_THRESHOLD", "10"))


class ProcessRegistry:
    """Thread-safe singleton tracking subprocess PIDs."""

    _instance: Optional["ProcessRegistry"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ProcessRegistry":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._pids: set[int] = set()
                cls._instance._pid_lock = threading.Lock()
        return cls._instance

    def register(self, pid: int) -> None:
        with self._pid_lock:
            self._pids.add(pid)
            self._persist()
        logger.debug("Registered subprocess PID %d (total: %d)", pid, len(self._pids))

    def unregister(self, pid: int) -> None:
        with self._pid_lock:
            self._pids.discard(pid)
            self._persist()

    @property
    def active_pids(self) -> set[int]:
        """Return PIDs that are still alive."""
        with self._pid_lock:
            alive = set()
            for pid in list(self._pids):
                try:
                    os.kill(pid, 0)  # signal 0 = check if alive
                    alive.add(pid)
                except OSError:
                    self._pids.discard(pid)
            self._persist()
            return alive

    @property
    def count(self) -> int:
        return len(self.active_pids)

    def check_threshold(self) -> Optional[str]:
        """Return a warning message if active count exceeds threshold, else None."""
        count = self.count
        if count >= WARN_THRESHOLD:
            return f"Process count ({count}) exceeds threshold ({WARN_THRESHOLD})"
        return None

    def kill_all(self) -> int:
        """SIGTERM all registered PIDs, then SIGKILL stragglers. Returns kill count."""
        pids = self.active_pids
        if not pids:
            return 0

        killed = 0
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
                killed += 1
            except OSError:
                pass

        # Give processes 2s to exit, then force-kill
        import time
        time.sleep(2)

        for pid in pids:
            try:
                os.kill(pid, 0)  # still alive?
                os.kill(pid, signal.SIGKILL)
                logger.warning("Force-killed PID %d", pid)
            except OSError:
                pass

        with self._pid_lock:
            self._pids.clear()
            self._persist()

        logger.info("Killed %d subprocess(es)", killed)
        return killed

    def _persist(self) -> None:
        """Write current PIDs to disk for external tools."""
        try:
            PID_FILE.write_text(json.dumps(list(self._pids)))
        except OSError:
            pass

    def get_stats(self) -> dict:
        return {
            "active_processes": self.count,
            "warn_threshold": WARN_THRESHOLD,
            "over_threshold": self.count >= WARN_THRESHOLD,
        }


def get_process_registry() -> ProcessRegistry:
    return ProcessRegistry()


# Auto-cleanup on interpreter exit
def _cleanup():
    try:
        registry = ProcessRegistry()
        if registry.count > 0:
            logger.info("Shutdown: cleaning up %d subprocess(es)", registry.count)
            registry.kill_all()
    except Exception:
        pass

atexit.register(_cleanup)
