#!/usr/bin/env bash
# tools/pod/launch_pod.sh — the ONE canonical way to bring up a live/test Nova pod.
# POD LAW (see LAWS.md): Secure Cloud only for live/test; Community = bakes only.
# Every launch arms the suicide-timer and boots ONCE, detached, then HANDS OFF.
#
# Usage:  RUNPOD_API_KEY=... bash tools/pod/launch_pod.sh
#
# POD-LAW: Secure Cloud only — live/test pods must be SECURE, never Community.
set -euo pipefail

API="${RUNPOD_API_KEY:?set RUNPOD_API_KEY}"
VOLUME_ID="${NOVA_VOLUME_ID:-1ditrne6cb}"     # nova-groove-vol
DC="${NOVA_DC:-EU-RO-1}"                       # must match the volume's datacenter
GPU="${NOVA_GPU:-NVIDIA GeForce RTX 4090}"
IMAGE="${NOVA_IMAGE:-runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04}"

# --- POD LAW #1: Secure Cloud flag for the live launch (Community = bakes only) ---
CLOUD_TYPE='"cloudType": "SECURE"'

echo ">> creating SECURE 4090 pod in $DC on volume $VOLUME_ID ..."
resp=$(curl -s -X POST "https://rest.runpod.io/v1/pods" \
  -H "Authorization: Bearer $API" -H "Content-Type: application/json" \
  -d "{
    ${CLOUD_TYPE},
    \"gpuTypeIds\": [\"${GPU}\"],
    \"gpuCount\": 1,
    \"networkVolumeId\": \"${VOLUME_ID}\",
    \"dataCenterIds\": [\"${DC}\"],
    \"imageName\": \"${IMAGE}\",
    \"containerDiskInGb\": 40,
    \"volumeMountPath\": \"/workspace\",
    \"ports\": [\"8765/http\", \"22/tcp\"],
    \"name\": \"nova-live-fresh\",
    \"interruptible\": false
  }")
POD_ID=$(echo "$resp" | grep -oE '"id":"[^"]+"' | head -1 | cut -d'"' -f4)
echo ">> pod: $POD_ID"
[ -n "$POD_ID" ] || { echo "CREATE FAILED: $resp"; exit 1; }

# Wait for the direct-SSH endpoint (Secure Cloud exposes 22/tcp via portMappings).
echo ">> waiting for SSH ..."
for i in $(seq 1 20); do
  d=$(curl -s "https://rest.runpod.io/v1/pods/$POD_ID" -H "Authorization: Bearer $API")
  IP=$(echo "$d" | grep -oE '"publicIp":"[^"]+"' | cut -d'"' -f4)
  PORT=$(echo "$d" | grep -oE '"22":[0-9]+' | grep -oE '[0-9]+$')
  [ -n "$IP" ] && [ -n "$PORT" ] && break
  sleep 8
done
echo ">> ssh root@$IP -p $PORT"

# --- POD LAW #2: the suicide-timer, armed in the launch. 6h backstop. ---
# String is intentionally literal & greppable (law-pods.js asserts it):
#   nohup sleep 6h; runpodctl stop pod $RUNPOD_POD_ID
SUICIDE='( nohup sleep 6h; runpodctl stop pod $RUNPOD_POD_ID ) &'

SSH="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=20 -i $HOME/.ssh/id_ed25519 -p $PORT root@$IP"
for i in $(seq 1 12); do $SSH 'echo up' 2>/dev/null | grep -q up && break; sleep 8; done

# Arm suicide-timer (with an API-curl fallback in case runpodctl is absent), then
# boot ONCE, detached, logged. POD LAW #3: NO pkill for >=3 min after this.
$SSH "bash -lc '
  ( nohup sleep 6h && ( runpodctl stop pod ${POD_ID} 2>/dev/null || curl -s -X POST https://rest.runpod.io/v1/pods/${POD_ID}/stop -H \"Authorization: Bearer ${API}\" ) ) >/root/suicide.log 2>&1 &
  cd /workspace && setsid bash /workspace/boot.sh </dev/null >/root/boot.console 2>&1 & disown
'"
echo ">> BOOT LAUNCHED — HANDS OFF for 12 minutes (silent-import window). POD_ID=$POD_ID IP=$IP PORT=$PORT"
