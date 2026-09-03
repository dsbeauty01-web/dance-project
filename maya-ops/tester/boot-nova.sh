#!/usr/bin/env bash
# maya-ops/tester/boot-nova.sh — ONE-TAP boot for the kids' tester window.
# STARTS the persistent tester pod (fixed id, so the locked URL always knows it),
# boots the Nova stack, and arms a self-stop at the end of the window.
# The tester URL never changes — pod-registry.js already points at this pod.
#
#   bash maya-ops/tester/boot-nova.sh          # 3h window (16:30 -> 19:30 Israel)
#   bash maya-ops/tester/boot-nova.sh 5400     # custom self-stop seconds
#
# Run from a phone by SSH-ing to this PC (Termux / a-Shell / Blink / iOS Shortcut),
# or straight from the RunPod mobile console: pod "nova-tester" -> Start.
set -uo pipefail
POD="ahpn3b9rl1tqrl"                        # persistent nova-tester pod
WINDOW="${1:-10800}"                         # default 3h
KEY="${RUNPOD_API_KEY:-$(powershell.exe -NoProfile -Command '[Environment]::GetEnvironmentVariable("RUNPOD_API_KEY","User")' 2>/dev/null | tr -d '\r')}"
[ -n "$KEY" ] || { echo "!! no RUNPOD_API_KEY"; exit 1; }

echo ">> starting pod $POD ..."
curl -s -X POST "https://rest.runpod.io/v1/pods/$POD/start" -H "Authorization: Bearer $KEY" -o /dev/null -w "   start: %{http_code}\n" \
  || { echo "!! start failed (host may be at capacity — try again in a few min)"; exit 2; }

echo ">> waiting for SSH ..."
IP=""; PORT=""
for i in $(seq 1 30); do
  D=$(curl -s "https://rest.runpod.io/v1/pods/$POD" -H "Authorization: Bearer $KEY")
  IP=$(echo "$D" | grep -oE '"publicIp":"[^"]+"' | cut -d'"' -f4)
  PORT=$(echo "$D" | grep -oE '"22":[0-9]+' | grep -oE '[0-9]+$')
  [ -n "$IP" ] && [ -n "$PORT" ] && break; sleep 10
done
[ -n "$IP" ] && [ -n "$PORT" ] || { echo "!! no SSH endpoint (pod may still be provisioning; the URL will wake when /health answers)"; exit 3; }

SSH="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=20 -i $HOME/.ssh/id_ed25519 -p $PORT root@$IP"
for i in $(seq 1 12); do $SSH 'echo up' 2>/dev/null | grep -q up && break; sleep 8; done
$SSH "command -v tmux >/dev/null 2>&1 || { apt-get update -qq; apt-get install -y -qq tmux; } >/dev/null 2>&1;
  tmux kill-session -t selfstop 2>/dev/null;
  tmux new-session -d -s selfstop \"sleep $WINDOW; runpodctl stop pod $POD 2>/dev/null || curl -s -X POST https://rest.runpod.io/v1/pods/$POD/stop -H 'Authorization: Bearer $KEY'\";
  tmux kill-session -t novaboot 2>/dev/null;
  tmux new-session -d -s novaboot 'bash /workspace/boot.sh >/root/boot.console 2>&1'; echo BOOTING" 2>/dev/null

echo ""
echo "════════════════════════════════════════════════════════"
echo " nova-tester is booting (self-stops in $((WINDOW/3600))h). /health answers in ~2-5 min."
echo " The tester URL wakes automatically — nothing else to do:"
echo " EN: https://dsbeauty01-web.github.io/dance-project/nova-commercial.html?game=freeze"
echo " HE: https://dsbeauty01-web.github.io/dance-project/nova-commercial.html?game=freeze&lang=he"
echo "════════════════════════════════════════════════════════"
