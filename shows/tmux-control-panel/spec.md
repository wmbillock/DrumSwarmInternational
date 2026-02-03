# TMUX Control Panel

## Goal
Rewrite the DCI Swarm TMUX monitoring dashboard from 4-pane to 2-pane layout with 8 interactive switchable screens.

## Acceptance Criteria
1. start_monitor.sh creates 2 panes: Pane 0 (left 60%) Claude Code, Pane 1 (right 40%) unified dashboard
2. prefix+1 through prefix+8 switch between 8 screens: overview, design, corps, tour, scoring, logs, git, system
3. unified_dashboard.py rewritten with 8 screens, non-blocking input handling via select.select()
4. Response caching with 30s TTL and fallback to cached data on timeout
5. Design screen: show list with j/k selection, a=approve, p=publish, Enter=detail
6. Corps screen: corps list with j/k selection, t=go_on_tour, c=return_to_camps, r=ready-for-contest
7. Logs screen: merged BE+FE logs with filter toggles (e/w/i/b/f keys)
8. Destructive actions require Y/N confirmation
9. status_line.sh shows correct corps count from /api/v1/system/health
10. Deprecated scripts deleted: log_dashboard.py, metrics_dashboard.py, agent_dashboard.py, changes_dashboard.py
11. dci CLI help updated for 8-screen layout

## Constraints
- No backend Python changes
- No frontend changes
- No new Python dependencies (stdlib only)
- No database or migration changes
- Atomic view file writes (temp + mv)
- 8-second default timeout for API calls