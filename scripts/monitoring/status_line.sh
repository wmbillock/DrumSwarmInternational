#!/usr/bin/env bash
# DCI Swarm — tmux status line data
# Called by tmux status-right to show live service info

PROJECT_ROOT="${DCI_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
BACKEND_PORT="${DCI_PORT:-8000}"
API_BASE="http://localhost:$BACKEND_PORT"

# Service checks
be="OFF"
fe="OFF"
if curl -s "$API_BASE/api/v1/shows" >/dev/null 2>&1; then
    be="ON"
fi
if curl -s "http://localhost:5173" >/dev/null 2>&1; then
    fe="ON"
fi

# Corps count
corps="?"
if [ "$be" = "ON" ]; then
    corps=$(curl -s "$API_BASE/api/v1/shows" 2>/dev/null | python3 -c "
import json,sys
try:
    shows=json.load(sys.stdin)
    print(sum(1 for s in shows if s.get('status')=='active'))
except: print('?')
" 2>/dev/null || echo "?")
fi

# Current dashboard view
view=$(cat "$PROJECT_ROOT/.dci-dashboard-view" 2>/dev/null || echo "metrics")

# Output for tmux
if [ "$be" = "ON" ]; then
    printf "BE:#[fg=green]ON#[default]"
else
    printf "BE:#[fg=red]OFF#[default]"
fi
printf " "
if [ "$fe" = "ON" ]; then
    printf "FE:#[fg=green]ON#[default]"
else
    printf "FE:#[fg=red]OFF#[default]"
fi
printf " │ %s corps │ [%s] │ prefix+s: menu" "$corps" "$view"
