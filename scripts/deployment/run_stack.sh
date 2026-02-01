#!/usr/bin/env bash
# DCI Swarm — Start full stack (backend + frontend)
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
BACKEND_PORT="${DCI_PORT:-8000}"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

cleanup() {
    echo ""
    echo "Shutting down..."
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM

# Kill existing
lsof -ti:"$BACKEND_PORT" | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

# Start backend
cd "$PROJECT_ROOT"
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
fi

uvicorn backend.api.app:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload \
    > "$PROJECT_ROOT/backend.log" 2>&1 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID) on port $BACKEND_PORT"

# Wait for backend
for i in $(seq 1 10); do
    if curl -s "http://localhost:$BACKEND_PORT/api/v1/shows" >/dev/null 2>&1; then
        echo "Backend is ready."
        break
    fi
    sleep 1
done

# Start frontend
cd "$FRONTEND_DIR"
npm run dev > "$PROJECT_ROOT/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID) on port 5173"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║         DCI SWARM — RUNNING          ║"
echo "╠══════════════════════════════════════╣"
echo "║  Backend:  http://localhost:$BACKEND_PORT      ║"
echo "║  Frontend: http://localhost:5173     ║"
echo "║  Logs:     backend.log, frontend.log ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "Press Ctrl+C to stop."

wait
