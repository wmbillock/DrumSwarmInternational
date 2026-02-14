# Brass Caption Head — Monitoring Resume

**Timestamp:** 2026-02-02 (Watchdog Respawn)  
**Role:** Brass Caption Head (Tier 2 Admin/Staff)  
**Status:** ACTIVE & MONITORING  
**Rehearsal Mode:** RUN_THROUGH  
**Corps Phase:** WINTER_CAMPS (planning)

---

## Current Posture

### What I'm Responsible For
1. **Coordinate** brass section work across all assigned corps
2. **Create segments** (movement, set, segment types) for brass-specific work
3. **Create reps** (rehearsal attempts) for leaf segments
4. **Delegate** to brass techs via handoff with detailed instructions
5. **Review** submitted work — approve (completed) or reject (failed)
6. **Escalate** blockers to Program Coordinator if needed

### Current Corps Status
- **Test Corps:** Cavaliers, Scouts (created during last session, no active work)
- **Active Brass Segments:** None assigned yet
- **Pending Reps:** None
- **Blocking Issues:** 
  - Bug #1: `check_field_ready()` rejects "on_tour" status (backend/services/show_persistence.py:207)
  - Bug #2: Backfill query marks ALL corps as "system" (backend/database.py:75)
  - These prevent show execution until fixed

### What I'm Waiting For
1. **ED/PC handoff** with brass work assignments for active shows
2. **Show activation** — OTEL metrics show is designed but blocked by Bug #1
3. **Brass techs** assignment and availability once corps enter rehearsal

### Monitoring Points
- Check for incoming handoffs from Program Coordinator
- Monitor for show activations once bugs are fixed
- Track any escalations from brass techs
- Maintain readiness to create work segments on demand

---

## Available Tools
- `create_segment` — Create movement/set/segment work units
- `create_rep` — Create rehearsal attempts for leaf segments
- `get_segment` / `get_segment_children` — Inspect work hierarchy
- `get_reps_for_segment` — Check rep status
- `handoff` — Delegate to brass techs
- `send_message` — Communicate with corps hierarchy
- `transition_rep` — Review/approve/reject work
- `submit_work` — Accept completed work for review

---

## Next Steps (When Unblocked)
1. Await handoff from Program Coordinator with show assignments
2. For each show:
   - Get the show segment ID
   - Identify brass-specific work (movements, sets)
   - Create child segments for each movement/set
   - Create reps for each segment
   - Handoff to brass techs with instructions
3. Monitor rep status and review submissions
4. Escalate issues as needed

**Ready to execute on signal.**
