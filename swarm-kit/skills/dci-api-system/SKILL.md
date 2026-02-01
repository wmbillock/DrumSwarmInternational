---
name: dci-api-system
description: API actions for system monitoring — health check, LLM usage, agents overview, work log
---

# DCI API: System Monitoring

Base URL: `http://localhost:8000/api/v1`

All actions use `curl` via the Bash tool.

## System Health

```bash
curl -s http://localhost:8000/api/v1/system/health
```

## LLM Usage

```bash
curl -s http://localhost:8000/api/v1/system/llm-usage
```

## Agents Overview

```bash
curl -s http://localhost:8000/api/v1/system/agents
```

## Work Log

```bash
curl -s http://localhost:8000/api/v1/system/work-log
```

## Metrics: Corps Scoreboard

```bash
curl -s http://localhost:8000/api/v1/metrics/scoreboard/corps
```

## Metrics: Agent Scoreboard

```bash
curl -s http://localhost:8000/api/v1/metrics/scoreboard/agents
```

## Metrics: Bottlenecks

```bash
curl -s http://localhost:8000/api/v1/metrics/bottlenecks
```

## Metrics: Trends

```bash
curl -s http://localhost:8000/api/v1/metrics/trends
```
