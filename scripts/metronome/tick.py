#!/usr/bin/env python3
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import request, error


ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "logs" / "metronome"
ALERT_LOG = LOG_DIR / "alerts.log"
STATE_FILE = LOG_DIR / "state.json"

BASE_URL = os.environ.get("DCI_BASE_URL", "http://localhost:8000").rstrip("/")
TIMEOUT_S = 30
STALL_MINUTES = 5
FAILURE_THRESHOLD = 3


def now_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_line(path: Path, payload: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


def api_request(method: str, path: str, body: dict | None = None, timeout: int = TIMEOUT_S):
    url = f"{BASE_URL}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=timeout) as resp:
        content = resp.read()
        if not content:
            return None
        return json.loads(content.decode("utf-8"))


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state))


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.log"

    try:
        health = api_request("GET", "/api/v1/system/health", timeout=10)
    except Exception as e:
        log_line(log_path, {"timestamp": now_ts(), "level": "error", "event": "backend_unavailable", "error": str(e)})
        return 1

    try:
        corps_list = api_request("GET", "/api/v1/corps?include_system=false", timeout=10) or []
    except Exception as e:
        log_line(log_path, {"timestamp": now_ts(), "level": "error", "event": "corps_list_failed", "error": str(e)})
        return 1

    try:
        agents_overview = api_request("GET", "/api/v1/system/agents", timeout=10) or []
    except Exception as e:
        agents_overview = []
        log_line(log_path, {"timestamp": now_ts(), "level": "error", "event": "agents_list_failed", "error": str(e)})

    state = load_state()
    failure_counts = state.get("failure_counts", {})

    summary = {
        "timestamp": now_ts(),
        "sessions": health.get("total_sessions") if isinstance(health, dict) else None,
        "reps_completed": health.get("completed_reps") if isinstance(health, dict) else None,
        "reps_failed": health.get("failed_reps") if isinstance(health, dict) else None,
        "corps_checked": 0,
        "corps_stalled": 0,
        "corps_resumed": 0,
    }

    tick_start = time.time()

    for corps in corps_list:
        if time.time() - tick_start > 240:
            log_line(log_path, {"timestamp": now_ts(), "event": "tick_timeout", "detail": "max duration reached"})
            break
        corps_id = corps.get("corps_id")
        state_value = corps.get("state", "")
        if not corps_id:
            continue
        if state_value not in ("winter_camps", "on_tour", "unknown"):
            continue

        summary["corps_checked"] += 1
        start = time.time()
        deadline = start + TIMEOUT_S
        failed = False

        def remaining():
            return max(1, int(deadline - time.time()))

        try:
            api_request("POST", f"/api/v1/corps/{corps_id}/command", {"command": "attention"}, timeout=remaining())
            log_line(log_path, {"timestamp": now_ts(), "event": "ten_hut", "corps_id": corps_id, "status": "ok"})
        except Exception as e:
            failed = True
            log_line(log_path, {"timestamp": now_ts(), "event": "ten_hut", "corps_id": corps_id, "status": "failed", "error": str(e)})

        # Detect stalling via last work log entry
        stalled = False
        try:
            work_log = api_request("GET", f"/api/v1/corps/{corps_id}/work-log?limit=1", timeout=remaining()) or []
            if work_log:
                last_ts = work_log[0].get("timestamp")
                if last_ts:
                    last_dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                    if (datetime.now(timezone.utc) - last_dt).total_seconds() > (STALL_MINUTES * 60):
                        stalled = True
            else:
                stalled = True
        except Exception as e:
            stalled = True
            log_line(log_path, {"timestamp": now_ts(), "event": "work_log_check_failed", "corps_id": corps_id, "error": str(e)})

        if stalled:
            summary["corps_stalled"] += 1
            try:
                if time.time() < deadline:
                    api_request("POST", f"/api/v1/corps/{corps_id}/command", {"command": "resume_hut"}, timeout=remaining())
                summary["corps_resumed"] += 1
                log_line(log_path, {"timestamp": now_ts(), "event": "resume_hut", "corps_id": corps_id, "status": "ok"})
            except Exception as e:
                failed = True
                log_line(log_path, {"timestamp": now_ts(), "event": "resume_hut", "corps_id": corps_id, "status": "failed", "error": str(e)})

        elapsed = time.time() - start
        if elapsed > TIMEOUT_S:
            failed = True

        if failed:
            failure_counts[corps_id] = failure_counts.get(corps_id, 0) + 1
        else:
            failure_counts[corps_id] = 0

        if failure_counts.get(corps_id, 0) >= FAILURE_THRESHOLD:
            log_line(ALERT_LOG, {"timestamp": now_ts(), "event": "red_flag", "corps_id": corps_id, "failures": failure_counts[corps_id]})

    summary["agents_active"] = health.get("active_agents") if isinstance(health, dict) else None
    summary["corps_active"] = health.get("active_corps") if isinstance(health, dict) else None
    liveness = {}
    for agent in agents_overview:
        cid = agent.get("corps_id") or "unknown"
        entry = liveness.setdefault(cid, {"count": 0})
        entry["count"] += 1
    summary["agent_liveness"] = liveness
    log_line(log_path, {"timestamp": now_ts(), "event": "tick_summary", **summary})

    state["failure_counts"] = failure_counts
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
