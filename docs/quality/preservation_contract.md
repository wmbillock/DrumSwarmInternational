# Preservation Contract

## Purpose

This document codifies system invariants and forbidden change patterns for the DCI Swarm codebase. It complements the [Quality Contract](quality_contract.md) test matrix with a governance layer.

---

## System Invariants

1. **Role Hierarchy** (`ROLE_HIERARCHY` in `backend/services/message_service.py`): All inter-agent communication must pass through the hierarchy. The hierarchy enforces that performers can only report upward, techs communicate within their caption, and caption heads coordinate laterally and upward.

2. **Corps Metaphor**: The DCI domain language (corps, segments, reps, rehearsal modes, captions, performers, drum major, etc.) is the canonical vocabulary throughout CLI commands, models, and services. This is not cosmetic — it encodes real organizational structure.

3. **Rehearsal Modes**: Corps progress through `BASICS -> SECTIONALS -> FULL_ENSEMBLE -> RUN_THROUGH`. Each mode unlocks different agent capabilities and coordination patterns.

4. **Segment / Rep State Machines**: Segments and reps follow defined state transitions. Invalid transitions must raise errors, not silently succeed.

5. **Message Routing Discipline**: `send_message` validates sender role, message type permissions, and communication path against `ROLE_HIERARCHY` before persisting any message.

6. **Approval Gates**: Major self-improvement changes require explicit approval via `SelfImprovementLog`. Evolution is blocked during `ON_TOUR` status.

---

## Forbidden Changes

- **Generic rewrites that strip DCI metaphor.** Do not rename corps to "project", segments to "tasks", performers to "workers", etc. The domain language is load-bearing.

- **Collapsing distinct roles into a single agent.** Each role in `ROLE_HIERARCHY` represents a distinct responsibility boundary. Merging roles breaks hierarchy enforcement and message routing.

- **Removing hierarchy enforcement from `message_service.py`.** The `ROLE_HIERARCHY` dict and validation in `send_message` are the core access-control mechanism. Do not bypass, weaken, or remove them.

- **Deleting domain vocabulary from CLI commands.** CLI commands use DCI terminology (`corps`, `run-through`, `rehearsal`, etc.). Do not replace with generic terms.

- **Removing or weakening approval gates.** The self-improvement approval flow exists to prevent unchecked agent evolution.

---

## Change Process

1. **TDD-first**: Write or update the test before the implementation. A PR with code changes but no corresponding test changes should be rejected.

2. **Small diffs**: One concern per PR. Do not bundle unrelated changes.

3. **Plan -> Review -> Apply cadence**: Design the change (plan mode or design room), verify it against this contract and the quality contract, then implement.

4. **Invariant check**: Before merging, confirm that `./dci run-through` passes and no system invariant listed above is violated.
