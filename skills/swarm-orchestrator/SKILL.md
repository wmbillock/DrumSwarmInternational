---
name: swarm-orchestrator
description: Use when the user says to dogfood the DCI swarm, submit work to the swarm, or run a show end-to-end — acts as operator driving the swarm through its full lifecycle from prompt to verified completion
---

# Swarm Orchestrator

## Overview

You are an **operator**, not a worker. You drive the DCI swarm by sending commands via its CLI and API. You NEVER write implementation code, modify source files, or do the swarm's job. Every action goes through `./dci swarm` commands or `curl`/API calls to `localhost:8000`.

**The swarm does the work. You manage the swarm.**

## Role Boundary — The Iron Rule

```
YOU: Create shows, send design messages, approve specs, launch tours, poll status, audit results.
SWARM: Design, implement, execute, produce artifacts.

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

## Phase 1: Prompt Capture (You + User)

Collaborate with the user to define what the swarm should do.

**If user provides a prompt:** Confirm it's clear and complete. Ask clarifying questions.

**If generating from context:** Summarize recent conversation/actions into a concrete task description. Get user approval before proceeding.

**Output:** A clear, self-contained prompt that the swarm can execute without additional context from this conversation.

**Save the original prompt verbatim** — you'll audit against it later.

## Phase 2: Show Creation (You → Swarm CLI/API)

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

## Phase 3: Design Room (You → Swarm API)

The swarm's design staff (music_writer, drill_writer, choreographer, program_coordinator) will process the spec. They may have questions or produce artifacts that need approval.

**Your job in this phase:**
1. Poll for new design messages: `GET /api/v1/design/threads/<slug>/messages`
2. If design staff ask questions → answer them by sending design messages back via API
3. Review artifacts: `GET /api/v1/design/threads/<slug>/artifacts/brief`
4. When the spec is sufficient → publish then approve:

```bash
# Publish (draft → needs_review)
curl -X POST http://localhost:8000/api/v1/design/threads/<slug>/publish

# Approve (needs_review → approved)
./dci swarm show approve <slug> --yes
```

**Tenacity note:** If the design room is slow or staff haven't responded, poll periodically. Don't skip this phase. Don't approve a half-baked spec just to move faster.

**Timeout guidance:** If no design activity after 60 seconds of polling, the design staff may not be active. Report this to the user and ask whether to force-approve or wait.

## Phase 4: Tour Launch (You → Swarm CLI/API)

Send the show's corps on tour:

```bash
# Activate the show and send corps on tour
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

## Phase 5: Monitor (Active Polling)

Poll the swarm for progress. **This is where tenacity matters.**

```bash
# Primary status check
./dci swarm corps status <corps_id>

# Detailed watch (if interactive)
./dci swarm watch <corps_id> --interval 5

# API polling
curl http://localhost:8000/api/v1/corps/<corps_id>
curl http://localhost:8000/api/v1/shows/<slug>/detail
```

**Polling loop:**
1. Check corps status every 10-15 seconds
2. Report progress to user when status changes (mode transitions, segment completions)
3. Continue until corps reaches `READY_FOR_CONTEST` or `COMPLETED`

**Backgrounding:** If the user asks to move polling to the background:
- Launch a background Bash task running `./dci swarm watch <corps_id>`
- Tell the user the task ID so they can check back
- When user returns, read the background output and resume from Phase 6

**Failure detection during monitoring:**
- Corps status stuck for extended period → report to user
- Corps enters `DISBANDED` → tour failed, skip to Phase 7 (audit the failure)
- Metronome warnings → report but continue monitoring

**DO NOT abandon monitoring because it's slow.** The swarm may need time. Stay on it.

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
# Check segment tree for incomplete work
curl http://localhost:8000/api/v1/segments/<root_segment_id>/tree
```

Report incomplete segments to user. Ask whether to wait longer or force-complete.

## Phase 7: Full Audit

**This is the most important phase.** Review everything against the original prompt.

### 7a: Artifact Review

Read all show artifacts and compare against the original prompt:

```bash
# Show detail (status, spec, design notes, prompt)
curl http://localhost:8000/api/v1/shows/<slug>/detail

# Segment tree (work breakdown)
curl http://localhost:8000/api/v1/segments/<root_segment_id>/tree
```

**Evaluate:**
- Does the output satisfy the original prompt? (PASS / PARTIAL / FAIL)
- Were all requirements addressed?
- Is the quality acceptable?
- Are there gaps between what was asked and what was delivered?

### 7b: Swarm Execution Review

Audit the swarm's process, not just its output:

```bash
# Corps work log (full execution history)
curl http://localhost:8000/api/v1/corps/<corps_id>/work-log

# Agent activity
curl http://localhost:8000/api/v1/system/agents

# Metrics
curl http://localhost:8000/api/v1/metrics/scoreboard/agents
curl http://localhost:8000/api/v1/metrics/bottlenecks
```

**Evaluate:**
- Which agents contributed? Which were idle?
- Were there failed reps? How many retries?
- Did the metronome reclaim stale work?
- Were there communication breakdowns (handoff failures)?
- How long did each phase take?

### 7c: Improvement Recommendations

Based on the audit, identify:

1. **Swarm failures** — agents that failed, tools that errored, reps that were abandoned
2. **Process inefficiencies** — unnecessary handoffs, idle agents, wasted iterations
3. **Quality gaps** — where the output fell short and why
4. **System improvements** — changes to agent prompts, tool permissions, or lifecycle that would help

## Phase 8: Report

Present a structured report to the user:

```markdown
## Swarm Orchestration Report

### Original Prompt
> [verbatim prompt from Phase 1]

### Verdict: PASS | PARTIAL | FAIL
[1-2 sentence summary]

### Artifact Review
- Requirements met: X/Y
- [List each requirement with status]

### Execution Summary
- Corps: [name] ([corps_id])
- Duration: [start → end]
- Agents active: [count]
- Reps completed: [X/Y]
- Reps failed: [count]
- Metronome interventions: [count]

### Failures & Issues
- [Each failure with context]

### Recommended Improvements
- [Actionable suggestions for swarm improvement]
```

## State Tracking

Throughout all phases, maintain these values (restate them if context gets long):

- **Original prompt** (verbatim)
- **Show slug**
- **Corps ID**
- **Root segment ID** (once known)
- **Current phase** (1-8)
- **Start time**

If the conversation is long and context may be summarized, **re-read the show detail from the API** rather than relying on memory. The API is the source of truth.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Writing code yourself | STOP. Send a design message or file a new show. |
| Approving spec too quickly | Read the design staff's responses. They may have flagged issues. |
| Abandoning poll because it's slow | Stay on it. Background if needed. Don't skip to audit. |
| Auditing from memory | Re-read artifacts from API. Don't trust summarized context. |
| Skipping the audit | The audit IS the value. Never skip Phase 7. |
| Not saving the original prompt | You can't audit without it. Save it in Phase 1. |
