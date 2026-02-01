# Competitions UI

## Overview

Competitions model the evaluation cycle where corps (agent teams) execute shows (tasks) and receive scored assessments from judge agents. The competition metaphor maps directly to agent quality measurement: each caption score reflects a dimension of output quality.

## Data Flow

```
Score (judge) → CompositeScore → Standings → Placement → Reputation → Drafting
```

1. **Judge agents** score each corps across five captions (brass, percussion, guard, visual, general_effect)
2. **CompositeScore** applies weights to produce a final score with penalty deductions
3. **Standings** rank all corps in a season by final score
4. **Placements** are recorded in each corps' `corps.yaml` history
5. **Reputation** trust_score updates feed back into the drafting system

## Caption Weights and Thresholds

| Caption | Weight | Description |
|---------|--------|-------------|
| brass | 20% | Code quality / correctness |
| percussion | 20% | Test coverage / reliability |
| guard | 20% | Security / error handling |
| visual | 15% | UI/UX / documentation quality |
| general_effect | 25% | Overall coherence / design |

**Thresholds:**
- `REWORK_THRESHOLD = 60.0` — Below this score, automatic rework (another rep)
- `ESCALATION_THRESHOLD = 40.0` — Below this, escalate to ED/user for intervention

## UI Screens

### CompetitionsList (`/competitions`)

- Lists all competitions with season, show, status, and corps count
- "Create Competition" button opens inline form
- Form fields: season ID, show selector (approved shows), corps multi-select
- Row click navigates to CompetitionDetail

### CompetitionDetail (`/competitions/:id`)

Three tabs:

1. **Standings** (default) — Table with rank, corps, final score, raw score, and inline caption mini-bars. Click a row to expand and see per-caption breakdown with weights and judge commentary.
2. **Caption Breakdown** — Side-by-side table showing all captions for all corps.
3. **Compare** — Select two corps from dropdowns for side-by-side caption comparison with diff column.

### Corps Breakdown Endpoint

`GET /api/v1/competitions/{competition_id}/corps/{corps_id}/breakdown`

Returns per-caption score details including weight, weighted score, and synthetic commentary.

## Telemetry Integration

The TelemetryPanel (right rail) includes a "Latest Scores" section that:
- Fetches the most recently completed competition
- Displays top-3 entries with rank and score in compact format

## Connection to Evolution

Competition placements feed the evolution cycle:
- `record_corps_placement()` writes to corps history after each competition
- Trust scores derived from placement history influence drafting priority
- Corps with consistently low scores may be disbanded or restructured
- High-performing corps get priority access to new shows
