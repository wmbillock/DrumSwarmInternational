# Judge Monitoring System Setup

## Overview

As a Timing & Penalties Judge monitoring corps `e3ce0861-3f6e-4411-90db-a366a28a70f8`, you now have access to comprehensive health monitoring tools.

## What's Been Created

### 1. Health Monitor Service
**Location:** `/Users/mattbillock/Development/dci-swarm/backend/services/health_monitor.py`

Core service that analyzes corps health by:
- Checking root segment status
- Analyzing all segments in the hierarchy
- Identifying failed reps, stale work, and errors
- Detecting critical issues at segment level
- Computing overall health statistics

**Key Functions:**
- `analyze_corps_health(db, corps_id)` - Full corps health check
- `get_segment_health(db, segment_id)` - Individual segment analysis
- `format_health_report(report)` - Human-readable output
- `export_json(report)` - Machine-readable JSON output

### 2. Judge CLI Tool
**Location:** `/Users/mattbillock/Development/dci-swarm/backend/cli/judge.py`

Command-line tool for judges with commands:

```bash
# Check health
python -m backend.cli.judge health <corps-id>
python -m backend.cli.judge health <corps-id> --json

# List all issues
python -m backend.cli.judge list-issues <corps-id>

# Escalate problem
python -m backend.cli.judge escalate <corps-id> <role> <subject> [--body <details>]

# Inspect segment
python -m backend.cli.judge segment <segment-id>
```

### 3. Judge Dashboard Service
**Location:** `/Users/mattbillock/Development/dci-swarm/backend/services/judge_dashboard.py`

Real-time dashboard with:
- Current status snapshot
- Streaming updates
- ASCII art visualization
- JSON export
- Alert aggregation

**Key Functions:**
- `create_judge_dashboard(db, corps_id)` - Create dashboard instance
- `dashboard.get_current_status()` - Status snapshot
- `dashboard.stream_updates()` - Continuous monitoring
- `dashboard.get_ascii_dashboard()` - Terminal visualization

### 4. Comprehensive Documentation
**Location:** `/Users/mattbillock/Development/dci-swarm/docs/judge-monitoring-guide.md`

Full guide covering:
- Quick start instructions
- Understanding health metrics
- Segment hierarchy explained
- Rep lifecycle states
- Escalation procedures
- Common scenarios and responses
- Programmatic API usage
- Troubleshooting

### 5. Example Workflows
**Location:** `/Users/mattbillock/Development/dci-swarm/examples/judge_monitoring_example.py`

Six complete examples:
1. Basic health check
2. Problem identification
3. Issue escalation
4. Dashboard visualization
5. Detailed segment analysis
6. Comparative monitoring over time

## Quick Start

### Option 1: Using the CLI Tool (Recommended)

```bash
# Run health check
python -m backend.cli.judge health e3ce0861-3f6e-4411-90db-a366a28a70f8

# View summary of issues
python -m backend.cli.judge list-issues e3ce0861-3f6e-4411-90db-a366a28a70f8

# Escalate a critical issue
python -m backend.cli.judge escalate e3ce0861-3f6e-4411-90db-a366a28a70f8 \
  program_coordinator \
  "Stale reps in percussion section"
```

### Option 2: Python API (For Integration)

```python
from backend.database import create_db_engine, create_session_factory
from backend.services.health_monitor import analyze_corps_health, format_health_report
from backend.services.judge_dashboard import create_judge_dashboard

engine = create_db_engine()
DBSession = create_session_factory(engine)
db = DBSession()

# Health check
report = analyze_corps_health(db, "e3ce0861-3f6e-4411-90db-a366a28a70f8")
print(format_health_report(report))

# Dashboard
dashboard = create_judge_dashboard(db, "e3ce0861-3f6e-4411-90db-a366a28a70f8")
print(dashboard.get_ascii_dashboard())

# JSON export
import json
print(json.dumps(report.to_dict(), indent=2))

db.close()
```

### Option 3: Run Examples

```bash
cd /Users/mattbillock/Development/dci-swarm
python examples/judge_monitoring_example.py
```

## Key Metrics Explained

### Segment Status
- **PENDING** - Not yet started
- **IN_PROGRESS** - Active work
- **REVIEW** - Awaiting verification
- **COMPLETED** - Successfully finished
- **FAILED** - Work failed verification
- **BLOCKED** - Dependency issue

### Rep Status
- **PENDING** - Awaiting assignment
- **ASSIGNED** - Assigned to tech/session
- **IN_PROGRESS** - Work underway
- **REVIEW** - Submitted for verification
- **COMPLETED** - Passed verification
- **FAILED** - Failed verification

### Critical Issues Detected
- Failed segments or reps
- Blocked work (dependency issues)
- Stale reps (no progress for >2 hours)
- Bottlenecks (mixed pending/active state)
- Unacknowledged handoffs (stuck messages)

## Escalation Roles

When you identify an issue and need to escalate:

| Role | Use When | Example |
|------|----------|---------|
| `executive_director` | Major structural issues | Wrong rehearsal mode, fundamental approach problem |
| `program_coordinator` | Coordination problems | Segment breakdown stuck, scheduling conflict |
| `caption_head_music` | Music section failures | Brass/woodwind reps failing |
| `caption_head_visual` | Visual section failures | Guard/visual reps failing |
| `caption_head_movement` | Movement section failures | Movement reps failing |

