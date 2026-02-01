# Evolution & Talent Pool

The Evolution & Talent Pool page surfaces the lifecycle of agent performers — selection events, genome metadata, mutation proposals, and safe simulation.

## URL

- `/evolution` — Talent pool, selection events, mutations, and simulation

## Tabs

### Talent Pool

Table of all performers with trust scores, age, status, and session counts. Clicking a performer reveals their **agent genome** — the full identity metadata:

- **Identity**: trust score, status, specialties
- **Performance Summary**: sessions, success rate, average score, rep completion, GUPP violations
- **Agent Definition (Genome)**: role, model tier, tools allowed, prompt template version, classification

### Selection Events

Chronological feed of capability ledger entries representing evolutionary pressure:

- Trust changes (promotions/demotions)
- Retirements (ageout, trust collapse, manual)
- Rep/session completions and failures
- GUPP violations

Filterable by event type.

### Mutations

Self-improvement proposals (definition changes) with their rationale, showing:

- Role and version transition (vN → vN+1)
- Proposed changes (JSON diff)
- Status (pending/approved/rejected)
- Approver identity

### Simulate Mutation

Safe sandbox mode for testing definition changes without applying them. Enter:

1. Agent Definition ID
2. Proposed changes (JSON: `model_tier`, `tools_allowed`, `system_prompt`, `nickname`)
3. Reason for mutation

The simulation reports:

- **Risk level** (low/medium/high)
- **Whether approval is required** (major changes to `model_tier` or `tools_allowed`)
- **Per-field impact analysis** with descriptions
- Confirmation that **no state was modified** (sandbox: true, applied: false)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/evolution/performers/{id}/genome` | Full agent genome metadata |
| GET | `/api/evolution/events` | Selection events (filterable by type) |
| GET | `/api/evolution/mutations` | Self-improvement proposals |
| POST | `/api/evolution/simulate-mutation` | Sandbox mutation simulation |

## Trust Thresholds

| Threshold | Value | Effect |
|-----------|-------|--------|
| Initial | 50.0 | New performer starting trust |
| Probation | 30.0 | Placed on probation |
| Retirement | 20.0 | Auto-retired |
| Maximum | 100.0 | Trust cap |

## Age Limits

- Minimum performer age: 12
- Maximum performer age: 22 (auto-ageout)
