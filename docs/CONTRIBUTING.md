# Contributing to DCI Swarm

## Cadence: Plan -> Review -> Apply

1. **Plan**: Design the change in plan mode or the design room. Identify which files, models, and services are affected.
2. **Review**: Check the change against the [Quality Contract](quality/quality_contract.md) and [Preservation Contract](quality/preservation_contract.md). Ensure no system invariants are violated.
3. **Apply**: Implement in a small, focused diff. One concern per PR. TDD-first — write or update tests before implementation.

## Artifact Locations

| Artifact | Location |
|----------|----------|
| Quality contract (test matrix) | `docs/quality/quality_contract.md` |
| Preservation contract (invariants) | `docs/quality/preservation_contract.md` |
| Architecture overview | `docs/architecture.md` |
| Backend tests | `backend/tests/` |

## Running Tests

```bash
# Full test suite
./dci run-through

# Run a specific test
./dci run-through -k test_preservation_smoke

# Run by quality contract ID
./dci run-through -k QC_A_01
```

## Rules

- **Preserve the DCI metaphor.** Corps, segments, reps, rehearsal modes, captions, performers — these are not cosmetic. Do not replace with generic terms.
- **No role collapse.** Each role in `ROLE_HIERARCHY` is a distinct responsibility boundary.
- **TDD-first.** Every code change must have a corresponding test change.
- **Reference the preservation contract** when proposing structural changes.
