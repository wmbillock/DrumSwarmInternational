I'll update the show spec based on the design conversation. Here's the complete updated spec:

```markdown
---
show_slug: make-the-anthropic-api-client-use-batch-functionality-if-possible
version: 2
created_at: "2026-02-01T23:53:15.824158+00:00"
updated_at: "2026-02-01T23:58:30.000000+00:00"
approved_at: null
approved_by: null
roles_consulted: []
---

# Make the Anthropic API Client Use Batch Functionality If Possible

## Show Concept

Integrate Anthropic's Batch API into the DCI swarm's LLM client to reduce API costs and scale throughput for high-volume, non-blocking workloads. This show explores where async work (agent runs, design note routing, synthesis, scoring calculations) can be queued and submitted as batch jobs to achieve 50% cost savings and process up to 10,000 requests per batch with up to 24-hour processing windows.

## Musical Design

**Thematic Focus**: Cost Optimization & Throughput Scaling

The batch integration follows a phased progression:
1. **Basics Phase**: Audit current LLM client usage patterns in `backend/services/llm_client.py` to identify high-volume, latency-tolerant workloads (non-blocking synthesis, design note routing, scoring calculations, agent runs)
2. **Sectionals Phase**: Extend `AnthropicLLMClient` with batch request queueing mechanism and threshold triggers (request count ≥50, time window ≥5 minutes, or explicit submission signal)
3. **Full Ensemble Phase**: Integrate batch submission for identified use cases; maintain synchronous interface for blocking paths (real-time design room chat, seance synthesis with deadlines); add monitoring hooks for batch job status tracking
4. **Run-Through Phase**: Dogfood the system; measure cost/latency trade-offs; verify correctness (batch results match synchronous results); adjust thresholds based on real-world patterns

## Visual Design

TBD — awaiting design input

## Guard Design

**Safety & Validation Requirements**:
- Batch requests must maintain ordering guarantees where causality matters
- Failed batch jobs must be retryable without data loss; individual failed requests may be retried immediately outside the batch or surfaced for manual retry depending on workload class
- Async results must be correctly mapped back to original request contexts via unique request identifiers
- Cost savings must be measurable and dashboard-visible
- Latency impact must be quantified per workload (e.g., "design note routing: -2h cost, +20min latency acceptable")
- Non-blocking workloads (async synthesis, background scoring) prioritize cost reduction; interactive workloads (design room responses, real-time agent decisions) must remain low-latency and may skip batching

## General Effect

When complete, the swarm will automatically leverage Anthropic's Batch API for non-blocking workloads at the `AnthropicLLMClient` level. All derived agent requests (synthesis, design note routing, scoring calculations, agent runs) will be queued and submitted as batches when thresholds are met, reducing operational costs by ~50% on identified jobs while maintaining system reliability and performance within acceptable latency bounds. This enables scaling to higher agent concurrency and corpus counts without proportional API cost increases.

## Constraints

- The Anthropic Batch API supports up to 10,000 requests per batch with 50% cost savings and up to 24-hour processing windows. This applies best to high-volume, non-blocking workloads where latency tolerance exists.
- **Batching Strategy**: Integrate batching at the `AnthropicLLMClient` level in `backend/services/llm_client.py`. For all agent requests (synthesis, design note routing, scoring calculations, agent runs), queue requests and submit as batches when: (1) threshold count is reached (e.g., 50+ requests), (2) time window expires (e.g., 5 minutes), or (3) explicit submission signal is sent. Non-blocking workloads (async synthesis, background scoring) prioritize cost reduction; interactive workloads (design room responses, real-time agent decisions) must remain low-latency and may skip batching.
- Batching must not block critical agent execution paths (e.g., real-time design room chat, seance synthesis with deadline constraints)
- Current LLM client initialization in `backend/services/llm_client.py` already supports `AnthropicLLMClient`; batch integration must extend this without breaking existing synchronous interfaces
- Batch job status polling and result retrieval must be resilient to network failures and API rate limits
- Cost/latency trade-offs must be configurable per workload class (e.g., agent runs batch, design notes batch, scoring batch)
- **Error Recovery**: Failed batch jobs must map to individual request retry strategy: (A) retry the entire batch, (B) retry individual failed requests immediately outside the batch, or (C) surface the failure to the user for manual retry — strategy depends on workload class criticality

## Deliverables

1. **Audit Report**: Catalog of current LLM client calls in the codebase with latency tolerance assessment (blocking vs non-blocking, frequency, volume, estimated batch-eligible requests per day/week)
2. **Batch Client Extension**: Enhanced `AnthropicLLMClient` with request queueing, threshold triggers, batch submission, job status polling, and result retrieval
3. **Workload Integration**: Identify and integrate batch functionality into 2-3 high-impact workloads (e.g., agent synthesis, design note routing, scoring calculations)
4. **Request-Result Mapping**: Mechanism to queue requests with unique identifiers and correctly return results to original request contexts
5. **Error Recovery Strategy**: Implementation of retry logic and failure handling per workload class (full batch retry vs. individual request retry vs. manual intervention)
6. **Monitoring & Metrics**: Dashboard visibility into batch job submission, completion time, cost savings, latency impact, and error rates
7. **Operational Playbook**: Documentation of batch job lifecycle, failure recovery procedures, and cost/latency tuning guidelines

## Swarm Prompt

**For Music Writer & Program Coordinator:**

Update the Anthropic API client in `backend/services/llm_client.py` to integrate Anthropic's Batch API functionality. The goal is to achieve 50% cost savings on high-volume, non-blocking workloads (agent synthesis, design note routing, scoring calculations) while maintaining system reliability.

**Phase 1 (Audit)**: Catalog all LLM client calls in the codebase. For each, determine:
- Current latency tolerance (is this blocking? how long can it wait?)
- Call frequency and volume per corp/season
- Whether it's safe to batch (does ordering/causality matter?)
- Estimated cost savings if batched
- Whether the call is made from `AnthropicLLMClient` or a wrapper class

**Phase 2 (Design)**: Design batch queueing at the `AnthropicLLMClient` level:
- Extend `AnthropicLLMClient` with batch request accumulation and buffering
- Define threshold triggers (request count ≥50, time window ≥5 minutes, explicit submission signal)
- Plan request → result mapping: assign unique IDs to queued requests, implement registry to return results to original contexts
- Error handling strategy: for each workload class, decide if failed requests retry as batch, individually, or require manual intervention
- Ensure synchronous interface remains unchanged for blocking paths (design room chat, seance synthesis)

**Phase 3 (Integration)**: Pick 2-3 high-impact workloads and integrate batch submission:
- Suggested candidates: agent synthesis (show_prompt generation), design note routing, scoring calculations
- Add configuration to enable/disable batching per workload class
- Maintain low-latency path for interactive workloads (skip batching, submit immediately)
- Add monitoring hooks to track batch job submission, status, completion, and latency

**Phase 4 (Validation)**: Dogfood the system:
- Run a season with batch integration enabled
- Measure cost savings and latency impact per workload
- Verify correctness (batch results match synchronous results)
- Adjust thresholds based on real-world patterns
- Document any failure scenarios and recovery procedures

**Still Pending**:
- Operational dashboard design: How should batch job metrics be visualized for system operators?
- Workload prioritization: Which 2-3 workloads should be prioritized for Phase 3 integration?

---

*Updated: 2026-02-01 — Design conversation clarified scope as LLM client integration (auto-batching for async workloads), established batching strategy (queue + threshold triggers), confirmed error recovery approach per workload class, and drafted swarm prompt. Ready for Phase 1 audit.*
```