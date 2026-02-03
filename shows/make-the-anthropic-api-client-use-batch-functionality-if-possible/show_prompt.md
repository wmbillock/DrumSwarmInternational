# Anthropic Batch API Integration

## Objective
Integrate Anthropic Batch API into the DCI swarm LLM client to achieve 50% cost savings on high-volume, non-blocking workloads (agent synthesis, design note routing, scoring calculations) while maintaining system reliability.

## Musical Design
Phased progression:
1. **Basics**: Audit current LLM client usage patterns to identify batch-eligible workloads
2. **Sectionals**: Extend AnthropicLLMClient with batch request queueing and threshold triggers
3. **Full Ensemble**: Integrate batch submission for 2-3 high-impact workloads
4. **Run-Through**: Dogfood, measure cost/latency, verify correctness

## Guard Design
- Batch requests maintain ordering where causality matters
- Failed batch jobs retryable without data loss
- Async results correctly mapped back via unique identifiers
- Non-blocking workloads prioritize cost; interactive workloads skip batching

## General Effect
The swarm automatically leverages batch API for non-blocking workloads, reducing costs by 50% while maintaining reliability.

## Constraints
- Integrate at AnthropicLLMClient level in backend/services/llm_client.py
- Threshold triggers: count >= 50, time >= 5 min, or explicit signal
- Must not block critical paths (design room chat, seance synthesis)
- Extend without breaking existing synchronous interfaces
- Cost/latency configurable per workload class

## Deliverables
- Audit report cataloging all LLM client calls with latency tolerance
- Enhanced AnthropicLLMClient with batch queueing, submission, polling, result retrieval
- Integration with 2-3 high-impact workloads
- Request-result mapping mechanism with unique identifiers
- Error recovery implementation per workload class
- Monitoring dashboard for batch metrics
- Operational playbook documenting lifecycle and recovery

## Acceptance Criteria
- Batch requests submitted when thresholds met
- Synchronous interface unchanged for blocking paths
- Batch results match synchronous results (correctness verified)
- Cost savings measurable and dashboard-visible
- Failed requests recoverable per workload class strategy
- Tests pass, no regressions