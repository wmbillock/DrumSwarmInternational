#!/usr/bin/env bash
# DCI Swarm — Popup action scripts for tmux hotkeys
# Called by tmux bind-key via display-popup or run-shell

set -euo pipefail

PROJECT_ROOT="${DCI_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
VENV_DIR="$PROJECT_ROOT/.venv"
BACKEND_PORT="${DCI_PORT:-8000}"
API_BASE="http://localhost:$BACKEND_PORT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

_venv() {
    [ -f "$VENV_DIR/bin/activate" ] && source "$VENV_DIR/bin/activate"
}

_kill_port() {
    lsof -ti:"$1" 2>/dev/null | xargs kill -9 2>/dev/null || true
}

_api() {
    curl -s -X "$1" "$API_BASE$2" -H "Content-Type: application/json" ${3:+-d "$3"} 2>/dev/null
}

# ─── Actions ──────────────────────────────────────────────────────────

action_resume_hut() {
    echo -e "${BOLD}RESUME — HUT!${NC}"
    echo ""
    _kill_port "$BACKEND_PORT"
    _kill_port 5173
    sleep 1

    # Use tmux run-shell to launch outside the popup's PTY so processes survive popup close
    tmux run-shell -b "cd '$PROJECT_ROOT' && source '$VENV_DIR/bin/activate' 2>/dev/null; uvicorn backend.api.app:app --host 0.0.0.0 --port $BACKEND_PORT --reload > '$PROJECT_ROOT/backend.log' 2>&1 &"
    echo -e "${GREEN}Backend restarting (port $BACKEND_PORT)${NC}"

    tmux run-shell -b "cd '$PROJECT_ROOT/frontend' && npx vite > '$PROJECT_ROOT/frontend.log' 2>&1 &"
    echo -e "${GREEN}Frontend restarting (port 5173)${NC}"

    # Wait for backend
    for i in $(seq 1 10); do
        if curl -s "$API_BASE/api/v1/shows" >/dev/null 2>&1; then
            echo -e "${GREEN}Backend is set${NC}"
            break
        fi
        sleep 1
    done
    echo ""
    echo -e "${GREEN}Services resumed.${NC} Press any key..."
    read -n 1
}

action_heartbeat() {
    echo -e "${BOLD}HEARTBEAT${NC}"
    echo ""
    result=$(_api POST /api/v1/heartbeat)
    if [ -n "$result" ]; then
        echo "$result" | python3 -m json.tool 2>/dev/null || echo "$result"
    else
        echo -e "${RED}Backend unreachable${NC}"
    fi
    echo ""
    echo "Press any key..."
    read -n 1
}

action_run_tests() {
    echo -e "${BOLD}RUN-THROUGH${NC}"
    echo ""
    _venv
    cd "$PROJECT_ROOT"
    python -m pytest backend/tests/ -v --tb=short 2>&1
    echo ""
    echo "Press any key..."
    read -n 1
}

action_restart_backend() {
    echo -e "${BOLD}Restarting Backend${NC}"
    _kill_port "$BACKEND_PORT"
    sleep 1
    tmux run-shell -b "cd '$PROJECT_ROOT' && source '$VENV_DIR/bin/activate' 2>/dev/null; uvicorn backend.api.app:app --host 0.0.0.0 --port $BACKEND_PORT --reload > '$PROJECT_ROOT/backend.log' 2>&1 &"
    echo -e "${GREEN}Backend restarting${NC}"
    sleep 2
    if curl -s "$API_BASE/api/v1/shows" >/dev/null 2>&1; then
        echo -e "${GREEN}Backend is set${NC}"
    else
        echo -e "${YELLOW}Backend still starting...${NC}"
    fi
    echo "Press any key..."
    read -n 1
}

action_restart_frontend() {
    echo -e "${BOLD}Restarting Frontend${NC}"
    _kill_port 5173
    sleep 1
    tmux run-shell -b "cd '$PROJECT_ROOT/frontend' && npx vite > '$PROJECT_ROOT/frontend.log' 2>&1 &"
    echo -e "${GREEN}Frontend restarting${NC}"
    echo "Press any key..."
    read -n 1
}

action_migrate() {
    echo -e "${BOLD}Running Migrations${NC}"
    echo ""
    _venv
    cd "$PROJECT_ROOT"
    alembic upgrade head 2>&1
    echo ""
    echo -e "${GREEN}Migration complete${NC}"
    echo "Press any key..."
    read -n 1
}

action_drill() {
    echo -e "${BOLD}DRILL${NC}"
    echo ""
    echo -n "Problem number (or args): "
    read -r args
    if [ -z "$args" ]; then
        echo "Cancelled."
        sleep 1
        return
    fi
    _venv
    cd "$PROJECT_ROOT"
    python -m backend.cli.drill -p $args 2>&1
    echo ""
    echo "Press any key..."
    read -n 1
}

