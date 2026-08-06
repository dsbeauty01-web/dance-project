#!/bin/bash
# tools/pod/boot.sh — canonical one-shot revival of the whole Nova stack.
# engine (app.py :8010) + bridge (:9999 -> LiveKit) + brain (rt_lk :8765). Idempotent.
# This is the SOURCE OF TRUTH; the pod pulls it (POD-LAW: git-pull first) so a
# fresh pod always boots the latest committed code, never a stale volume copy.
#
# POD LAW (LAWS.md):
#   - Boot ONCE, detached, logged.
#   - NO-PKILL-WINDOW: after this script launches a service, DO NOT pkill it for
#     at least 3 minutes. Imports are silent for 20-40s; a kill during load is the
#     "engine hangs at 394MB" bug. Wait, read the log, THEN act.
#   - LAW-PODS-9-COLDLOAD: silence < 15min = loading, not dead. FIRST boot on a
#     fresh container streams multi-GB torch/CUDA off the network volume — silent,
#     no logs, no GPU activity, up to 25 min. No process intervention before min 15.
#     Verify progress READ-ONLY: this boot.log grows OR nvidia-smi memory climbs.
#   - LAW-PODS-8-BRACKET: never an un-bracketed pkill -f pattern (it self-matches and
#     kills the boot). Use the bracket trick: pkill -f "[b]oot.sh" / "[a]pp.py". None here.
LOG=/root/boot.log; exec >>"$LOG" 2>&1
echo "===== BOOT $(date -u) ====="
export DEBIAN_FRONTEND=noninteractive
export PYTHONPATH=/workspace/_sys/pylibs311_good/dist-packages

# 0) POD-LAW: git-pull first — refresh the repo on the pod so boot uses latest code.
#    (repo lives at /workspace/repo on the pod; secrets stay in /workspace/.env, uncommitted)
if [ -d /workspace/repo/.git ]; then
  git -C /workspace/repo pull --ff-only 2>&1 | tail -2 || echo "git pull skipped"
  # sync the live brain from the pulled repo if present
  [ -f /workspace/repo/pod/rt_lk.py ] && cp /workspace/repo/pod/rt_lk.py /workspace/rt_lk.py
fi

# 1) secrets from an uncommitted env file (NEVER hardcode keys in the repo)
[ -f /workspace/.env ] && set -a && . /workspace/.env && set +a

# 2) ffmpeg (apt) — the "no voice" dep
which ffmpeg >/dev/null 2>&1 || { apt-get update -qq; apt-get install -y -qq ffmpeg; }
echo "ffmpeg: $(which ffmpeg)"

# 3) container pip deps (fast wheels only)
python -c "import flask,edge_tts,websockets" 2>/dev/null || \
  pip install --only-binary=:all: --prefer-binary --ignore-installed blinker \
    flask flask-sock python-dotenv edge_tts websockets aiortc av 2>&1 | tail -1

# 4) bridge
cd /workspace
setsid nohup python -u lk_bridge.py >/root/bridge.log 2>&1 </dev/null &
for i in $(seq 1 30); do python -c "import socket;s=socket.socket();s.settimeout(2);s.connect(('127.0.0.1',9999));s.close()" 2>/dev/null && { echo "BRIDGE_UP"; break; }; sleep 3; done

# 5) engine app.py (nova_idle default). NO-PKILL-WINDOW starts here — leave it be
#    while MuseTalk loads (silent 20-40s, then GPU climbs; ~10-15 min cold).
cd /workspace/LiveTalking
setsid nohup python -u app.py --transport livekit --model musetalk --avatar_id nova_idle --max_session 1 --batch_size 8 --listenport 8010 >/root/app.log 2>&1 </dev/null &
for i in $(seq 1 180); do c=$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8010/ 2>/dev/null); [ "$c" != "000" ] && [ -n "$c" ] && { echo "APP_UP $c"; break; }; sleep 5; done

# 6) re-bridge (avoid LiveKit idle-timeout now that app.py feeds frames)
cd /workspace
setsid nohup python -u lk_bridge.py >/root/bridge.log 2>&1 </dev/null &
sleep 4

# 7) brain rt_lk (intro brain: flow + TRUTH-GATE + TURN-GATE + freeze demo)
cd /workspace
setsid nohup python -u rt_lk.py >/root/rtlk.log 2>&1 </dev/null &
for i in $(seq 1 40); do c=$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/ 2>/dev/null); [ "$c" = "200" ] && { echo "BRAIN_UP"; break; }; sleep 4; done

echo "===== BOOT DONE $(date -u) :8765=$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/) ====="
