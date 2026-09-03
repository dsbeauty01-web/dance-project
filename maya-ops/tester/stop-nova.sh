#!/usr/bin/env bash
# maya-ops/tester/stop-nova.sh — stop any running nova-tester pod now.
set -uo pipefail
KEY="${RUNPOD_API_KEY:-$(powershell.exe -NoProfile -Command '[Environment]::GetEnvironmentVariable("RUNPOD_API_KEY","User")' 2>/dev/null | tr -d '\r')}"
[ -n "$KEY" ] || { echo "no RUNPOD_API_KEY"; exit 1; }
IDS=$(curl -s "https://rest.runpod.io/v1/pods" -H "Authorization: Bearer $KEY" \
  | tr '{' '\n' | grep -i 'nova-tester' | grep -oE '"id":"[^"]+"' | cut -d'"' -f4)
[ -n "$IDS" ] || { echo "no nova-tester pod running"; exit 0; }
for id in $IDS; do
  curl -s -X POST "https://rest.runpod.io/v1/pods/$id/stop" -H "Authorization: Bearer $KEY" -o /dev/null -w "stopped $id: %{http_code}\n"
done
