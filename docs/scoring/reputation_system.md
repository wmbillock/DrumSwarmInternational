# Reputation / Fitness Update System

## Overview

After a performance is scored (Standings produced), each participating agent's reputation in the talent pool is updated and placement history is appended to the corps.

All updates are deterministic, pure YAML, no DB writes.

## Trust Score Formula

Weighted moving average:

```
new_trust = (old_trust * old_samples + performance_score) / (old_samples + 1)
```

Where `old_samples = total_sessions`. Converges naturally as sample size grows.

## Minimum Sample Dampening

Below a threshold (default 3), the trust delta is scaled:

```
dampening = min(total_sessions, threshold) / threshold
new_trust = old_trust + dampening * (full_new_trust - old_trust)
```

This prevents a single good or bad score from swinging a new agent's trust wildly.

## Season Decay

Between seasons, trust decays toward a baseline (default 50.0):

```
trust += decay_rate * (baseline - trust)
```

Default `decay_rate = 0.05`. Setting `decay_rate = 0` disables decay.

## Session Counting

- `total_sessions` increments by 1 per scored performance.
- `successful_sessions` increments by 1 when `final_score >= 60.0`.
- `failed_sessions` increments by 1 when `final_score < 60.0`.

## Retirement / Release

`release_agent` sets `availability` back to `"active"`, preserving all reputation fields (`trust_score`, `total_sessions`, `successful_sessions`, `failed_sessions`, `experience_seasons`). Corps history entries are unaffected.

## Score Range Enforcement

Both `performance_score` input and computed `trust_score` are enforced to [0, 100]:

- `performance_score` is validated at the start of `update_reputations`. Values that are None, NaN, or outside 0..100 raise `ValueError`.
- Computed `trust_score` is clamped to [0, 100] after both reputation updates and season decay.

## Idempotency (session_id)

`update_reputations` accepts an optional `session_id: str` parameter. Each agent tracks a `seen_sessions` list (capped at 20 most recent). If the given `session_id` has already been processed for an agent, that agent is skipped. This prevents double-counting when the same standings are applied more than once.

## Corps History

`record_corps_placement` appends an entry to the corps YAML `history` list:

```yaml
history:
  - season_id: "2025-spring"
    placement: 1
    final_score: 92.5
    notes: "Clean sweep"
```
