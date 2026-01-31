# Talent Pool YAML Schema

The talent pool is a human-readable YAML export of performer data. The database remains the **system of record**; YAML files are generated views.

## Output Structure

```
talent_pool/
├── ledger.yaml            # index of all non-retired agents
└── agents/
    └── <agent-id>.yaml    # full profile per agent
```

## Ledger Format (`ledger.yaml`)

```yaml
agents:
  - agent_id: "abc-123"
    display_name: "Alice"
    primary_instrument: "bass"
    availability: "active"
  - agent_id: "def-456"
    display_name: "Bob"
    primary_instrument: "drums"
    availability: "probation"
```

Each entry contains the four **required fields** only, serving as a lightweight index.

## Agent File Format (`agents/<id>.yaml`)

```yaml
agent_id: "abc-123"
display_name: "Alice"
primary_instrument: "bass"
availability: "active"
trust_score: 72.5
total_sessions: 10
successful_sessions: 8
failed_sessions: 2
experience_seasons: 3
last_active_season: 3
specialties:
  - jazz
  - funk
```

### Required Fields

| Field | Type | Source |
|---|---|---|
| `agent_id` | string | `performer.id` |
| `display_name` | string | `performer.name` |
| `primary_instrument` | string | `performer.role_type` |
| `availability` | string | `performer.status` enum value |

### Optional Fields

| Field | Type | Source |
|---|---|---|
| `trust_score` | float | `performer.trust_score` |
| `total_sessions` | int | `performer.total_sessions` |
| `successful_sessions` | int | `performer.successful_sessions` |
| `failed_sessions` | int | `performer.failed_sessions` |
| `experience_seasons` | int | `performer.experience_seasons` |
| `last_active_season` | int | `performer.experience_seasons` (no separate tracking yet) |
| `specialties` | list[string] | `performer.specialties` (parsed from comma-separated string) |

## Notes

- Retired performers are excluded from export.
- Files are written atomically (write to temp file, then rename) to avoid partial writes.
- To regenerate, call `export_talent_pool(db_session, output_path)` from `backend.services.talent_pool`.
