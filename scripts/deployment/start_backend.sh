#!/usr/bin/env bash
# DCI Swarm — Start backend with hot-reload
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
PORT="${DCI_PORT:-4224}"

# Kill existing backend on port
lsof -ti:"$PORT" | xargs kill -9 2>/dev/null || true

# Activate venv
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
fi

cd "$PROJECT_ROOT"
echo "Starting DCI Swarm backend on port $PORT..."
uvicorn backend.api.app:app --host 0.0.0.0 --port "$PORT" --reload
