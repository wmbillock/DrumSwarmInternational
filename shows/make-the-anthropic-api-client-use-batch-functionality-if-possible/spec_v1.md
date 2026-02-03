# Anthropic Batch API Integration

## Goal
Integrate Anthropic Batch API into the DCI swarm LLM client to reduce API costs by 50% on high-volume non-blocking workloads.

## Acceptance Criteria
1. Audit report cataloging all LLM client calls with latency tolerance assessment
2. AnthropicLLMClient extended with batch request queueing and threshold triggers
3. Threshold triggers: request count >= 50, time window >= 5 minutes, or explicit submission signal
4. 2-3 high-impact workloads integrated (agent synthesis, design note routing, scoring calculations)
5. Synchronous interface unchanged for blocking paths (design room chat, seance synthesis)
6. Request-result mapping via unique identifiers
7. Error recovery: per-workload-class strategy (batch retry vs individual retry vs manual)
8. Monitoring dashboard for batch job submission, completion time, cost savings, error rates
9. Operational playbook documenting batch lifecycle and recovery procedures
10. Batch results match synchronous results (correctness verified)

## Constraints
- Anthropic Batch API: up to 10,000 requests/batch, 50% cost savings, 24h processing window
- Integrate at AnthropicLLMClient level in backend/services/llm_client.py
- Must not block critical agent execution paths
- Must extend existing client without breaking synchronous interfaces
- Cost/latency trade-offs configurable per workload class
- Non-blocking workloads prioritize cost reduction; interactive workloads skip batching