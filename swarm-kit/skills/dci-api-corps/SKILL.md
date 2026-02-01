---
name: dci-api-corps
description: API actions for managing corps — list, create, generate identity, get detail, send lifecycle commands
---

# DCI API: Corps Management

Base URL: `http://localhost:8000/api/v1`

All actions use `curl` via the Bash tool. Replace `<corps_id>` with the corps UUID.

## List Corps

```bash
curl -s http://localhost:8000/api/v1/corps
```

## Generate Identity (name, mascot, colors)

```bash
curl -s -X POST http://localhost:8000/api/v1/corps/generate-identity \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Create Corps

```bash
curl -s -X POST http://localhost:8000/api/v1/corps \
  -H "Content-Type: application/json" \
  -d '{"name": "<name>", "mascot": "<mascot>", "philosophy": "<philosophy>"}'
```

Optional fields: `color_scheme` (object), `uniform_concept` (string).

## Get Corps Detail

```bash
curl -s http://localhost:8000/api/v1/corps/<corps_id>
```

## Send Command (go_on_tour, return_to_camps, etc.)

```bash
curl -s -X POST http://localhost:8000/api/v1/corps/<corps_id>/command \
  -H "Content-Type: application/json" \
  -d '{"command": "<command_name>"}'
```

Valid commands: `go_on_tour`, `return_to_camps`, `disband`

## Ready for Contest

```bash
curl -s -X POST http://localhost:8000/api/v1/corps/<corps_id>/ready-for-contest
```

## Return to Tour (from READY_FOR_CONTEST back to ON_TOUR)

```bash
curl -s -X POST http://localhost:8000/api/v1/corps/<corps_id>/return-to-tour
```

## Complete Corps

```bash
curl -s -X POST http://localhost:8000/api/v1/corps/<corps_id>/complete
```

## Get Corps History

```bash
curl -s http://localhost:8000/api/v1/corps/<corps_id>/history
```

## Get Corps Staff

```bash
curl -s http://localhost:8000/api/v1/corps/<corps_id>/staff
```

## ED Chat (talk to Executive Director)

```bash
curl -s -X POST http://localhost:8000/api/v1/corps/<corps_id>/ed-chat \
  -H "Content-Type: application/json" \
  -d '{"message": "<message>"}'
```

## Send Feedback to Corps

```bash
curl -s -X POST http://localhost:8000/api/v1/corps/<corps_id>/feedback \
  -H "Content-Type: application/json" \
  -d '{"feedback": "<feedback text>", "source": "director"}'
```
