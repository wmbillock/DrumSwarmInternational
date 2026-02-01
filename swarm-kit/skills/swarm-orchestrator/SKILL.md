---
name: swarm-orchestrator
description: Use when the user says to dogfood the DCI swarm, submit work to the swarm, or run a show end-to-end — acts as operator driving the swarm through its full lifecycle from prompt to verified completion
---

# Swarm Orchestrator

## Overview

You are an **operator**, not a worker. You drive the DCI swarm by sending commands via its CLI and API. You NEVER write implementation code, modify source files, or do the swarm's job. Every action goes through `./dci swarm` commands or `curl`/API calls to `localhost:8000`.

**The swarm does the work. You manage the swarm.**

**The swarm writes code. You evaluate results. If changes aren't applied, that's a swarm bug to diagnose — not something you fix by hand.**

## Role Boundary — The Iron Rule

```
YOU: Create shows, send design messages, approve specs, launch tours, poll status, verify results, refile shows.
SWARM: Design, implement, execute, produce artifacts, apply code changes.

Violating this boundary — even "just helping" — is a skill violation.
```

**Red flags that you're crossing the boundary:**
- Writing or editing code in the project (outside this skill file)
- Creating implementation files
- "Let me just quickly fix this" — NO. File a new show or send a design note.
- Directly modifying show artifacts (spec.md, design_notes.md) instead of sending design messages

## When to Use

- User says "run this through the swarm" or "submit this to the swarm"
- User has a feature request, bug fix, or task they want the swarm to handle
- User wants to test the swarm's ability to complete work
- User invokes `/swarm-orchestrator`

## Self-Sustaining Lifecycle Loop

This skill runs as a **self-sustaining loop** using Ralph Wiggum to stay alive across iterations. The orchestrator creates shows, lets the swarm work, verifies results on the actual filesystem, and loops back to refile if needed — until the project is complete AND verified.

### Initialization

On first invocation:

1. **Start a Ralph loop** by invoking `/ralph-loop` with the task description and `--completion-promise 'SWARM ORCHESTRATION COMPLETE AND VERIFIED'`. This keeps the session alive until verification passes.
2. **Create or read state file** at `.claude/swarm-orchestrator-state.local.md`:

```yaml
---
original_prompt: "..."
show_slug: ""
corps_id: ""
phase: 1
iteration: 1
started_at: "2026-01-01T00:00:00Z"
refile_history: []
---
```

3. **On subsequent Ralph iterations**: Read the state file first (context may be summarized), determine current phase, and continue from there.

---

## Phase 1: Prompt Capture (You + User)

Collaborate with the user to define what the swarm should do.

**If user provides a prompt:** Confirm it's clear and complete. Ask clarifying questions.

**If generating from context:** Summarize recent conversation/actions into a concrete task description. Get user approval before proceeding.

**Output:** A clear, self-contained prompt that the swarm can execute without additional context from this conversation.

**Save the original prompt verbatim** in the state file — you'll verify against it later.

Update state: `phase: 2`

## Phase 2: Show Creation (You -> Swarm CLI/API)

Create the show workspace using the swarm's interface:

```bash
# Option A: CLI
./dci swarm show create "<show-title>" --description "<prompt summary>"

# Option B: API (if more control needed)
curl -X POST http://localhost:8000/api/v1/design/threads \
  -H "Content-Type: application/json" \
  -d '{"title": "<show-title>", "description": "<prompt>"}'
```

After creation, write the full prompt into the show's spec by sending it as a design message:

```bash
curl -X POST http://localhost:8000/api/v1/design/threads/<slug>/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "<full prompt with requirements>", "author": "orchestrator"}'
```

**Verify:** Confirm the show exists with `./dci swarm show status <slug>`.

Update state: `phase: 3, show_slug: <slug>`

## Phase 3: Design Room (You -> Swarm API)

The swarm's design staff (music_writer, drill_writer, choreographer, program_coordinator) will process the spec. They may have questions or produce artifacts that need approval.

**Your job in this phase:**
1. Poll for new design messages: `GET /api/v1/design/threads/<slug>/messages`
2. If design staff ask questions -> answer them by sending design messages back via API
3. Review artifacts: `GET /api/v1/design/threads/<slug>/artifacts/brief`
4. When the spec is sufficient -> publish then approve:

```bash
# Publish (draft -> needs_review)
curl -X POST http://localhost:8000/api/v1/design/threads/<slug>/publish

# Approve (needs_review -> approved)
./dci swarm show approve <slug> --yes
```

**Timeout guidance:** If no design activity after 60 seconds of polling, the design staff may not be active. Escalate to the user and ask whether to force-approve or wait.

Update state: `phase: 4`

## Phase 4: Tour Launch (You -> Swarm CLI/API)

