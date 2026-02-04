# Caption Awards Achievement System

## Overview
Caption awards are humorous achievements awarded to corps, performers, and staff
at measurable activity milestones. The catalog is stored in
`backend/config/awards/caption_awards.yaml` and evaluated by
`backend/services/achievement_detector.py`.

## Catalog Format
Each achievement entry includes:
- `id`: Stable identifier.
- `category`: One of the 12 caption award categories.
- `tier`: `bronze`, `silver`, `gold`, `platinum`, `diamond`.
- `scope`: `corps`, `performer`, or `staff`.
- `name`, `description`: Display text.
- `trigger`: Measurable condition.

Example entry:

```yaml
- id: brass_excellence_corps_01
  category: brass_excellence
  tier: bronze
  scope: corps
  name: "Brass Excellence - Warmup Wizard"
  description: "Corps average brass score at least 60. (min 5 completed reps)"
  trigger:
    metric: caption_avg_score
    op: ">="
    value: 60
    caption: brass
    min_reps_completed: 5
```

## Supported Trigger Fields
- `metric`: The metric name evaluated for the recipient.
- `op`: Comparison operator (`>=`, `>`, `==`, `<`, `<=`).
- `value`: Threshold for the metric.
- `caption`: Optional caption filter (`brass`, `percussion`, `guard`, `visual`, `general_effect`).
- `min_reps_completed`: Optional minimum reps completed.
- `min_total_sessions`: Optional minimum sessions before eligibility.
- `min_success_rate`: Optional success-rate floor.

## Trigger Metrics
Metrics are computed on demand from the database:
- `reps_completed`, `reps_failed`
- `sessions_total`, `sessions_completed`, `sessions_failed`
- `success_rate`
- `avg_score` (caption-filtered when requested)
- `caption_avg_score`
- `max_reps_in_session`
- `unique_captions`
- `unique_segment_types` (corps only)
- `handoffs_sent`
- `comeback_count`

## API Endpoints
- `GET /api/v1/awards` with optional filters (`recipient_id`, `corps_id`, `category`, `recipient_type`)
- `POST /api/v1/awards/check/{corps_id}` to manually trigger checks

## Notifications
New awards are broadcast as WebSocket events of type `award.unlocked`.
