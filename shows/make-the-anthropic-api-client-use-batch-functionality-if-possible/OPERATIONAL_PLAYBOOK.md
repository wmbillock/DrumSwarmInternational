# Anthropic Batch Operations Playbook

## Overview
Batching is used for non-blocking workloads to reduce cost. Requests are queued in the Anthropic client and submitted based on thresholds:
- Queue size >= 50
- Queue age >= 5 minutes
- Explicit submission via `submit_batch()`

## Lifecycle
1. **Queue**: Batchable requests are added with a unique request ID.
2. **Submit**: Thresholds or explicit signal triggers submission.
3. **Process**: Batch jobs are recorded with status and workload counts.
4. **Complete**: Results are stored and can be correlated via request IDs.
5. **Fallback**: If batch submission fails, requests are processed locally.

## Monitoring
Use the System Health dashboard → **LLM Batch** panel to inspect:
- Queue size
- Submitted/completed counts
- Error and fallback rates
- Recent batch job status

## Recovery
- If batch submission errors appear, validate Anthropic credentials and retry.
- For persistent failures, set `ANTHROPIC_BATCH_COUNT` lower or disable batchable flags in workloads.
- Fallback processing ensures critical background workflows continue to run.

## Correctness Verification
- Batch outputs are stored with request IDs and compared to synchronous fallbacks in QA.
- Mechanical summaries are used when batch results are deferred to preserve correctness guarantees.
