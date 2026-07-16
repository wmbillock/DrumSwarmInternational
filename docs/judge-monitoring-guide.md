# Judge Monitoring Guide — DCI Swarm System Health

As a Timing & Penalties Judge (or other judge role), you have access to comprehensive health monitoring tools to track corps system performance and escalate issues to appropriate personnel.

## Overview

The health monitoring system provides:

1. **Real-time system status** - View current state of all segments and work units
2. **Issue detection** - Automatically identify failed reps, stale work, and blocked segments
3. **Escalation pathways** - Send alerts to Executive Director, Program Coordinator, or Caption Heads
4. **Detailed analytics** - Track work progress through the segment hierarchy

## Quick Start

### 1. Running a Health Check

```bash
# Text format (human-readable)
python -m backend.cli.judge health e3ce0861-3f6e-4411-90db-a366a28a70f8

# JSON format (for integration with other systems)
python -m backend.cli.judge health e3ce0861-3f6e-4411-90db-a366a28a70f8 --json
```

### 2. List All Current Issues

```bash
python -m backend.cli.judge list-issues e3ce0861-3f6e-4411-90db-a366a28a70f8
```

### 3. Escalate a Problem

```bash
python -m backend.cli.judge escalate \
  e3ce0861-3f6e-4411-90db-a366a28a70f8 \
  executive_director \
  "Critical rep failures in percussion section"
```

### 4. Inspect a Specific Segment

```bash
python -m backend.cli.judge segment <segment-id>
```

## Understanding Health Status

### Critical Issues

The system flags issues as **CRITICAL** when:

- A segment's status is **FAILED** - Work cannot proceed through this branch
- A segment is **BLOCKED** - Dependencies not met
- Reps have **FAILED** - Individual work units failed verification
- Reps are **STALE** - No progress for more than 2 hours (configurable)
- A segment has mixed pending/active reps - Potential bottleneck

### Warnings

**WARNING** status indicates:

- Unacknowledged handoff messages (work handed off but not yet acknowledged)
- High volume of pending reps
- Inconsistent rep state transitions

## Key Health Metrics

### Per-Segment Metrics

```
Segment: "Brass Visual Break"
├─ Type: SET
├─ Status: IN_PROGRESS
├─ Children: 3 sub-segments
├─ Reps: 5 total
│  ├─ Failed: 1
│  ├─ Pending: 2
│  └─ Stale: 0
└─ Critical Issues: 1 rep failed
```

### Corps-Level Metrics

```
Corps Health Summary
├─ Total Segments: 47
├─ Total Reps: 156
│  ├─ Failed: 2
│  ├─ Pending: 12
│  └─ Stale: 3
├─ Segments by Status:
│  ├─ Completed: 30
│  ├─ In Progress: 12
│  ├─ Pending: 4
│  └─ Failed: 1
└─ Rehearsal Mode: FULL_ENSEMBLE
```

## Understanding the Segment Hierarchy

The system uses a hierarchical structure to organize work:

```
Show (root)
├─ Movement 1
│  ├─ Set 1
│  │  └─ Segment (leaf node with reps)
│  └─ Set 2
│     └─ Segment
└─ Movement 2
   └─ ...
```

**Rep Status Lifecycle:**

```
PENDING → ASSIGNED → IN_PROGRESS → REVIEW → COMPLETED
                         ↓
                       FAILED
```

- **PENDING**: Rep created, awaiting assignment
- **ASSIGNED**: Rep assigned to a session/tech
- **IN_PROGRESS**: Work is underway
- **REVIEW**: Work submitted, awaiting verification
- **COMPLETED**: Verification passed
- **FAILED**: Work could not be completed

## Escalation Roles

When escalating issues, you can send messages to:

### Executive Director (`executive_director`)
- **Use when**: Major structural issues, fundamental problems with the approach
- **Example**: "Corps is in wrong rehearsal mode for this work"

### Program Coordinator (`program_coordinator`)
- **Use when**: Coordination problems, segment breakdown issues, scheduling conflicts
- **Example**: "Multiple segments stuck pending rep creation"

### Caption Heads (`caption_head_music`, `caption_head_visual`, `caption_head_movement`)
- **Use when**: Section-specific failures, rep-level issues within a caption
- **Example**: "Percussion reps failing verification gates"

### Chief Judge Role
- **Use when**: You need to note timing or execution issues
- **Example**: "Segment progression taking too long (3+ hours)"