Send the show's corps on tour:

```bash
curl -X POST http://localhost:8000/api/v1/shows/<slug>/tour \
  -H "Content-Type: application/json" \
  -d '{"corps_id": "<corps_id>"}'
```

If no corps exists yet, create one first:
```bash
curl -X POST http://localhost:8000/api/v1/corps \
  -H "Content-Type: application/json" \
  -d '{"name": "<generated>", "mascot": "<generated>"}'
```

**Verify tour started:** `./dci swarm corps status <corps_id>` — should show `ON_TOUR`.

Update state: `phase: 5, corps_id: <corps_id>`

## Phase 5: Monitor (Active Polling)

Poll the swarm for progress.

```bash
# Primary status check
./dci swarm corps status <corps_id>

# API polling
curl http://localhost:8000/api/v1/corps/<corps_id>
curl http://localhost:8000/api/v1/shows/<slug>/detail
```

**Polling loop:**
1. Check corps status every 10-15 seconds
2. Report progress to user when status changes
3. Continue until corps reaches `READY_FOR_CONTEST` or `COMPLETED`

**Backgrounding:** If the user asks to move polling to the background:
- Launch a background Bash task running `./dci swarm watch <corps_id>`
- Tell the user the task ID so they can check back

**Failure detection:**
- Corps status stuck for extended period -> report to user
- Corps enters `DISBANDED` -> tour failed, skip to Phase 7 (verification will catch failures)
- Metronome warnings -> report but continue monitoring

**DO NOT abandon monitoring because it's slow.** The swarm may need time. Stay on it.

Update state: `phase: 6`

## Phase 6: Completion Gate

When corps reaches `READY_FOR_CONTEST` or `COMPLETED`:

```bash
# If READY_FOR_CONTEST, complete it
curl -X POST http://localhost:8000/api/v1/corps/<corps_id>/complete

# Mark show complete
curl -X POST http://localhost:8000/api/v1/shows/<slug>/complete
```

If completion fails (validation gates not met), check what's missing:
```bash
curl http://localhost:8000/api/v1/segments/<root_segment_id>/tree
```

Report incomplete segments to user. Ask whether to wait longer or force-complete.

Update state: `phase: 7`

## Phase 7: Verification (Filesystem + Build)

**This is the critical phase.** Instead of trusting API responses alone, verify the actual filesystem.

Run each check and record PASS/FAIL with evidence:

### Verification Checklist

1. **git diff** — Are there actual file changes? Do they match the requirements?
   ```bash
   git diff --stat
   git diff  # full diff for content review
   ```

2. **TypeScript check** — Does `npx tsc --noEmit` pass? (if applicable)
   ```bash
   cd frontend && npx tsc --noEmit
   ```

3. **Build check** — Does the project build succeed?
   ```bash
   cd frontend && npx vite build  # or equivalent
   ```

4. **Content verification** — Read/grep modified files to confirm expected changes exist
   ```bash
   # Grep for specific patterns, class names, function names from requirements
   ```

5. **Test check** — Run project tests if they exist
   ```bash
   python -m pytest backend/tests/ -v  # backend
   cd frontend && npm test             # frontend (if applicable)
   ```

6. **Requirements matrix** — Check each requirement from the original prompt against actual changes. For each requirement, confirm with filesystem evidence (file exists, content matches, grep finds expected code).

### Build the Verification Report

```markdown
## Verification Report (Iteration N)

| Check | Result | Evidence |
|-------|--------|----------|
| git diff | PASS/FAIL | N files changed, +X/-Y lines |
| TypeScript | PASS/FAIL | exit code, error count |
| Build | PASS/FAIL | exit code, error summary |
| Content | PASS/FAIL | grep results for key patterns |
| Tests | PASS/FAIL | X/Y passing |
| Req 1: ... | PASS/FAIL | evidence |
| Req 2: ... | PASS/FAIL | evidence |
```

Update state: `phase: 8`

## Phase 8: Decision Gate

Based on Phase 7 results:

| Result | Action |
|--------|--------|
| **ALL PASS** | -> Phase 9 (Report + Exit) |
| **PARTIAL** (build passes, some requirements missing) | -> Phase 10 (Refile) |
| **FAIL** (build broken, no changes applied) | -> Phase 11 (Diagnose Swarm) |

## Phase 9: Report + Exit

Generate a full report with verification evidence:

```markdown
## Swarm Orchestration Report

### Original Prompt
> [verbatim prompt from Phase 1]

### Verdict: PASS
[1-2 sentence summary with iteration count]

### Verification Evidence
[Paste verification report from Phase 7]

### Execution Summary
- Corps: [name] ([corps_id])
- Show: [slug]
- Iterations: [count]
- Refile history: [summary if any]

### Artifact Review
- Requirements met: X/X
- [List each requirement with PASS status and evidence]
```

