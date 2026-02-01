Perfect! I've updated the TMUX Control Panel spec with all the design decisions from the conversation. Here's what changed:

## Summary of Updates

✅ **Restructured as Full DCI Show Spec** with all mandatory sections:
- **Show Concept** — High-level goal and context
- **Musical Design** — Eight "movements" corresponding to screens
- **Visual Design** — Layout, navigation keys, status bar details
- **Guard Design** — Technical architecture for input handling and caching
- **General Effect** — Operational impact and UX transformation
- **Constraints** — 10 specific non-negotiable requirements
- **Deliverables** — Detailed checklist with acceptance criteria
- **Swarm Prompt** — Synthesized actionable prompt for the swarm

## Key Design Decisions Incorporated

1. **Input Handling**: Explicitly specifies `select.poll()` (not curses) for non-blocking stdin reading, with justification (TMUX compatibility, terminal state safety)

2. **Cache Invalidation**: Documents the 8-second timeout strategy with:
   - Last-good fallback on timeout
   - Clear "stale data" UI message
   - **Ctrl+R force refresh** to handle the race condition where agents start just before timeout window closes

3. **Confirmation Prompts**: Specifies Y/N destructive action confirmation (not single-key) for safety

4. **All 8 Screens**: Complete specification with action keys, filters, and dependencies

The spec is now ready for the drum-corps-director agent to implement this show end-to-end.