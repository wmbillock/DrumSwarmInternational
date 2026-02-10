#!/usr/bin/env bash
# DCI Swarm System Heartbeat — designed to be called by cron.
#
# Pings the swarm API heartbeat endpoint, which wakes the DCI head (admin ED),
# all admin/logistics agents, and the executive director for each active corps.
#
# Install with:
#   crontab -e
#   # Every 5 minutes:
#   */5 * * * * /path/to/dci-swarm/scripts/heartbeat_cron.sh >> /tmp/dci-heartbeat.log 2>&1
#
# Adjust DCI_API_URL if the server runs on a different host/port.

DCI_API_URL="${DCI_API_URL:-http://localhost:4224}"

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

response=$(curl -sf -X POST "${DCI_API_URL}/api/v1/heartbeat" \
    -H "Content-Type: application/json" \
    -w "\n%{http_code}" \
    --max-time 30 2>&1)

http_code=$(echo "$response" | tail -1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo "${TIMESTAMP} OK: ${body}"
else
    echo "${TIMESTAMP} FAILED (HTTP ${http_code}): ${body}" >&2
    exit 1
fi
