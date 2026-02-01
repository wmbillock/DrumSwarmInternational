# V1 API Reference

Base path: `/api/v1`

All endpoints return JSON. Errors use standard HTTP status codes with `{"detail": "..."}` bodies.

---

## Corps

### `GET /api/v1/corps`

List all corps from filesystem workspaces.

**Response** `200`
```json
[
  {
    "corps_id": "blue-devils",
    "display_name": "Blue Devils",
    "philosophy": "Innovation through excellence",
    "state": "active"
  }
]
```

### `GET /api/v1/corps/{corps_id}`

Get corps detail including roster size and history.

**Response** `200`
```json
{
  "corps_id": "blue-devils",
  "display_name": "Blue Devils",
  "philosophy": "Innovation through excellence",
  "state": "active",
  "roster_size": 14,
  "history_count": 3,
  "history": [
    {"season_id": "s1", "placement": 1, "final_score": 85.0, "notes": "show:my-show"}
  ]
}
```

**Errors:** `400` invalid ID, `404` not found.

---

## Runs

### `GET /api/v1/runs`

List all run manifests across seasons, sorted by `started_at` descending.

**Response** `200`
```json
[
  {
    "run_id": "my-show-blue-devils-20260131T120000",
    "show_slug": "my-show",
    "corps_id": "blue-devils",
    "season_id": "s1",
    "started_at": "2026-01-31T12:00:00+00:00",
    "status": "completed"
  }
]
```

### `GET /api/v1/runs/{run_id}`

Get run manifest and output.

**Response** `200` — manifest fields plus `"output": "..."` (truncated to 10K chars).

### `GET /api/v1/runs/{run_id}/logs`

Get run output log (truncated to 50K chars).

**Response** `200`
```json
{"run_id": "...", "log": "..."}
```

### `POST /api/v1/runs`

Start a show run. Creates manifest, executes stub, returns run ID.

**Request**
```json
{
  "show_slug": "my-show",
  "corps_id": "blue-devils",
  "season_id": "s1"
}
```

**Response** `200`
```json
{"run_id": "my-show-blue-devils-20260131T120000", "status": "completed"}
```

**Errors:** `400` show not approved, `404` show/corps/season not found.

---

## Design Room

### `POST /api/v1/design/threads`

Create a new design thread (show workspace + empty spec).

**Request**
```json
{"title": "My New Show"}
```

**Response** `200`
```json
{"slug": "my-new-show", "path": "/path/to/shows/my-new-show"}
```

### `GET /api/v1/design/threads`

List all design threads.

**Response** `200`
```json
[
  {"slug": "my-new-show", "status": "draft", "has_spec": true}
]
```

### `GET /api/v1/design/threads/{slug}/messages`

Get parsed design notes as messages.

**Response** `200`
```json
{
  "slug": "my-new-show",
  "messages": [
    {"role": "music_writer", "content": "Add brass feature", "tags": ["music"]}
  ]
}
```

### `POST /api/v1/design/threads/{slug}/messages`

Post a message — routes via `note_router` to determine tags and role.

**Request**
```json
{"message": "Add a brass section with forte dynamics", "role_hint": null}
```

**Response** `200`
```json
{
  "role": "music_writer",
  "tags": ["music"],
  "response": "[music_writer] Noted. Tags: music."
}
```

### `GET /api/v1/design/threads/{slug}/artifacts/brief`

Get the current show spec.

**Response** `200`
```json
{"slug": "my-new-show", "content": "# My New Show\n\n## Decisions\n..."}
```

### `PUT /api/v1/design/threads/{slug}/artifacts/brief`

Update the show spec.

**Request**
```json
{"content": "# Updated Spec\n\n## Decisions\n- ..."}
```

**Response** `200`
```json
{"status": "updated"}
```

### `GET /api/v1/design/threads/{slug}/artifacts/prompt`

Get the finalized show prompt (`show_prompt.md`).

**Response** `200`
```json
{"slug": "my-new-show", "content": "# Show Prompt\n..."}
```

### `POST /api/v1/design/threads/{slug}/approve`

Approve spec — freezes versioned copy, marks show as approved.

**Response** `200`
```json
{"version": 1, "path": "shows/my-new-show/spec_v1.md"}
```

**Errors:** `400` empty spec or already approved.

### `GET /api/v1/design/threads/{slug}/versions`

List approved spec versions.

**Response** `200`
```json
{"versions": [{"version": 1, "path": "spec_v1.md"}]}
```

---

## Corps History / Seance

### `GET /api/v1/corps/{corps_id}/history`

List past shows for a corps (builds history index from `corps.yaml` + filesystem).

**Response** `200`
```json
{
  "corps_id": "blue-devils",
  "entries": [
    {
      "entry_id": "blue-devils-s1",
      "season_id": "s1",
      "show_slug": "my-show",
      "placement": 1,
      "final_score": 85.0,
      "artifacts": {"standings": "seasons/s1/standings.yaml"},
      "runs": ["my-show-blue-devils-20260131T120000"]
    }
  ]
}
```

### `POST /api/v1/seances`

Start a seance session bound to a specific history entry.

**Request**
```json
{"corps_id": "blue-devils", "entry_id": "blue-devils-s1"}
```

**Response** `200`
```json
{"seance_id": "...", "corps_id": "blue-devils", "entry_id": "blue-devils-s1", "status": "open"}
```

### `GET /api/v1/seances/{seance_id}`

Get seance session metadata.

**Response** `200` — session object with status, corps_id, entry_id, binder info.

### `POST /api/v1/seances/{seance_id}/messages`

Post a message to the ED in a seance session.

**Request**
```json
{"message": "What went well in this show?", "mode": "strict"}
```

`mode` is `"strict"` (grounded in binder artifacts only) or `"relaxed"` (broader context).

**Response** `200` — ED response object.

### `GET /api/v1/seances/{seance_id}/transcript`

Read full seance transcript.

**Response** `200`
```json
{"seance_id": "...", "transcript": "..."}
```

---

## Competitions

### `POST /api/v1/competitions`

Create a competition — validates show is approved, corps exist, registers corps in season.

**Request**
```json
{
  "season_id": "s1",
  "show_slug": "my-show",
  "corps_ids": ["blue-devils", "cavaliers"]
}
```

**Response** `200`
```json
{
  "competition_id": "s1-my-show",
  "season_id": "s1",
  "show_slug": "my-show",
  "corps_ids": ["blue-devils", "cavaliers"],
  "status": "ready"
}
```

### `POST /api/v1/competitions/{competition_id}/run`

Run a competition heat with deterministic stub scoring, compute standings, record placements.

**Response** `200`
```json
{
  "competition_id": "s1-my-show",
  "status": "completed",
  "standings": [
    {
      "corps_id": "blue-devils",
      "rank": 1,
      "final_score": 78.4,
      "raw_score": 78.4,
      "caption_scores": {"brass": 82, "percussion": 75, "guard": 71, "visual": 80, "general_effect": 84}
    }
  ]
}
```

### `GET /api/v1/competitions/{competition_id}/scores`

Retrieve scores/standings for a completed competition.

**Response** `200` — standings object with `results` array, `season_id`, `show_slug`, `generated_at`.

**Errors:** `404` standings not found (competition hasn't run).

---

## Validation

All ID and slug parameters are validated:
- Must match `^[a-zA-Z0-9][a-zA-Z0-9._-]*$`
- Path traversal (`..`, `/`, `\`) is rejected with `400`
