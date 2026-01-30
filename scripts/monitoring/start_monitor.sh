#!/usr/bin/env bash
# DCI Swarm — TMUX Monitoring Dashboard
#
# Layout:
# ┌──────────────────────────────┬─────────────────────────┐
# │                              │ [1:Metrics] [2:Agents]  │
# │  Claude Code                 │ [3:Logs]   [4:Changes]  │
# │  (large workspace)           │                         │
# │                              │  (switchable right pane)│
# │                              │                         │
# └──────────────────────────────┴─────────────────────────┘
# Switch views: prefix+1/2/3/4

set -euo pipefail

SESSION_NAME="${DCI_SESSION:-dci-swarm}"
PROJECT_ROOT="${DCI_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
VENV_DIR="$PROJECT_ROOT/.venv"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$PROJECT_ROOT/backend.log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[dci]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[dci]${NC} $1"; }
log_error() { echo -e "${RED}[dci]${NC} $1"; }

check_dependencies() {
    if ! command -v tmux &>/dev/null; then
        log_error "tmux is not installed. Install with: brew install tmux"
        exit 1
    fi
}

session_exists() {
    tmux has-session -t "$SESSION_NAME" 2>/dev/null
}

kill_existing_session() {
    if session_exists; then
        log_warn "Killing existing session '$SESSION_NAME'"
        tmux kill-session -t "$SESSION_NAME"
    fi
}

venv_prefix() {
    if [ -f "$VENV_DIR/bin/activate" ]; then
        echo "source '$VENV_DIR/bin/activate' && "
    fi
}

create_session() {
    log_info "Setting the field — creating monitoring dashboard..."

    local VP
    VP="$(venv_prefix)"

    local VIEW_FILE="$PROJECT_ROOT/.dci-dashboard-view"

    # Create session with pane 0 (Claude Code workspace — left, large)
    tmux new-session -d -s "$SESSION_NAME" -c "$PROJECT_ROOT" -x 220 -y 55
    tmux rename-window -t "$SESSION_NAME:0" "monitor"

    # Split: right pane (single unified dashboard)
    tmux split-window -h -t "$SESSION_NAME:0.0" -c "$PROJECT_ROOT" -p 40

    # --- Pane 0: Claude Code workspace (left, large) ---
    tmux send-keys -t "$SESSION_NAME:0.0" "cd '$PROJECT_ROOT' && clear" C-m
    if command -v claude &>/dev/null; then
        tmux send-keys -t "$SESSION_NAME:0.0" "claude" C-m
    fi

    # --- Pane 1: Unified Dashboard (right) ---
    echo "metrics" > "$VIEW_FILE"
    tmux send-keys -t "$SESSION_NAME:0.1" "${VP}python3 '$SCRIPT_DIR/unified_dashboard.py' --refresh 3" C-m

    # Pane titles
    tmux set-option -t "$SESSION_NAME" pane-border-status top
    tmux set-option -t "$SESSION_NAME" pane-border-format " #[bold]#{pane_title} "
    tmux set-option -t "$SESSION_NAME" pane-border-style "fg=colour240"
    tmux set-option -t "$SESSION_NAME" pane-active-border-style "fg=colour75"

    tmux select-pane -t "$SESSION_NAME:0.0" -T "Claude Code"
    tmux select-pane -t "$SESSION_NAME:0.1" -T "Dashboard [1:Metrics 2:Agents 3:Logs 4:Changes]"

    # Keybindings: switch dashboard views by writing to the view file
    tmux bind-key -T prefix 1 run-shell "echo metrics > '$VIEW_FILE'"
    tmux bind-key -T prefix 2 run-shell "echo agents > '$VIEW_FILE'"
    tmux bind-key -T prefix 3 run-shell "echo logs > '$VIEW_FILE'"
    tmux bind-key -T prefix 4 run-shell "echo changes > '$VIEW_FILE'"

    # prefix+d to toggle focus to dashboard pane
    tmux bind-key -T prefix d select-pane -t "$SESSION_NAME:0.1"
    # prefix+0 to return focus to Claude Code
    tmux bind-key -T prefix 0 select-pane -t "$SESSION_NAME:0.0"

    # Focus Claude Code pane
    tmux select-pane -t "$SESSION_NAME:0.0"

    log_info "Dashboard is set. Attaching..."
}

attach_session() {
    if [ -n "${TMUX:-}" ]; then
        tmux switch-client -t "$SESSION_NAME"
    else
        tmux attach-session -t "$SESSION_NAME"
    fi
}

# --- Main ---

check_dependencies

case "${1:-start}" in
    start)
        kill_existing_session
        create_session
        attach_session
        ;;
    stop)
        kill_existing_session
        log_info "Dashboard dismissed."
        ;;
    restart)
        kill_existing_session
        create_session
        attach_session
        ;;
    status)
        if session_exists; then
            log_info "Session '$SESSION_NAME' is on the field."
            tmux list-panes -t "$SESSION_NAME" -F "  #{pane_index}: #{pane_title} (#{pane_width}x#{pane_height})" 2>/dev/null
        else
            log_warn "Session '$SESSION_NAME' is at rest."
        fi
        ;;
    attach)
        if session_exists; then
            attach_session
        else
            log_error "No session running. Use: ./dci mark-time"
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|attach}"
        exit 1
        ;;
esac
