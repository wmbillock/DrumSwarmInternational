<!-- tags: admin -->

**[user]** Reference doc: https://platform.claude.com/workspaces/default/batches
<!-- tags: admin -->

**[user]** let's leverage this feature if at all possible

<!-- tags: admin -->
**[program_coordinator]** I need to understand the scope before drafting language. One clarifying question:

**Are you asking to integrate Anthropic's Batch API into the LLM client so agents use batching automatically when running tasks, or are you asking for a separate feature where users can opt-in to batch processing for their own API calls?**

The distinction matters because:
- **Auto-batching in the agent runtime** = modify `backend/services/llm_client.py` to queue agent requests and submit them as batches when thresholds are met
- **User-facing batch submission** = new API endpoint + frontend UI for users to submit multiple shows/corps tasks as a batch job

Which direction aligns with your intent?

<!-- tags: admin -->
**[program_coordinator]** **Brief update:**

Add to **Constraints** section:
- The Anthropic API client supports batch processing for up to 10,000 requests per batch, with 50% cost savings and up to 24-hour processing windows. This applies best to high-volume, non-blocking workloads where latency tolerance exists.

This clarifies the technical scope — your show should explore where DCI's LLM client can batch off async work (agent runs, design note routing, synthesis, scoring calculations) to reduce API spend and scale throughput without hitting standard rate limits. 

Ready to draft Swarm Prompt language once we confirm: **Should batching prioritize cost reduction, throughput scaling, or both equally?**

Sources:
- [Batch processing - Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/batch-processing)
- [Create a Message Batch - Claude API Reference](https://docs.anthropic.com/en/api/creating-message-batches)
- [Introducing the Message Batches API](https://www.anthropic.com/news/message-batches-api)
<!-- tags: admin -->

**[user]** I want the former, because batching is supposed to be more cost-and-token efficient. In essence, introduce the batch concept to the root LLM agent. For all derived child agents such as AnthropicAPI, use batching if the feature is available, and if it makes sense in the current context.

<!-- tags: admin -->
**[program_coordinator]** I need to update the Brief with concrete implementation scope before drafting Swarm Prompt language.

**Brief Update — Add this to the Constraints section:**

```markdown
## Constraints

- The Anthropic Batch API supports up to 10,000 requests per batch with 50% cost savings and up to 24-hour processing windows.
- **Batching Strategy**: Integrate batching at the `AnthropicLLMClient` level in `backend/services/llm_client.py`. For all agent requests (synthesis, design note routing, scoring calculations, agent runs), queue requests and submit as batches when: (1) threshold count is reached (e.g., 50+ requests), (2) time window expires (e.g., 5 minutes), or (3) explicit submission signal is sent. Non-blocking workloads (async synthesis, background scoring) prioritize cost reduction; interactive workloads (design room responses, real-time agent decisions) must remain low-latency and may skip batching.
- Failed batch jobs must be retryable without data loss; async results must map correctly back to original request contexts.
- Cost savings and latency impact must be measurable and dashboard-visible.
```

**One clarifying question before implementation:**

**When a batched request fails or times out during the 24-hour window, should the system: (A) retry the entire batch, (B) retry individual failed requests immediately outside the batch, or (C) surface the failure to the user for manual retry?**

This determines the error-recovery architecture and affects which workloads are safe to batch.
<!-- tags: admin -->

**[user]** Backlog should be able to switch between cost reduction, throughput, or performance based on user preference. We can file that away as a future improvement, for now I just want to focus on the batch functionality. For the batch jobs, I'm not sure - coordinate with your other agents to suggest something. If a batch job fails, retry 3 times with progressive backoff, and if that still fails then fall back to the standard one-prompt-at-a-time mode

<!-- tags: admin -->
**[program_coordinator]** **Brief Update — Add to Constraints section:**

```markdown
## Error Recovery & Fallback Strategy

- When a batch job fails: retry up to 3 times with progressive backoff (1s, 2s, 4s), then fall back to standard one-prompt-at-a-time mode for remaining requests in that batch
- Cost-reduction vs. throughput vs. performance trade-offs are deferred to backlog (future improvement: user-configurable preference)
- Current focus: batch functionality integration only
```

**Ready to draft Swarm Prompt language.** Brief is now concrete: batching strategy defined, error recovery specified, scope locked. Ready for agents to implement.
