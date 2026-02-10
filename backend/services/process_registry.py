"""Process registry — tracks subprocesses spawned by the swarm.

Provides a singleton registry so the app shutdown hook and parade-rest
can reliably kill child processes. Persists PID list to disk per instance
for safe reaping on restart (supports multiple concurrent swarms).
"""

import atexit
import dataclasses
import json
import logging
import os
import signal
import threading
import time
import uuid
from pathlib import Path
from typing import Optional
import subprocess

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
INSTANCE_DIR = PROJECT_ROOT / ".dci"
INSTANCE_FILE = INSTANCE_DIR / "instance-id"
PID_FILE_PREFIX = "dci-swarm-pids"
WARN_THRESHOLD = int(os.environ.get("DSI_PROCESS_WARN_THRESHOLD", "10"))


@dataclasses.dataclass(frozen=True)
class ProcessRecord:
    pid: int
    pgid: int
    cmd: list[str]
    cwd: str
    started_at: float
    instance_id: str


class ProcessRegistry:
    """Thread-safe singleton tracking subprocesses for this instance."""

    _instance: Optional["ProcessRegistry"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ProcessRegistry":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._records: dict[int, ProcessRecord] = {}
                cls._instance._pid_lock = threading.Lock()
                cls._instance._instance_id = cls._resolve_instance_id()
                cls._instance._orphans_reaped = 0
        return cls._instance

    @property
    def instance_id(self) -> str:
        return self._instance_id

    @staticmethod
    def _resolve_instance_id() -> str:
        instance_id = os.environ.get("DSI_INSTANCE_ID")
        if not instance_id:
            try:
                if INSTANCE_FILE.exists():
                    instance_id = INSTANCE_FILE.read_text().strip()
                    logger.warning(
                        "DSI_INSTANCE_ID not set; using shared instance id from %s. "
                        "Set DSI_INSTANCE_ID for concurrent swarms.",
                        INSTANCE_FILE,
                    )
            except OSError:
                instance_id = None
        if not instance_id:
            instance_id = uuid.uuid4().hex
        os.environ["DSI_INSTANCE_ID"] = instance_id
        try:
            INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
            INSTANCE_FILE.write_text(instance_id)
        except OSError:
            pass
        return instance_id

    def _pid_file(self) -> Path:
        return Path("/tmp") / f"{PID_FILE_PREFIX}-{self._instance_id}.json"

    def register(self, pid: int, cmd: Optional[list[str]] = None, cwd: Optional[str] = None, pgid: Optional[int] = None) -> None:
        with self._pid_lock:
            if pgid is None:
                try:
                    pgid = os.getpgid(pid)
                except OSError:
                    pgid = pid
            record = ProcessRecord(
                pid=pid,
                pgid=pgid,
                cmd=cmd or [],
                cwd=cwd or "",
                started_at=time.time(),
                instance_id=self._instance_id,
            )
            self._records[pid] = record
            self._persist()
        logger.debug("Registered subprocess PID %d (total: %d)", pid, len(self._records))

    def unregister(self, pid: int) -> None:
        with self._pid_lock:
            self._records.pop(pid, None)
            self._persist()

    @property
    def active_pids(self) -> set[int]:
        """Return PIDs that are still alive."""
        with self._pid_lock:
            alive = set()
            for pid in list(self._records.keys()):
                try:
                    os.kill(pid, 0)  # signal 0 = check if alive
                    alive.add(pid)
                except OSError:
                    self._records.pop(pid, None)
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
        with self._pid_lock:
            records = list(self._records.values())
        if not records:
            return 0

        killed = 0
        for record in records:
            try:
                os.killpg(record.pgid, signal.SIGTERM)
                killed += 1
            except OSError:
                try:
                    os.kill(record.pid, signal.SIGTERM)
                    killed += 1
                except OSError:
                    pass

        # Give processes 2s to exit, then force-kill
        time.sleep(2)

        for record in records:
            try:
                os.kill(record.pid, 0)  # still alive?
                try:
                    os.killpg(record.pgid, signal.SIGKILL)
                except OSError:
                    os.kill(record.pid, signal.SIGKILL)
                logger.warning("Force-killed PID %d", record.pid)
            except OSError:
                pass

        with self._pid_lock:
            self._records.clear()
            self._persist()

        logger.info("Killed %d subprocess(es)", killed)
        return killed

    def _persist(self) -> None:
        """Write current records to disk for external tools."""
        try:
            payload = [dataclasses.asdict(r) for r in self._records.values()]
            self._pid_file().write_text(json.dumps(payload))
        except OSError:
            pass

    def get_stats(self) -> dict:
        return {
            "active_processes": self.count,
            "warn_threshold": WARN_THRESHOLD,
            "over_threshold": self.count >= WARN_THRESHOLD,
            "orphans_reaped": self._orphans_reaped,
            "instance_id": self._instance_id,
            "pid_file": str(self._pid_file()),
        }

    def reap_orphans(self) -> int:
        """Kill orphaned processes from the last run of this instance."""
        pid_file = self._pid_file()
        if not pid_file.exists():
            return 0
        try:
            data = json.loads(pid_file.read_text())
        except Exception:
            return 0
        if not isinstance(data, list):
            return 0

        killed = 0
        for item in data:
            try:
                record = ProcessRecord(**item)
            except Exception:
                continue
            if record.instance_id != self._instance_id:
                continue
            if not _is_process_alive(record.pid):
                continue
            if not _matches_record(record):
                continue
            if _kill_record(record):
                killed += 1

        try:
            pid_file.write_text(json.dumps([]))
        except OSError:
            pass
        if killed:
            self._orphans_reaped += killed
            logger.info("Startup: reaped %d orphaned subprocess(es)", killed)
        return killed


def get_process_registry() -> ProcessRegistry:
    return ProcessRegistry()


def start_tracked_process(
    cmd: list[str],
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    text: bool = True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
) -> subprocess.Popen:
    """Start a subprocess in its own process group and register it."""
    proc = subprocess.Popen(
        cmd,
        stdout=stdout,
        stderr=stderr,
        text=text,
        cwd=cwd,
        env=env,
        start_new_session=True,
    )
    registry = get_process_registry()
    try:
        pgid = os.getpgid(proc.pid)
    except OSError:
        pgid = proc.pid
    registry.register(proc.pid, cmd=cmd, cwd=cwd, pgid=pgid)
    return proc


def run_tracked_process(
    cmd: list[str],
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    text: bool = True,
    timeout: Optional[int] = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    """Run a subprocess with tracking and timeouts."""
    stdout = subprocess.PIPE if capture_output else None
    stderr = subprocess.PIPE if capture_output else None
    proc = start_tracked_process(cmd, cwd=cwd, env=env, text=text, stdout=stdout, stderr=stderr)
    registry = get_process_registry()
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            pgid = os.getpgid(proc.pid)
        except OSError:
            pgid = proc.pid
        _kill_record(ProcessRecord(
            pid=proc.pid,
            pgid=pgid,
            cmd=cmd,
            cwd=cwd or "",
            started_at=time.time(),
            instance_id=registry.instance_id,
        ))
        raise
    finally:
        registry.unregister(proc.pid)
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)

def _is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _get_cmdline(pid: int) -> str:
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _matches_record(record: ProcessRecord) -> bool:
    try:
        if os.getpgid(record.pid) != record.pgid:
            return False
    except OSError:
        return False

    if not record.cmd:
        return False
    cmdline = _get_cmdline(record.pid)
    if not cmdline:
        return False
    needle = record.cmd[0]
    return needle in cmdline


def _kill_record(record: ProcessRecord) -> bool:
    try:
        os.killpg(record.pgid, signal.SIGTERM)
    except OSError:
        try:
            os.kill(record.pid, signal.SIGTERM)
        except OSError:
            return False
    time.sleep(2)
    if _is_process_alive(record.pid):
        try:
            os.killpg(record.pgid, signal.SIGKILL)
        except OSError:
            try:
                os.kill(record.pid, signal.SIGKILL)
            except OSError:
                return False
    return True


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
