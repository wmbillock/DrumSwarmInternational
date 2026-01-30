#!/usr/bin/env bash
# DCI Swarm — TMUX Monitoring Dashboard
# Creates a 2x2 grid layout for real-time swarm monitoring
#
# Layout:
# ┌──────────────────────────┬──────────────────────────┐
# │ Pane 0: CLI              │ Pane 1: Backend Logs     │
# │ • Shell prompt           │ • Real-time log tailing  │
# │ • Manual commands        │ • API server output      │
# ├──────────────────────────┼──────────────────────────┤
# │ Pane 2: Agent Status     │ Pane 3: Corps Watcher    │
# │ • task_watcher.py        │ • corps activity feed    │
# │ • Real-time agent stats  │ • rep/score monitoring   │
# └──────────────────────────┴──────────────────────────┘

set -euo pipefail

# --- Configuration ---
SESSION_NAME="${DCI_SESSION:-dci-swarm}"
PROJECT_ROOT="${DCI_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
BACKEND_DIR="$PROJECT_ROOT/backend"
LOG_FILE="${DCI_LOG:-$PROJECT_ROOT/backend.log}"
VENV_DIR="$PROJECT_ROOT/.venv"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Dependency Checks ---
check_dependencies() {
    if ! command -v tmux &>/dev/null; then
        log_error "tmux is not installed. Install with: brew install tmux"
        exit 1
    fi

    local version
    version=$(tmux -V | grep -oE '[0-9]+\.[0-9]+')
    local major
    major=$(echo "$version" | cut -d. -f1)

    if [[ "$major" -lt 3 ]]; then
        log_error "tmux version $version not supported. Minimum: 3.0"
        exit 1
    fi

    log_info "tmux version $version OK"
}

# --- Session Management ---
session_exists() {
    tmux has-session -t "$SESSION_NAME" 2>/dev/null
}

kill_existing_session() {
    if session_exists; then
        log_warn "Killing existing session '$SESSION_NAME'"
        tmux kill-session -t "$SESSION_NAME"
    fi
}

