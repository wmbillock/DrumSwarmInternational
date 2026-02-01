---
name: dci-dogfooding
description: Use when code changes have been made to the DCI swarm and need to be verified through the live system — exercises new features, endpoints, and behaviors via API calls and CLI commands against the running swarm
---

# DCI Dogfooding

## Overview

Verify code changes to the DCI swarm by exercising them through the live system. You test through the API and CLI, never by reading source code or running unit tests. The running swarm is the source of truth.

**Core principle:** If you didn't exercise it through the live API, you didn't verify it.

## When to Use

- After implementing backend/frontend changes to the DCI swarm
- After fixing bugs in the swarm
- When the user says "dogfood this" or "verify through the swarm"
- Before committing changes, to catch runtime issues unit tests miss

**When NOT to use:**
- For unit test verification (use pytest directly)
- For TypeScript type checking (use tsc)
- For code review (use code-review skill)

## Prerequisites

The backend must be running at `localhost:8000`. Check with:

```bash
curl -s http://localhost:8000/api/v1/corps | head -c 100
```

If not running: `./dci forward-march` or `./dci ten-hut`.

## The Process

### 1. Identify What Changed

List the features/endpoints that were added or modified. For each, determine the API call that exercises it.

### 2. Exercise Each Change via API

For every changed feature, make the actual API call and verify the response:

```bash
# Example: testing a new query parameter
curl -s http://localhost:8000/api/v1/corps | jq '.[] | .corps_type'

# Example: testing a rejection case
curl -s -X POST http://localhost:8000/api/v1/seasons/test/corps \
  -H "Content-Type: application/json" \
  -d '{"corps_id": "system-corps-id"}'
# Expect: 400
```

**Do NOT:**
- Assume it works because the code looks right
- Skip error cases (test rejections, not just happy paths)
- Only test via the UI (Playwright clicks don't prove the API works)

### 3. Run Integration Flows

If the change touches a workflow (e.g., competition → auto-critique), run the full flow:

```bash
# Create a test season
curl -X POST http://localhost:8000/api/v1/seasons -d '...'

# Register corps
curl -X POST http://localhost:8000/api/v1/seasons/<id>/corps -d '...'

# Run competition
curl -X POST http://localhost:8000/api/v1/seasons/<id>/competitions/<comp>/run

# Check results
curl http://localhost:8000/api/v1/seasons/<id>/competitions/<comp>/standings
```

### 4. Report Findings

For each feature tested:
- **PASS**: API returned expected response
- **FAIL**: Unexpected error or wrong behavior (include the error)
- **FIXED**: Found and fixed a bug during dogfooding (describe what was wrong)

### 5. Fix and Re-verify

If bugs are found:
1. Fix the code
2. Re-exercise the same API call
3. Confirm the fix works through the live system

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Only clicking through Playwright UI | Make direct API calls with curl |
| Testing only happy paths | Test error cases, rejections, edge cases |
| Assuming code correctness from reading it | Exercise it live — runtime bugs are invisible in source |
| Skipping multi-step workflows | If feature spans multiple endpoints, test the full flow |
| Not checking response bodies | Read the actual JSON, don't just check status codes |
