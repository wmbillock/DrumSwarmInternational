---
name: dci-api-shows
description: API actions for managing shows and the Design Room — create, list, design, lint, approve, publish, activate, and complete shows
---

# DCI API: Shows & Design Room

Base URL: `http://localhost:8000/api/v1`

All actions use `curl` via the Bash tool. Replace `<slug>` with the show's slug.

## List Shows

```bash
curl -s http://localhost:8000/api/v1/shows
```

## Create Show

```bash
curl -s -X POST http://localhost:8000/api/v1/shows \
  -H "Content-Type: application/json" \
  -d '{"title": "<title>", "description": "<description>"}'
```

Returns: `{"slug": "...", "title": "...", "status": "draft"}`

## Get Show Detail

```bash
curl -s http://localhost:8000/api/v1/shows/<slug>/detail
```

## Send Design Message

Send a message to the Design Room. The system routes it to the appropriate creative staff role based on content tags.

```bash
curl -s -X POST http://localhost:8000/api/v1/design/threads/<slug>/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "<message text>", "author": "orchestrator"}'
```

## Get Design Messages

```bash
curl -s http://localhost:8000/api/v1/design/threads/<slug>/messages
```

## Get Brief

```bash
curl -s http://localhost:8000/api/v1/design/threads/<slug>/artifacts/brief
```

## Update Brief

```bash
curl -s -X PUT http://localhost:8000/api/v1/design/threads/<slug>/artifacts/brief \
  -H "Content-Type: application/json" \
  -d '{"content": "<brief content>"}'
```

## Get Prompt

```bash
curl -s http://localhost:8000/api/v1/design/threads/<slug>/artifacts/prompt
```

## Update Prompt

```bash
curl -s -X PUT http://localhost:8000/api/v1/design/threads/<slug>/artifacts/prompt \
  -H "Content-Type: application/json" \
  -d '{"content": "<prompt content>"}'
```

## Lint Prompt

```bash
curl -s -X POST http://localhost:8000/api/v1/design/threads/<slug>/lint
```

## Publish Show (draft -> needs_review)

```bash
curl -s -X POST http://localhost:8000/api/v1/design/threads/<slug>/publish
```

## Approve Show (needs_review -> approved)

```bash
curl -s -X POST http://localhost:8000/api/v1/design/threads/<slug>/approve
```

## Activate Show (approved -> published, spawns corps)

```bash
curl -s -X POST http://localhost:8000/api/v1/shows/<slug>/activate
```

## Complete Show

```bash
curl -s -X POST http://localhost:8000/api/v1/shows/<slug>/complete
```

## Launch Tour for Show

```bash
curl -s -X POST http://localhost:8000/api/v1/shows/<slug>/tour \
  -H "Content-Type: application/json" \
  -d '{"corps_id": "<corps_id>"}'
```

## Get Show Versions

```bash
curl -s http://localhost:8000/api/v1/design/threads/<slug>/versions
```