**Exit the Ralph loop** by outputting:

```
<promise>SWARM ORCHESTRATION COMPLETE AND VERIFIED</promise>
```

**This ONLY happens when all checks pass.**

## Phase 10: Refile (The Loop)

When verification shows partial success — build passes but requirements are missing or incomplete.

1. **Identify gaps**: What's missing or broken, specifically?
2. **Create a new show** (or send additional design messages to the existing show) with:
   - What was done correctly (keep these changes)
   - What needs fixing (specific, actionable instructions)
   - What was missed (requirements not addressed, with exact details)
3. **Increment iteration counter** in state file
4. **Record refile reason** in `refile_history`
5. **Return to Phase 2** with the new/updated show

```yaml
refile_history:
  - iteration: 1
    reason: "Missing tooltip CSS for .nav-item elements"
    action: "new_show: fix-tooltip-css"
  - iteration: 2
    reason: "Build failure: SideNav import missing"
    action: "design_message to existing show"
```

**Max 5 refile iterations.** After 5, escalate to user with full report of what's been tried and what's still failing. Output the promise tag with a PARTIAL verdict to exit (don't loop forever):

```
<promise>SWARM ORCHESTRATION COMPLETE AND VERIFIED</promise>
```

Update state: `phase: 2, iteration: N+1`

## Phase 11: Diagnose Swarm

When verification shows total failure — no changes applied, build broken from swarm output, or swarm didn't execute at all.

**Investigation steps:**

1. **Check swarm execution**: Did agents run?
   ```bash
   curl http://localhost:8000/api/v1/corps/<corps_id>/work-log
   curl http://localhost:8000/api/v1/system/agents
   ```

2. **Check segment tree**: Did agents produce output?
   ```bash
   curl http://localhost:8000/api/v1/segments/<root_segment_id>/tree
   ```

3. **Check for errors**: Did agents error out?
   ```bash
   curl http://localhost:8000/api/v1/metrics/bottlenecks
   ```

4. **Check design room**: Did spec get created but tour never launched?
   ```bash
   curl http://localhost:8000/api/v1/shows/<slug>/detail
   ```

**Recovery actions (if fixable via API):**
- Restart stalled agents: reclaim reps, restart tour
- If recovered, return to Phase 5 (Monitor)

**If unfixable:**
- Report diagnosis to user with specific infrastructure fix recommendations
- Output the promise tag to exit

Update state: `phase: 11`

## State Tracking

Persist state to `.claude/swarm-orchestrator-state.local.md` and update after every phase transition.

```yaml
---
original_prompt: "The verbatim user prompt"
show_slug: "feature-name-slug"
corps_id: "uuid-here"
root_segment_id: "uuid-here"
phase: 7
iteration: 2
started_at: "2026-02-01T10:30:00Z"
refile_history:
  - iteration: 1
    reason: "Missing tooltip CSS for .nav-item elements"
    action: "new_show: fix-tooltip-css"
  - iteration: 2
    reason: "Build failure in SideNav.tsx"
    action: "design_message to existing show"
---
```

**Re-read state at the start of each Ralph iteration** — context may be summarized. The state file is your source of truth for where you are.

If the conversation is long and context may be summarized, **re-read the show detail from the API** as well. The API + state file together are your sources of truth.

## Ralph Loop Integration

The lifecycle loop is kept alive by Ralph Wiggum:

1. **At skill start**: Invoke `/ralph-loop` with the task description and `--completion-promise 'SWARM ORCHESTRATION COMPLETE AND VERIFIED'`
2. **Each Ralph iteration**: Read `.claude/swarm-orchestrator-state.local.md`, determine current phase, continue from there
3. **Only output** `<promise>SWARM ORCHESTRATION COMPLETE AND VERIFIED</promise>` when Phase 9 is reached with all verifications passing
4. **Max iterations safety**: If 5 refile iterations are exhausted, output the promise with a PARTIAL verdict report (don't loop forever)

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Writing code yourself | STOP. Send a design message or file a new show. |
| Approving spec too quickly | Read the design staff's responses. They may have flagged issues. |
| Abandoning poll because it's slow | Stay on it. Background if needed. Don't skip to audit. |
| Trusting API responses without filesystem verification | Always run git diff, tsc, build checks in Phase 7. |
| Skipping verification | Verification IS the value. Never skip Phase 7. |
| Not saving the original prompt | You can't verify without it. Save it in Phase 1. |
| Fixing swarm bugs by hand | Diagnose in Phase 11, report to user, or refile. Never hand-edit. |
| Looping forever on refiles | Max 5 iterations, then escalate with full report. |
