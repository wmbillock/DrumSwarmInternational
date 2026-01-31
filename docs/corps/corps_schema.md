# Corps Schema

## Directory Structure

```
corps/
└── <corps_id>/
    ├── corps.yaml    # identity, philosophy, state, season history
    └── roster.yaml   # agent assignments referencing talent pool agent_ids
```

## corps.yaml

| Field | Type | Required | Description |
|---|---|---|---|
| `corps_id` | string | yes | Unique identifier |
| `display_name` | string | yes | Human-readable name |
| `philosophy` | string | yes | Short guiding principle |
| `state` | enum | yes | One of: `commissioned`, `active`, `contending`, `stagnant`, `rebuilt`, `retired` |
| `current_season_id` | string | no | Active season reference |
| `history` | list | no | Season history entries |

### History Entry

```yaml
history:
  - season_id: "season-2025"
    placement: 1
    notes: "champion"
```

## roster.yaml

```yaml
corps_id: "blue-devils-2025"
assignments:
  - agent_id: "abc-123"
    role: "brass_caption_head"
  - agent_id: "def-456"
    role: "percussion_tech"
```

Each `agent_id` must reference an existing agent in the talent pool (`talent_pool/agents/<agent_id>.yaml`).

## State Transitions

```
commissioned → active
active → contending | stagnant | retired
contending → active | stagnant | retired
stagnant → rebuilt | retired
rebuilt → active
retired → (terminal)
```

## Relationship to Talent Pool

Roster assignments reference agents by `agent_id` from the talent pool. The talent pool is the source of truth for agent identity and capabilities; the roster tracks which agents are assigned to a corps and in what role.
