<!-- tags: questions -->

**[user]** #program_coordinator We are redesigning the TMUX dashboard from a 4-pane layout to a 2-pane layout with 8 switchable screens. The Brief is ready. Key architecture decision: should the interactive key handling use Python select/poll for non-blocking stdin, or should we use curses? The current code uses a simple time.sleep loop. We need non-blocking input to support action keys per screen. What is your recommendation for the input handling approach, and do you see any risks in the 8-screen design?

<!-- tags: questions -->
**[program_coordinator]** I'm reading the Brief and architecture now. Let me make a technical recommendation directly:

**Input Handling:** Use **Python `select`/`poll` on stdin** — not curses. Here's why:
- Curses resets terminal state on exit (risky in TMUX panes), adds complexity for a simple key dispatcher
- `select.poll()` on stdin is non-blocking, lightweight, integrates seamlessly with existing `time.sleep()` refresh cycles
- You keep raw terminal control (important for TMUX compatibility)
- Each screen defines its own action key map; poll just reads and dispatches

**Risk in 8-screen design:** One architectural gap — **Screen 4 (On Tour) has a hard 8-second timeout with caching.** This creates a race: if an agent starts executing *just before* the 8s window closes, the UI shows stale status. Recommend adding a **cache invalidation trigger** (`Ctrl+R` to force refresh) so ops can unblock without waiting for the next cycle.

**Brief update needed in Section 3 (Interactive Actions):**
> Add a line: *"Screens support instant refresh via Ctrl+R (forces agent tree/logs/changes to re-fetch). Destructive actions (approve/publish, go_on_tour, etc.) show a confirm prompt with Y/N keys."*

This handles the timeout edge case and gives ops agency. Ready to proceed with this approach?
