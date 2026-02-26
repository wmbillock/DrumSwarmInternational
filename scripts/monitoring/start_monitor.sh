#!/usr/bin/env bash
# DCI Swarm — TMUX Monitoring Dashboard
#
# Layout:
# ┌──────────────────────────────┬─────────────────────────┐
# │                              │  Dashboard (switchable)  │
# │  Claude Code                 ├─────────────────────────┤
# │  (large workspace)           │  Backend log (tail)      │
# │                              ├─────────────────────────┤
# │                              │  Frontend log (tail)     │
# └──────────────────────────────┴─────────────────────────┘
#   Status bar: BE:ON FE:ON │ N corps │ prefix+s: menu
#
# Switch dashboard views: prefix+1..6
# Swarm menu: prefix+s (popup)
# Navigation: prefix+0=Claude, prefix+d=dashboard, prefix+l=BE log, prefix+;=FE log

set -euo pipefail

SESSION_NAME="${DCI_SESSION:-dci-swarm}"
PROJECT_ROOT="${DCI_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
VENV_DIR="$PROJECT_ROOT/.venv"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$PROJECT_ROOT/backend.log"
FE_LOG_FILE="$PROJECT_ROOT/frontend.log"
INSTANCE_ID="${DSI_INSTANCE_ID:-$SESSION_NAME}"

# Detect tmux base-index settings (user may configure these to start at 1)
_W=$(tmux show-options -gv base-index 2>/dev/null || echo 0)
_P=$(tmux show-options -gwv pane-base-index 2>/dev/null || echo 0)

# Pane target shortcuts: SESSION:WINDOW.PANE
WIN="$SESSION_NAME:$_W"
T0="$SESSION_NAME:$_W.$_P"
T1="$SESSION_NAME:$_W.$((_P + 1))"
T2="$SESSION_NAME:$_W.$((_P + 2))"
T3="$SESSION_NAME:$_W.$((_P + 3))"

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
    local ACTIONS="$SCRIPT_DIR/swarm_actions.sh"
    local STATUS_LINE="$SCRIPT_DIR/status_line.sh"

    # Create session with pane 0 (Claude Code workspace — left, large)
    tmux new-session -d -s "$SESSION_NAME" -c "$PROJECT_ROOT" -x 220 -y 55
    tmux rename-window -t "$WIN" "monitor"
    tmux set-environment -t "$SESSION_NAME" DSI_INSTANCE_ID "$INSTANCE_ID"

    # Split: right column (40%)
    tmux split-window -h -t "$T0" -c "$PROJECT_ROOT" -p 40

    # Split right column into 3: dashboard (top 60%), BE log (mid 20%), FE log (bottom 20%)
    tmux split-window -v -t "$T1" -c "$PROJECT_ROOT" -p 40
    tmux split-window -v -t "$T2" -c "$PROJECT_ROOT" -p 50

    # --- Pane 0: Claude Code workspace (left, large) ---
    tmux send-keys -t "$T0" "cd '$PROJECT_ROOT' && clear" C-m
    if command -v claude &>/dev/null; then
        tmux send-keys -t "$T0" "claude" C-m
    fi

    # --- Pane 1: Unified Dashboard (top right) ---
    echo "metrics" > "$VIEW_FILE"
    tmux send-keys -t "$T1" "${VP}python3 '$SCRIPT_DIR/unified_dashboard.py' --refresh 3" C-m

    # --- Pane 2: Backend log (mid right) ---
    tmux send-keys -t "$T2" "touch '$LOG_FILE' && tail -f '$LOG_FILE'" C-m

    # --- Pane 3: Frontend log (bottom right) ---
    tmux send-keys -t "$T3" "touch '$FE_LOG_FILE' && tail -f '$FE_LOG_FILE'" C-m

    # Pane titles
    tmux set-option -t "$SESSION_NAME" pane-border-status top
    tmux set-option -t "$SESSION_NAME" pane-border-format " #[bold]#{pane_title} "
    tmux set-option -t "$SESSION_NAME" pane-border-style "fg=colour240"
    tmux set-option -t "$SESSION_NAME" pane-active-border-style "fg=colour75"

    tmux select-pane -t "$T0" -T "Claude Code"
    tmux select-pane -t "$T1" -T "Dashboard [1-6]"
    tmux select-pane -t "$T2" -T "Backend Log"
    tmux select-pane -t "$T3" -T "Frontend Log"

    # ─── Dashboard view keybindings (prefix+1..6) ────────────────────
    tmux bind-key -T prefix 1 run-shell "echo metrics > '$VIEW_FILE'"
    tmux bind-key -T prefix 2 run-shell "echo agents > '$VIEW_FILE'"
    tmux bind-key -T prefix 3 run-shell "echo logs > '$VIEW_FILE'"
    tmux bind-key -T prefix 4 run-shell "echo changes > '$VIEW_FILE'"
    tmux bind-key -T prefix 5 run-shell "echo memory > '$VIEW_FILE'"
    tmux bind-key -T prefix 6 run-shell "echo lifecycle > '$VIEW_FILE'"

    # ─── Navigation keybindings ──────────────────────────────────────
    tmux bind-key -T prefix 0 select-pane -t "$T0"
    tmux bind-key -T prefix d select-pane -t "$T1"
    tmux bind-key -T prefix l select-pane -t "$T2"
    tmux bind-key -T prefix '\;' select-pane -t "$T3"

    # ─── Swarm menu (prefix+s) — display-menu popup ─────────────────
    tmux bind-key -T prefix s display-menu -T "#[bold]DCI Swarm" \
        "Resume Hut (restart BE+FE)"  r "display-popup -E -w 60 -h 20 '$ACTIONS resume-hut'" \
        "Heartbeat"                   h "display-popup -E -w 60 -h 12 '$ACTIONS heartbeat'" \
        "Run-Through (tests)"         t "display-popup -E -w 80 -h 30 '$ACTIONS run-tests'" \
        "Restart Backend"             b "display-popup -E -w 60 -h 12 '$ACTIONS restart-backend'" \
        "Restart Frontend"            f "display-popup -E -w 60 -h 12 '$ACTIONS restart-frontend'" \
        "Run Migration"               m "display-popup -E -w 60 -h 12 '$ACTIONS migrate'" \
        "Drill"                       d "display-popup -E -w 60 -h 15 '$ACTIONS drill'" \
        "Check Step (status)"         c "display-popup -E -w 60 -h 20 '$ACTIONS check-step'" \
        "Parade Rest (stop all)"      p "display-popup -E -w 60 -h 12 '$ACTIONS parade-rest'" \
        "" \
        "Open Browser"                o "run-shell '$ACTIONS open-browser'" \
        "Help"                        ? "display-popup -E -w 65 -h 30 '$ACTIONS help'"

    # ─── Status bar ──────────────────────────────────────────────────
    tmux set-option -t "$SESSION_NAME" status on
    tmux set-option -t "$SESSION_NAME" status-style "bg=colour235,fg=colour248"
    tmux set-option -t "$SESSION_NAME" status-left "#[bold,fg=colour75] DCI SWARM #[default]│ "
    tmux set-option -t "$SESSION_NAME" status-left-length 20
    tmux set-option -t "$SESSION_NAME" status-right "#(bash '$STATUS_LINE') │ %H:%M"
    tmux set-option -t "$SESSION_NAME" status-right-length 80
    tmux set-option -t "$SESSION_NAME" status-interval 5

    # Focus Claude Code pane
    tmux select-pane -t "$T0"

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
