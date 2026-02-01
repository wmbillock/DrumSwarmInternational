# Swarm Prompt: TMUX Control Panel

## Objective
Rewrite the DCI Swarm TMUX monitoring dashboard from a 4-pane layout to a 2-pane layout with 8 interactive switchable screens.

## Context
All files are under scripts/monitoring/ in the project root. The project root is the working directory. The backend API runs on port 8000 at /api/v1/.

## Tasks (in order)

### Task 1: Rewrite start_monitor.sh
File: scripts/monitoring/start_monitor.sh

Change the TMUX layout from 4 panes to 2 panes:
- Pane 0 (left, 60%): Claude Code workspace (unchanged)
- Pane 1 (right, 40%): Unified Control Panel running unified_dashboard.py
- REMOVE panes 2 and 3 (BE log tail and FE log tail) -- logs are now Screen 6 inside the dashboard
- Update keybindings:
  - prefix+1 through prefix+8 write screen names to the view file
  - Screen names: overview, design, corps, tour, scoring, logs, git, system
  - Keep prefix+0 for Claude Code pane, prefix+d for dashboard pane
  - REMOVE prefix+l and prefix+; (no more separate log panes)
  - Keep prefix+s for swarm menu
- Update pane titles: pane 0 = Claude Code, pane 1 = Control Panel [1-8]
- Fix view selector race condition: use atomic write (echo to temp file, then mv)
- All other tmux config (status bar, border styles, session management) stays the same

### Task 2: Rewrite unified_dashboard.py
File: scripts/monitoring/unified_dashboard.py

This is the major rewrite. Replace the current 6 views with 8 screens. Keep the existing code structure (ANSI colors, fetch(), clear(), main loop) but add:

A) Update VIEWS list and tab bar:
VIEWS = ["overview", "design", "corps", "tour", "scoring", "logs", "git", "system"]
Update render_tab_bar() to show all 8.

B) Non-blocking input handling:
- Put terminal in raw mode (tty.setraw + termios) at startup, restore on exit
- In the main loop, use select.select([sys.stdin], [], [], refresh_interval) instead of time.sleep()
- If a key is pressed, dispatch to the current screen action handler
- Global keys: 1-8 switch screens, Ctrl+R force refresh, q quit
- Each screen defines an actions dict mapping key chars to callables

C) Response caching:
_cache = {}  # {url: {data: ..., time: float}}
CACHE_TTL = 30  # seconds
def fetch(path, timeout=8): try live fetch, on success update cache, on failure return cached if within TTL, else None
Change default timeout from 3s to 8s.

D) Screen implementations:

1. render_overview() -- Combine current render_metrics() with system health data from /api/v1/system/health. Show: BE/FE status, active_corps count, shows by status, any warnings. Keep command quick-ref at bottom.

2. render_design() -- Fetch shows from /api/v1/shows. Display table: slug, title, status, has_spec, has_prompt. Highlight current selection with > marker. Action keys:
   - j/k: move selection
   - a: approve selected show (POST /api/v1/design/threads/{slug}/approve)
   - p: publish selected show (POST /api/v1/design/threads/{slug}/publish)
   - Enter: show detail for selected show

3. render_corps() -- Fetch corps from /api/v1/corps. Display table: name, status, mode, agent count. Highlight current selection. Action keys:
   - j/k: move selection
   - t: go_on_tour (POST /api/v1/corps/{id}/command with go_on_tour)
   - c: return_to_camps
   - r: ready-for-contest
   - Show confirm prompt for destructive actions

4. render_tour() -- Current render_agents() logic but enhanced:
   - Fetch system health for corps summaries
   - For each on_tour corps: show agent tree, rep counts
   - Use 8s timeout, fall back to cache
   - No action keys needed (read-only monitoring)

5. render_scoring() -- Fetch competitions from /api/v1/competitions. Show competition ID, corps involved, scores if available. Fetch season standings if a season exists.

6. render_logs() -- Read both backend.log and frontend.log, merge by timestamp:
   - Parse timestamps from log lines
   - Tag each line with [BE] or [FE] prefix
   - Show last 50 lines by default
   - Action keys for filtering:
     - e: toggle ERROR lines
     - w: toggle WARNING lines
     - i: toggle INFO lines
     - b: toggle backend lines
     - f: toggle frontend lines
   - Track filter state in module-level dict

7. render_git() -- Current render_changes() logic (git status, recent commits, completed reps). No changes needed except renaming.

8. render_system() -- Merge current render_memory() and render_lifecycle():
   - Memory stats per agent
   - LLM usage from /api/v1/system/llm-usage
   - Lifecycle/ageouts
   - Self-improvement pending items

E) Action execution helper:
def execute_action(label, cmd_or_url, method="POST", confirm=False):
    if confirm: show Are you sure? [y/N] at bottom, read key, abort if not y
    if cmd_or_url starts with /: API call via urllib POST
    else: shell command via subprocess
    Show result briefly

F) Selection state:
Maintain per-screen selection index for screens that have lists (design, corps). Reset on screen switch.

### Task 3: Fix status_line.sh
File: scripts/monitoring/status_line.sh

The corps count is wrong. Currently counts active shows, should count corps.
Change to fetch /api/v1/system/health and read active_corps field.
Also update the view indicator to show screen name from the 8-screen list.

### Task 4: Update swarm_actions.sh
File: scripts/monitoring/swarm_actions.sh

Add new actions: show-list, show-approve, show-publish, corps-tour, corps-camps, competition-run.
Update action_help() to document 8 screens (prefix+1..8) and new actions.

### Task 5: Delete deprecated scripts
Delete: log_dashboard.py, metrics_dashboard.py, agent_dashboard.py, changes_dashboard.py

### Task 6: Update dci CLI help
File: dci (project root)
In cmd_horns_up(), update TMUX Hotkeys section for 8 screens, remove prefix+l and prefix+; references.

## Testing
1. python3 scripts/monitoring/unified_dashboard.py --once --view overview (no errors)
2. python3 scripts/monitoring/unified_dashboard.py --once --view design (show list)
3. python3 scripts/monitoring/unified_dashboard.py --once --view logs (merged logs)
4. bash scripts/monitoring/status_line.sh (correct corps count)
5. start_monitor.sh has only 1 split-window call (2 panes)

## Do NOT
- Do not change any backend Python code (backend/ directory)
- Do not change any frontend code (frontend/ directory)
- Do not modify the database or migrations
- Do not add new Python dependencies (use only stdlib)
- Do not change the tmux session name or the ./dci ten-hut flow
