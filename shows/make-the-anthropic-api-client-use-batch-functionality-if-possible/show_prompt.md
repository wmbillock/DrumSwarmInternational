# Show Prompt

## Show Concept

Derived from spec and design discussions.



## Musical Design

No musical design notes captured yet.



## Visual Design

No visual design notes captured yet.



## Guard Design

No guard design notes captured yet.



## General Effect

No general effect notes captured yet.



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

