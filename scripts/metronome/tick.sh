#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT/logs/metronome"
LOCK_FILE="$LOG_DIR/metronome.lock"

mkdir -p "$LOG_DIR"

exec 9>"$LOCK_FILE"
if ! flock -w 300 9; then
  exit 0
fi

python "$ROOT/scripts/metronome/tick.py"
