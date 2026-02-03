# LLM Call Audit Report

## Summary
This audit catalogs LLM call sites and their latency tolerance. Batchable workloads are flagged for deferred execution; interactive workflows remain synchronous.

## Call Sites

| Area | File | Purpose | Latency Tolerance | Batchable |
| --- | --- | --- | --- | --- |
| Agent runtime | `backend/services/agent_runtime.py` | Primary agent execution loop | Low (interactive) | No |
| ED chat | `backend/services/ed_chat.py` | Staff ED interactive chat | Low | No |
| Critique session | `backend/services/critique_service.py` | Interactive judge responses | Low | No |
| Critique actions | `backend/services/critique_service.py` | Action item extraction | Medium (post-processing) | Yes |
| Agent adaptation | `backend/services/agent_adaptation.py` | Prompt synthesis for adaptations | High (background) | Yes |
| Judge tape assessment | `backend/services/judge_service.py` | Overall assessment synthesis | Medium (post-scoring) | Yes |
| Corps critique clarify | `backend/api/v1/corps.py` | User-triggered clarification | Low | No |
| Design room helpers | `backend/api/v1/helpers.py` | Misc LLM helper calls | Low | No |

## Batch Integration Notes
- Batchable calls now include workload labels: `agent_synthesis`, `critique_actions`, `scoring_calculation`.
- Non-blocking calls accept deferred responses and fall back to deterministic summaries if queued.