create_session() {
    log_info "Creating DCI Swarm monitoring dashboard..."

    # Create session with first pane (CLI)
    tmux new-session -d -s "$SESSION_NAME" -c "$PROJECT_ROOT" -x 160 -y 40
    tmux rename-window -t "$SESSION_NAME:0" "monitor"

    # Split: create right pane (pane 1 = logs)
    tmux split-window -h -t "$SESSION_NAME:0" -c "$PROJECT_ROOT"

    # Split left pane vertically (pane 2 = agent status)
    tmux split-window -v -t "$SESSION_NAME:0.0" -c "$PROJECT_ROOT"

    # Split right pane vertically (pane 3 = corps watcher)
    tmux split-window -v -t "$SESSION_NAME:0.1" -c "$PROJECT_ROOT"

    # --- Initialize Panes ---

    # Pane 0: CLI (top-left)
    tmux send-keys -t "$SESSION_NAME:0.0" "cd '$PROJECT_ROOT' && clear" C-m
    tmux send-keys -t "$SESSION_NAME:0.0" "echo ''" C-m
    tmux send-keys -t "$SESSION_NAME:0.0" "echo '  ╔══════════════════════════════════════╗'" C-m
    tmux send-keys -t "$SESSION_NAME:0.0" "echo '  ║         DCI SWARM - CLI              ║'" C-m
    tmux send-keys -t "$SESSION_NAME:0.0" "echo '  ╠══════════════════════════════════════╣'" C-m
    tmux send-keys -t "$SESSION_NAME:0.0" "echo '  ║  Project: $PROJECT_ROOT'" C-m
    tmux send-keys -t "$SESSION_NAME:0.0" "echo '  ║  Backend: http://localhost:8000      ║'" C-m
    tmux send-keys -t "$SESSION_NAME:0.0" "echo '  ║  Frontend: http://localhost:5173     ║'" C-m
    tmux send-keys -t "$SESSION_NAME:0.0" "echo '  ╚══════════════════════════════════════╝'" C-m
    tmux send-keys -t "$SESSION_NAME:0.0" "echo ''" C-m

    # Pane 1: Backend logs (top-right)
    tmux send-keys -t "$SESSION_NAME:0.1" "cd '$PROJECT_ROOT'" C-m
    tmux send-keys -t "$SESSION_NAME:0.1" "echo 'Tailing backend logs...'" C-m
    if [ -f "$VENV_DIR/bin/activate" ]; then
        tmux send-keys -t "$SESSION_NAME:0.1" "source '$VENV_DIR/bin/activate' && uvicorn backend.api.app:app --host 0.0.0.0 --port 8000 --reload 2>&1 | tee '$LOG_FILE'" C-m
    else
        tmux send-keys -t "$SESSION_NAME:0.1" "touch '$LOG_FILE' && tail -f '$LOG_FILE'" C-m
    fi

    # Pane 2: Agent status (bottom-left)
    if [ -f "$SCRIPT_DIR/task_watcher.py" ]; then
        tmux send-keys -t "$SESSION_NAME:0.2" "cd '$PROJECT_ROOT'" C-m
        if [ -f "$VENV_DIR/bin/activate" ]; then
            tmux send-keys -t "$SESSION_NAME:0.2" "source '$VENV_DIR/bin/activate' && python3 '$SCRIPT_DIR/task_watcher.py' --refresh 2" C-m
        else
            tmux send-keys -t "$SESSION_NAME:0.2" "python3 '$SCRIPT_DIR/task_watcher.py' --refresh 2" C-m
        fi
    else
        tmux send-keys -t "$SESSION_NAME:0.2" "watch -n 2 'curl -s http://localhost:8000/api/shows 2>/dev/null | python3 -m json.tool 2>/dev/null || echo \"Backend not available\"'" C-m
    fi

    # Pane 3: Corps watcher (bottom-right)
    if [ -f "$SCRIPT_DIR/corps_watcher.py" ]; then
        tmux send-keys -t "$SESSION_NAME:0.3" "cd '$PROJECT_ROOT'" C-m
        if [ -f "$VENV_DIR/bin/activate" ]; then
            tmux send-keys -t "$SESSION_NAME:0.3" "source '$VENV_DIR/bin/activate' && python3 '$SCRIPT_DIR/corps_watcher.py' --refresh 3" C-m
        else
            tmux send-keys -t "$SESSION_NAME:0.3" "python3 '$SCRIPT_DIR/corps_watcher.py' --refresh 3" C-m
        fi
    else
        tmux send-keys -t "$SESSION_NAME:0.3" "watch -n 3 'echo \"Corps Activity Feed\" && echo \"==================\" && curl -s http://localhost:8000/api/shows 2>/dev/null | python3 -m json.tool 2>/dev/null || echo \"Waiting for backend...\"'" C-m
    fi

    # Set pane border labels
    tmux set-option -t "$SESSION_NAME" pane-border-status top
    tmux set-option -t "$SESSION_NAME" pane-border-format " #{pane_index}: #{pane_title} "

    tmux select-pane -t "$SESSION_NAME:0.0" -T "CLI"
    tmux select-pane -t "$SESSION_NAME:0.1" -T "Backend Logs"
    tmux select-pane -t "$SESSION_NAME:0.2" -T "Agent Status"
    tmux select-pane -t "$SESSION_NAME:0.3" -T "Corps Watcher"

    # Focus CLI pane
    tmux select-pane -t "$SESSION_NAME:0.0"

    log_info "Dashboard created successfully"
}

attach_session() {
    if [ -n "${TMUX:-}" ]; then
        tmux switch-client -t "$SESSION_NAME"
    else
        tmux attach-session -t "$SESSION_NAME"
    fi
}

show_session_info() {
    echo ""
    log_info "Session: $SESSION_NAME"
    log_info "Panes:"
    tmux list-panes -t "$SESSION_NAME" -F "  #{pane_index}: #{pane_title} (#{pane_width}x#{pane_height})" 2>/dev/null || true
    echo ""
}

# --- Main ---
main() {
    check_dependencies

    case "${1:-start}" in
        start)
            kill_existing_session
            create_session
            show_session_info
            attach_session
            ;;
        stop)
            kill_existing_session
            log_info "Session stopped."
            ;;
        restart)
            kill_existing_session
            create_session
            show_session_info
            attach_session
            ;;
        status)
            if session_exists; then
                log_info "Session '$SESSION_NAME' is running."
                show_session_info
            else
                log_warn "Session '$SESSION_NAME' is not running."
            fi
            ;;
        attach)
            if session_exists; then
                attach_session
            else
                log_error "Session '$SESSION_NAME' is not running. Start it first."
                exit 1
            fi
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status|attach}"
            exit 1
            ;;
    esac
}

main "$@"
