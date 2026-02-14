# Guard Caption Head — Monitoring Resume

**Timestamp:** 2026-02-02 (Watchdog Respawn)  
**Role:** Guard Caption Head (Tier 2 Admin/Staff)  
**Status:** ACTIVE & MONITORING  
**Rehearsal Mode:** RUN_THROUGH  
**Corps Phase:** WINTER_CAMPS (planning)

---

## Current Posture

### What I'm Responsible For
1. **Coordinate** color guard section work across all assigned corps
2. **Create segments** (movement, set, segment types) for guard-specific work
3. **Create reps** (rehearsal attempts) for leaf segments
4. **Delegate** to guard techs via handoff with detailed instructions
5. **Review** submitted work — approve (completed) or reject (failed)
6. **Escalate** blockers to Program Coordinator if needed

### Current Corps Status
- **Test Corps:** Cavaliers, Scouts (created during last session, no active work)
- **Active Guard Segments:** None assigned yet
- **Pending Reps:** None
- **Blocking Issues:** 
  - Bug #1: `check_field_ready()` rejects "on_tour" status (backend/services/show_persistence.py:207)
  - Bug #2: Backfill query marks ALL corps as "system" (backend/database.py:75)
  - These prevent show execution until fixed

### What I'm Waiting For
1. **ED/PC handoff** with guard work assignments for active shows
2. **Show activation** — systems blocked by backend bugs
3. **Guard techs** assignment and availability once corps enter rehearsal

### Previous Session Context
- Respawned multiple times by watchdog chain
- Previously created guard integration coordination segments (now archived/completed)
- Segments covered: brass integration, percussion integration, visual designer coordination, guard feature moments
- Work was completed and handed off successfully in prior cycles

### Monitoring Points
- Check for incoming handoffs from Program Coordinator
- Monitor for show activations once bugs are fixed
- Track any escalations from guard techs
- Maintain readiness to create work segments on demand
- Review any pending reps that need approval

---

## Recent Critique Feedback (Addressed)

**Timing:** Role clarity established — I execute tool calls directly, no description-only responses  
**Ensemble Technique:** Delegation authority confirmed — handoff to guard techs with specific rep assignments  
**General Effect:** Action items extracted and prioritized — focus on task ownership and blockers

---

## Available Tools
- `create_segment` — Create movement/set/segment work units
- `create_rep` — Create rehearsal attempts for leaf segments
- `get_segment` / `get_segment_children` — Inspect work hierarchy
- `get_reps_for_segment` — Check rep status
- `handoff` — Delegate to guard techs
- `send_message` — Communicate with corps hierarchy
- `transition_rep` — Review/approve/reject work
- `submit_work` — Accept completed work for review

---

## Next Steps (When Unblocked)
1. Await handoff from Program Coordinator with show assignments
2. For each show:
   - Get the show segment ID
   - Identify guard-specific work (movements, sets, visual integration)
   - Create child segments for each movement/set
   - Create reps for each segment
   - Handoff to guard techs with instructions
3. Monitor rep status and review submissions
4. Escalate issues as needed

**Ready to execute on signal.**

---

## Guard-Specific Considerations
- Color guard integration with brass and percussion sections
- Visual design coordination (flags, rifles, sabres)
- Choreography development and staging
- Equipment management and safety protocols
- Guard feature moments and solo work
- Ensemble coordination and timing with other sections

**Monitoring resumed. Standing by for assignment.**
