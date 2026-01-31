# Season Schema

## Directory Structure

```
seasons/
└── <season_id>/
    ├── season.yaml         # season identity and metadata
    ├── scorecard.md        # caption scoring headings
    ├── lifecycle_rules.md  # season lifecycle rules
    └── performances/
        └── <corps_id>/     # created when a corps registers
```

## season.yaml

| Field | Type | Required | Description |
|---|---|---|---|
| `season_id` | string | yes | Unique identifier for the season |
| `metadata` | dict | no | Arbitrary metadata (theme, year, etc.) |

## scorecard.md

Stubbed markdown with caption headings:

- Brass
- Percussion
- Guard
- Visual
- General Effect

## lifecycle_rules.md

Placeholder for season-specific lifecycle and scoring rules.

## performances/

Each subdirectory corresponds to a registered corps (`<corps_id>/`). Created by `register_corps` when a corps enters the season. The corps must exist in the `corps/` directory with a valid `corps.yaml`.
