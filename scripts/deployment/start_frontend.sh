#!/usr/bin/env bash
# DCI Swarm — Start frontend with hot-reload
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

cd "$FRONTEND_DIR"
echo "Starting DCI Swarm frontend..."
npm run dev
