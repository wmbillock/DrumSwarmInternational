# Judge Monitoring — Quick Reference Card

## Your Corps ID
```
e3ce0861-3f6e-4411-90db-a366a28a70f8
```

## Most Common Commands

### 1. Check System Health
```bash
python -m backend.cli.judge health e3ce0861-3f6e-4411-90db-a366a28a70f8
```
**Use:** Every 15-30 minutes during rehearsal

### 2. See All Issues
```bash
python -m backend.cli.judge list-issues e3ce0861-3f6e-4411-90db-a366a28a70f8
```
**Use:** When you see warning/critical count in health check

### 3. Escalate to Program Coordinator
```bash
python -m backend.cli.judge escalate e3ce0861-3f6e-4411-90db-a366a28a70f8 \
  program_coordinator \
  "Issue summary here"
```
**Use For:** Coordination problems, stuck segments, scheduling issues

### 4. Escalate to Executive Director
```bash
python -m backend.cli.judge escalate e3ce0861-3f6e-4411-90db-a366a28a70f8 \
  executive_director \
  "Critical issue description"
```
**Use For:** Major problems, structural issues, rehearsal mode problems

### 5. Escalate to Caption Head
```bash
python -m backend.cli.judge escalate e3ce0861-3f6e-4411-90db-a366a28a70f8 \
  caption_head_music \
  "Brass section reps failing"
```
**Use For:** Section-specific failures (music, visual, movement)

### 6. Inspect a Segment
```bash
python -m backend.cli.judge segment <segment-id>
```
**Use:** When you see a segment with issues in health check

### 7. Get JSON Data
```bash
python -m backend.cli.judge health e3ce0861-3f6e-4411-90db-a366a28a70f8 --json
```
**Use:** For integration with dashboards or analysis tools

## Health Status Indicators

| Status | Meaning | Action |
|--------|---------|--------|
| **CRITICAL** | System problem | Escalate immediately (5 min) |
| **WARNING** | Potential issue | Monitor closely, escalate if worsens |
| **OK** | System healthy | Continue normal monitoring |

## What to Escalate

| Issue | Escalate To |
|-------|-------------|
| Failed reps in section | Caption head for that section |
| Multiple stuck segments | Program coordinator |
| Rehearsal mode problem | Executive director |
| Unacknowledged messages | Program coordinator |
| System-wide failures | Executive director |

## Key Metrics

```
Total Segments  → How much work is defined
Total Reps      → How many work attempts
Failed Reps     → How many failed verification
Pending Reps    → How many waiting to start
Stale Reps      → How many haven't progressed (>2h)
```

### Healthy Ranges
- **Failed**: 0-2 (occasional, expected)
- **Pending**: Should decrease over time
- **Stale**: 0 (indicates bottleneck if >0)
- **In Progress**: Should increase as work starts

## Escalation Template

```bash
python -m backend.cli.judge escalate e3ce0861-3f6e-4411-90db-a366a28a70f8 \
  <ROLE> \
  "<ISSUE_TITLE>" \
  --body "Details about the issue and what action is needed"
```

### Example:
```bash
python -m backend.cli.judge escalate e3ce0861-3f6e-4411-90db-a366a28a70f8 \
  program_coordinator \
  "3 reps stale in percussion set" \
  --body "Movement 1 Set 2 has 3 reps pending for >2 hours. Check assignment status."
```

## Red Flags (Escalate Immediately)

- [ ] Any CRITICAL issues shown
- [ ] Segment status is FAILED
- [ ] Segment is BLOCKED
- [ ] >3 failed reps
- [ ] >5 stale reps
- [ ] Unacknowledged handoff messages
- [ ] Corps status changed to DISBANDED

## Green Flags (System is Healthy)

- [ ] No critical issues
- [ ] Most segments in progress or completed
- [ ] Failed reps ≤2
- [ ] No stale reps
- [ ] Pending reps decreasing over time
- [ ] Messages being acknowledged promptly

## Typical Monitoring Schedule

| Time | Action |
|------|--------|
| Start | Run health check, note baseline |
| Every 15 min | Quick `list-issues` check |
| Every 30 min | Full health check |
| On issue | Drill down with `segment` command |
| As needed | Escalate to appropriate role |

## Roles & Escalation Paths

```
You (Judge)
    ↓
Executive Director (major issues)
Program Coordinator (coordination)
├─ Caption Head Music
├─ Caption Head Visual
└─ Caption Head Movement
```

## Database Locations

| Info | File |
|------|------|
| Database | `/Users/mattbillock/Development/dci-swarm/dci_swarm.db` |
| Health monitor code | `backend/services/health_monitor.py` |
| Judge CLI code | `backend/cli/judge.py` |
| Dashboard code | `backend/services/judge_dashboard.py` |
| Full guide | `docs/judge-monitoring-guide.md` |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Corps not found" | Check corps ID is exactly correct |
| No issues showing but slow progress | Increase monitoring frequency |
| Messages not working | Verify role names match exactly |
| Can't find segment | Copy segment ID from health check output |

## Available Tools

| Tool | Command | Purpose |
|------|---------|---------|
| Health Monitor | `judge health` | Check overall system |
| Issue Lister | `judge list-issues` | See all problems |
| Escalator | `judge escalate` | Send alerts to roles |
| Segment Inspector | `judge segment` | Drill down on one segment |
| Dashboard | `judge_dashboard.py` (Python API) | Real-time visualization |

## Remember

1. **Check regularly** - 15-30 min intervals during rehearsal
2. **Act on critical issues** - Within 5 minutes if possible
3. **Be specific** - Include segment/rep IDs when escalating
4. **Track patterns** - Note if same areas keep failing
5. **Communicate clearly** - Descriptions help roles respond faster

---

**Your Role:** Monitor system health and escalate issues to appropriate roles
**Your Tools:** CLI commands, dashboard, health reports
**Your Responsibility:** Ensure work is progressing without critical blockers