## Common Scenarios and Responses

### Scenario 1: Failed Rep Detected

```
[CRITICAL] Brass Visual: 1 rep(s) FAILED
```

**Response:**
1. Run `judge segment <segment-id>` to see which rep failed
2. Check the rep's error message
3. Escalate to appropriate caption head:
   ```bash
   python -m backend.cli.judge escalate <corps-id> caption_head_music \
     "Rep failure in brass visual: verification gate failed" \
     --body "Rep needs to be redone with corrected approach"
   ```

### Scenario 2: Stale Work

```
[CRITICAL] Segment 'Movement 1': 3 rep(s) are STALE (> 2h)
```

**Response:**
1. Identify which reps are stuck
2. Check if they're assigned to a session
3. Escalate to program coordinator if reps are unassigned:
   ```bash
   python -m backend.cli.judge escalate <corps-id> program_coordinator \
     "Stale unassigned reps in movement 1" \
     --body "3 reps have been pending for >2 hours"
   ```

### Scenario 3: Blocked Segment

```
[CRITICAL] Set 2 'Visual Break': Segment is BLOCKED
```

**Response:**
1. Check parent segment status
2. Escalate to program coordinator for dependency resolution
3. Verify that parent's reps are progressing

### Scenario 4: Bottleneck (Mixed Rep States)

```
[CRITICAL] Movement 1: 2 rep(s) still PENDING while others are active
```

**Response:**
1. This indicates uneven progress across reps
2. Escalate to PC for load balancing
3. May need to reassign reps or adjust parallel work

## Using the Health API Programmatically

You can also use the health monitoring system in Python:

```python
from backend.database import create_db_engine, create_session_factory
from backend.services.health_monitor import analyze_corps_health, format_health_report

engine = create_db_engine()
DBSession = create_session_factory(engine)
db = DBSession()

# Run health check
report = analyze_corps_health(db, "e3ce0861-3f6e-4411-90db-a366a28a70f8")

# Print formatted report
print(format_health_report(report))

# Access data programmatically
print(f"Critical issues: {len(report.critical_issues)}")
print(f"Total failed reps: {report.stats['reps_failed']}")
print(f"Total stale reps: {report.stats['reps_stale']}")

# Export as JSON
import json
print(json.dumps(report.to_dict()))
```

## Customization Options

### Adjust Stale Threshold

By default, reps are considered "stale" after 2 hours without update. To customize:

```bash
# Through Python API
from backend.services.health_monitor import analyze_corps_health
report = analyze_corps_health(db, corps_id, stale_threshold_hours=4)
```

### Filter Issues by Segment Type

```python
# Get only SET-level issues
problem_sets = [s for s in report.all_segments
                if s.segment_type == "set" and s.critical_issues]
```

### Export Specific Data

```python
# Export just critical segments
critical_segs = [s.to_dict() for s in report.all_segments
                 if s.critical_issues]
import json
print(json.dumps(critical_segs, indent=2))
```

## Integration with Monitoring Dashboard

The health monitor integrates with the metrics collector:

```bash
# Check if monitoring service is running
curl http://localhost:4224/api/health

# View metrics
curl http://localhost:4224/api/metrics/corps/<corps-id>
```

## Troubleshooting

### Issue: "Corps not found"

```
[CRITICAL] Corps not found in database
```

**Solution**: Verify the corps ID. You can query all active corps from the database directly.

### Issue: "Segment not found"

When running `segment` command, verify the segment ID is correct. Segment IDs are 36-character UUIDs.

### Issue: "No root segment found"

If the health check shows no root segment, the corps may not be properly initialized. Escalate to Executive Director.

### Issue: Stale reps with stale_threshold_hours=2

This is normal during long rehearsals. If expecting longer durations, adjust the threshold or ignore these warnings during intensive sessions.

## Key Takeaways

1. **Regular Checks**: Run health checks every 15-30 minutes during active rehearsal
2. **Quick Response**: Address CRITICAL issues within 5 minutes
3. **Clear Escalations**: Provide specific segment/rep IDs when escalating
4. **Track Patterns**: Look for recurring failures in specific sections/types
5. **Communicate**: Always include relevant context when escalating

## See Also

- System Architecture: `docs/architecture.md`
- Verification Gates: `backend/services/verification.py`
- Message System: `backend/models/message.py`
- Agent Runtime: `backend/services/agent_runtime.py`