## System Architecture

```
Corps (e3ce0861-3f6e-4411-90db-a366a28a70f8)
├── Show (root segment)
│   ├── Movement 1
│   │   ├── Set 1
│   │   │   ├── Segment (with reps)
│   │   │   └── Segment (with reps)
│   │   └── Set 2
│   │       └── Segment (with reps)
│   └── Movement 2
│       └── ...
├── Agent Sessions (ED, PC, Caption Heads)
├── Messages (escalations, handoffs)
└── Reps (individual work units)
```

Each segment can have:
- Status (pending, in_progress, review, completed, failed, blocked)
- Multiple reps (work units being attempted)
- Child segments (hierarchical breakdown)

## Monitoring Workflow

1. **Check health every 15-30 minutes**
   ```bash
   python -m backend.cli.judge health <corps-id>
   ```

2. **Review critical issues**
   ```bash
   python -m backend.cli.judge list-issues <corps-id>
   ```

3. **Inspect problematic segments**
   ```bash
   python -m backend.cli.judge segment <segment-id>
   ```

4. **Escalate if needed**
   ```bash
   python -m backend.cli.judge escalate <corps-id> <role> "<issue>"
   ```

5. **Monitor resolution**
   - Re-run health check in 5-10 minutes
   - Track if issue is resolved
   - Escalate further if necessary

## Customization

### Adjust Stale Threshold

By default, reps are "stale" after 2 hours. To change:

```python
# In Python code:
report = analyze_corps_health(db, corps_id, stale_threshold_hours=4)

# In CLI (future enhancement):
python -m backend.cli.judge health <corps-id> --stale-threshold 4
```

### Monitor Specific Segments

```python
from backend.services.segment_service import get_children
from backend.services.health_monitor import get_segment_health

children = get_children(db, parent_id)
for child in children:
    health = get_segment_health(db, child.id)
    if health.critical_issues:
        print(f"Problem in {child.title}: {health.critical_issues}")
```

### Export for External Systems

```python
import json
report = analyze_corps_health(db, corps_id)

# Export to JSON for external dashboards
with open("corps_health.json", "w") as f:
    json.dump(report.to_dict(), f, indent=2)

# Send to monitoring service
import requests
requests.post("http://monitoring-service/health", json=report.to_dict())
```

## Troubleshooting

### "Corps not found"
- Verify corps ID is correct
- Check database is initialized and populated

### No issues detected but system seems slow
- Increase monitoring frequency
- Check for patterns in pending reps
- Look for unacknowledged messages

### Messages not being escalated
- Verify target role exists (check `backend/models/agent_definition.py`)
- Check if agents are active (should be spawned automatically)
- Review message logs in database

## Advanced Usage

### Real-time Monitoring Loop

```python
from backend.services.judge_dashboard import create_judge_dashboard
import time

dashboard = create_judge_dashboard(db, corps_id)

# Stream updates continuously
for status in dashboard.stream_updates(max_updates=12):  # 12 updates
    print(dashboard.get_ascii_dashboard())
    print(f"Critical issues: {status['critical_count']}")
    print(f"Warnings: {status['warning_count']}")
    time.sleep(30)  # Check every 30 seconds
```

### Alert on Threshold

```python
report = analyze_corps_health(db, corps_id)

if report.stats['reps_failed'] > 5:
    escalate_issue(corps_id, "executive_director",
                   f"High failure rate: {report.stats['reps_failed']} reps failed")

if report.stats['reps_stale'] > 10:
    escalate_issue(corps_id, "program_coordinator",
                   f"High stale count: {report.stats['reps_stale']} reps stale")
```

### Segment Type Analysis

```python
# Find all problematic SETs
problem_sets = [s for s in report.all_segments
                if s.segment_type == "set" and s.critical_issues]

# Find longest-stale reps
stale_reps = []
for seg in report.all_segments:
    stale_reps.extend(seg.stale_reps)
stale_reps.sort(key=lambda x: x['age_hours'], reverse=True)
```

## Files Reference

| File | Purpose |
|------|---------|
| `backend/services/health_monitor.py` | Core health analysis |
| `backend/services/judge_dashboard.py` | Real-time dashboard |
| `backend/cli/judge.py` | Judge CLI tool |
| `docs/judge-monitoring-guide.md` | Full documentation |
| `examples/judge_monitoring_example.py` | Example workflows |
| `JUDGE_MONITORING_SETUP.md` | This file |

## Next Steps

1. **Read the guide:** `docs/judge-monitoring-guide.md`
2. **Run examples:** `python examples/judge_monitoring_example.py`
3. **Start monitoring:** `python -m backend.cli.judge health <corps-id>`
4. **Integrate dashboards:** Use `judge_dashboard.py` in monitoring web UI

## Support

For questions about:
- **Health metrics**: See `backend/services/health_monitor.py` docstrings
- **CLI usage**: Run `python -m backend.cli.judge --help`
- **API integration**: See `examples/judge_monitoring_example.py`
- **System architecture**: See `docs/architecture.md`

---

**Created:** 2026-01-31
**For:** Timing & Penalties Judge monitoring corps `e3ce0861-3f6e-4411-90db-a366a28a70f8`
**Available Tools:** CLI tool, Python API, Real-time dashboard, Comprehensive documentation
