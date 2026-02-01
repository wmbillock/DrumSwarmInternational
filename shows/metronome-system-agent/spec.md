Perfect! The spec has been successfully updated with all required sections and design conversation details. Here's a summary of what was added:

## Summary of Updates

**Version bumped to 2** and spec now includes:

### ✅ **All Required Sections**
1. **Show Concept** — Clear purpose: autonomous heartbeat for the DCI swarm
2. **Musical Design** — Three movements organized by captions:
   - **Percussion** (timing/rhythm) — cron script, lock file, tick sequence
   - **Brass** (command & signal) — ten-hut/resume-hut with precise definitions
   - **Visual** (observation & display) — status gathering and summary format
3. **Guard Design** — Error handling, resilience, idempotency, isolation
4. **General Effect** — Behavioral outcomes and detailed acceptance criteria (5 checkboxes)
5. **Deliverables** — Code modules, logging structure, documentation requirements
6. **Evaluation Rubric** — Four scoring dimensions (Functionality 50%, Code 25%, Operational 15%, Devil's Advocate 10%) with explicit pass threshold (≥78/100)

### ✅ **Devil's Advocate Proofing**
- **Concrete specifications**: Lock file path (`/tmp/metronome.lock`), timeout (30 sec per corps, 4 min total), stalled definition (>5 min no activity)
- **Testable acceptance criteria**: 5 checkbox sections with objective, verifiable requirements
- **Edge cases explicit**: Concurrent ticks, stale locks, unreachable corps, partial failures, timeouts, idempotency
- **Thresholds defined**: N=3 consecutive tick failures before alert, 300-second lock timeout, daily log rotation

### ✅ **All Design Decisions Incorporated**
- Cron interval: 5 minutes ✓
- Wake targets: ED/PC/caption heads/logistics (NOT performers) ✓
- Stalled detection: >5 min pending with no agent activity ✓
- System-level daemon (outside any corps) ✓
- Stateless per tick with lock file concurrency ✓
- Structured logging with alerts ✓

The spec is now **testable, unambiguous, and ready for implementation**.