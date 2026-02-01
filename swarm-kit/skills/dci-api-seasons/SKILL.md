---
name: dci-api-seasons
description: API actions for managing seasons and competitions — create seasons, register corps, create and run competitions, get scores and recaps
---

# DCI API: Seasons & Competitions

Base URL: `http://localhost:8000/api/v1`

All actions use `curl` via the Bash tool.

## List Seasons

```bash
curl -s http://localhost:8000/api/v1/seasons
```

## Create Season

```bash
curl -s -X POST http://localhost:8000/api/v1/seasons \
  -H "Content-Type: application/json" \
  -d '{"name": "<season name>"}'
```

Optional: provide `season_id` directly instead of `name`. Can also pass `metadata` (object).

## Get Season

```bash
curl -s http://localhost:8000/api/v1/seasons/<season_id>
```

## Update Season

```bash
curl -s -X PUT http://localhost:8000/api/v1/seasons/<season_id> \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"key": "value"}}'
```

## Register Corps to Season

```bash
curl -s -X POST http://localhost:8000/api/v1/seasons/<season_id>/corps \
  -H "Content-Type: application/json" \
  -d '{"corps_id": "<corps_id>"}'
```

## List Competitions

```bash
curl -s http://localhost:8000/api/v1/competitions
```

Supports query params: `?season_id=<id>` and `?show_slug=<slug>`

## Create Competition

Requires show to be approved. Competition ID = `{season_id}-{show_slug}`.

```bash
curl -s -X POST http://localhost:8000/api/v1/competitions \
  -H "Content-Type: application/json" \
  -d '{"season_id": "<season_id>", "show_slug": "<show_slug>", "corps_ids": ["<id1>", "<id2>"]}'
```

## Run Competition

```bash
curl -s -X POST http://localhost:8000/api/v1/competitions/<competition_id>/run
```

## Get Scores

```bash
curl -s http://localhost:8000/api/v1/competitions/<competition_id>/scores
```

## Get Score Breakdown (per corps)

```bash
curl -s http://localhost:8000/api/v1/competitions/<competition_id>/corps/<corps_id>/breakdown
```

## Get Recap

```bash
curl -s http://localhost:8000/api/v1/competitions/<competition_id>/recap
```

## Get Tapes

```bash
curl -s http://localhost:8000/api/v1/competitions/<competition_id>/tapes
```

## Get Tape for Corps

```bash
curl -s http://localhost:8000/api/v1/competitions/<competition_id>/tapes/<corps_id>
```

## Start Critique Session

```bash
curl -s -X POST http://localhost:8000/api/v1/competitions/<competition_id>/critique \
  -H "Content-Type: application/json" \
  -d '{"corps_id": "<corps_id>"}'
```

## Generate All Reports

```bash
curl -s -X POST http://localhost:8000/api/v1/competitions/<competition_id>/reports/generate-all
```
