# Living System Correctness & Durability Fixes (A–G)

## A — Drafting sees updated trust

Added tests proving `draft_roster` reads fresh agent YAML (including `trust_score`) after `update_reputations` and `apply_season_decay`. No code change needed — `load_talent_pool` already reads full agent files.

## B — Score validation & clamping

Added `_validate_score` and `_clamp` helpers in `reputation.py`. `performance_score` input is validated to 0..100 (rejects None, NaN, out-of-range). Computed `trust_score` is clamped to [0, 100] after both reputation updates and season decay.

## C — Idempotent reputation updates

`update_reputations` now accepts a `session_id` parameter. Each agent tracks `seen_sessions` (capped at 20). If `session_id` was already processed, the agent is skipped.

## D — Shared YAML utilities

Extracted `backend/services/yaml_util.py` with `atomic_write` and `safe_dump_yaml`. Replaced 5 duplicate `_atomic_write` definitions and all `yaml.dump(x, default_flow_style=False)` calls across 9 service modules.

## E — Prompt template lint fix

Changed `test_no_unfilled_after_substitution` to use regex `r'\{\{\s*\w+\s*\}\}'` instead of raw `"{{" not in text`, avoiding false positives from non-placeholder `{{` sequences.

## F — Root README

Created `README.md` with quick start, documentation links, and demo instructions.

## G — Lifecycle tour demo

Created `backend/scripts/tour_demo.py` with `run_tour(base_dir)` function exercising the full pool → draft → score → reputation update → decay → release cycle. Companion test in `backend/tests/test_tour_demo.py`.
