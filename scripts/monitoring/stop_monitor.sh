#!/usr/bin/env bash
# DCI Swarm — Stop monitoring dashboard

set -euo pipefail

SESSION_NAME="${DCI_SESSION:-dci-swarm}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux kill-session -t "$SESSION_NAME"
    echo -e "${GREEN}[INFO]${NC}  Session '$SESSION_NAME' terminated."
else
    echo -e "${YELLOW}[WARN]${NC}  Session '$SESSION_NAME' is not running."
fi