action_check_step() {
    echo -e "${BOLD}CHECK STEP${NC}"
    echo ""

    if curl -s "$API_BASE/api/v1/shows" >/dev/null 2>&1; then
        echo -e "  Backend:   ${GREEN}ON${NC}  (port $BACKEND_PORT)"
    else
        echo -e "  Backend:   ${RED}OFF${NC}"
    fi

    if curl -s "http://localhost:5173" >/dev/null 2>&1; then
        echo -e "  Frontend:  ${GREEN}ON${NC}  (port 5173)"
    else
        echo -e "  Frontend:  ${RED}OFF${NC}"
    fi

    if tmux has-session -t "${DCI_SESSION:-dci-swarm}" 2>/dev/null; then
        echo -e "  Dashboard: ${GREEN}ON${NC}"
    else
        echo -e "  Dashboard: ${RED}OFF${NC}"
    fi

    echo ""
    # Show counts
    shows=$(_api GET /api/v1/shows 2>/dev/null)
    if [ -n "$shows" ]; then
        total=$(echo "$shows" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "?")
        echo -e "  Shows: ${CYAN}$total${NC}"
    fi

    agents=$(_api GET /api/v1/system/agents 2>/dev/null)
    if [ -n "$agents" ]; then
        count=$(echo "$agents" | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(1 for a in d if a.get('status')=='active'))" 2>/dev/null || echo "?")
        echo -e "  Active agents: ${GREEN}$count${NC}"
    fi

    echo ""
    echo "Press any key..."
    read -n 1
}

action_parade_rest() {
    echo -e "${BOLD}${RED}PARADE REST${NC}"
    echo ""
    echo -n "Stop all services? [y/N] "
    read -r confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "Cancelled."
        sleep 1
        return
    fi
    _kill_port "$BACKEND_PORT"
    _kill_port 5173
    echo -e "${GREEN}Services stopped.${NC}"
    echo "Press any key..."
    read -n 1
}

action_open_browser() {
    open "http://localhost:5173" 2>/dev/null || xdg-open "http://localhost:5173" 2>/dev/null || echo "Cannot open browser"
}

action_help() {
    echo -e "${BOLD}DCI SWARM — TMUX HOTKEYS${NC}"
    echo ""
    echo -e "${BOLD}Swarm Menu (prefix+s):${NC}"
    echo -e "  ${GREEN}r${NC}  Resume Hut — restart BE+FE"
    echo -e "  ${GREEN}h${NC}  Heartbeat — ping the swarm"
    echo -e "  ${GREEN}t${NC}  Run-Through — run tests"
    echo -e "  ${GREEN}b${NC}  Restart backend only"
    echo -e "  ${GREEN}f${NC}  Restart frontend only"
    echo -e "  ${GREEN}m${NC}  Run migration"
    echo -e "  ${GREEN}d${NC}  Drill — run calibration"
    echo -e "  ${GREEN}c${NC}  Check Step — service status"
    echo -e "  ${GREEN}p${NC}  Parade Rest — stop all"
    echo -e "  ${GREEN}o${NC}  Open browser"
    echo ""
    echo -e "${BOLD}Dashboard Views (prefix+N):${NC}"
    echo -e "  ${CYAN}1${NC} Metrics  ${CYAN}2${NC} Agents  ${CYAN}3${NC} Logs"
    echo -e "  ${CYAN}4${NC} Changes  ${CYAN}5${NC} Memory  ${CYAN}6${NC} Lifecycle"
    echo ""
    echo -e "${BOLD}Navigation:${NC}"
    echo -e "  ${CYAN}prefix+0${NC}  Claude Code"
    echo -e "  ${CYAN}prefix+d${NC}  Dashboard"
    echo -e "  ${CYAN}prefix+l${NC}  Backend log"
    echo -e "  ${CYAN}prefix+;${NC}  Frontend log"
    echo ""
    echo "Press any key..."
    read -n 1
}

# ─── Dispatch ─────────────────────────────────────────────────────────

case "${1:-help}" in
    resume-hut|r)       action_resume_hut ;;
    heartbeat|h)        action_heartbeat ;;
    run-tests|t)        action_run_tests ;;
    restart-backend|b)  action_restart_backend ;;
    restart-frontend|f) action_restart_frontend ;;
    migrate|m)          action_migrate ;;
    drill|d)            action_drill ;;
    check-step|c)       action_check_step ;;
    parade-rest|p)      action_parade_rest ;;
    open-browser|o)     action_open_browser ;;
    help|"?")           action_help ;;
    *)                  echo "Unknown action: $1"; exit 1 ;;
esac
