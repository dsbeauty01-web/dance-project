#!/bin/bash
# MAYA BOOT — separate from Nova's boot.sh on purpose (standing rule 1: do not touch Nova's files).
# Engine loads maya_idle directly: RESOLUTION LAW forbids mixing nova_* (1076x1924) and
# maya_* (1080x1920) in one stream session, and booting nova then swapping would do exactly that.
#
# REWRITTEN 2026-08-06 after the fresh-pod boot failed silently twice:
#  - A fresh container has NO pip packages. The engine died on `No module named flask`
#    with nothing on the console, and the boot "completed". Deps are now installed here.
#    (--ignore-installed blinker: pip otherwise refuses to replace the distutils copy.)
#  - Boot order was bridge -> engine. The engine took 25 min to first load; the bridge's
#    LiveKit connection died in that window and it CRASHED the moment the engine finally
#    connected (PublishTrackError: engine is closed). Order is now ENGINE FIRST, bridge
#    only after the engine port answers. The engine retries the bridge connect harmlessly.
#  - Everything runs in tmux (LAW-PODS-7: setsid boots die with sshd teardown).
#  - The switchboard (maya-server, :8000) is now part of boot, not a manual afterthought.
LOG=/root/maya-boot.log; exec >>"$LOG" 2>&1
echo "===== MAYA BOOT $(date -u) ====="
export PYTHONPATH=/workspace/_sys/pylibs311_good/dist-packages
[ -f /root/nova.env ] || grep -E "^export " /workspace/boot.sh > /root/nova.env
set -a; . /root/nova.env; set +a
export LK_ROOM=maya-live  # ROOM LAW: Maya NEVER broadcasts into Nova's room (collision found 2026-08-06)

# deps a fresh container is missing (idempotent, ~40s when already present)
which ffmpeg >/dev/null 2>&1 || { apt-get update -qq; apt-get install -y -qq ffmpeg; }
which tmux  >/dev/null 2>&1 || apt-get install -y -qq tmux
python3 -c "import flask" 2>/dev/null || pip install -q --ignore-installed blinker flask flask-sock python-dotenv edge_tts websockets aiortc av
python3 -c "import fastapi" 2>/dev/null || pip install -q fastapi "uvicorn[standard]"

RUNSVC='export PYTHONPATH=/workspace/_sys/pylibs311_good/dist-packages && set -a && . /root/nova.env && set +a'

# 1. ENGINE first (the long cold load; up to 25 min on a fresh container)
tmux new-session -d -s mayaengine "$RUNSVC && cd /workspace/LiveTalking && python3 -u app.py --transport livekit --model musetalk --avatar_id maya_idle --max_session 1 --batch_size 8 --listenport 8010 >> /root/app.log 2>&1"
for i in $(seq 1 200); do c=$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8010/ 2>/dev/null); [ -n "$c" ] && [ "$c" != "000" ] && { echo "ENGINE_UP $c"; break; }; sleep 8; done

# 2. BRIDGE once the engine can connect to it immediately
tmux new-session -d -s mayabridge "$RUNSVC && cd /workspace && python3 -u lk_bridge.py >> /root/bridge.log 2>&1"
for i in $(seq 1 30); do python3 -c "import socket;s=socket.socket();s.settimeout(2);s.connect(('127.0.0.1',9999));s.close()" 2>/dev/null && { echo BRIDGE_UP; break; }; sleep 3; done

# 3. BRAIN
tmux new-session -d -s mayabrain "$RUNSVC && python3 -u /workspace/maya_rt.py >> /root/mayart.log 2>&1"
for i in $(seq 1 40); do c=$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/ 2>/dev/null); [ "$c" = "200" ] && { echo MAYA_BRAIN_UP; break; }; sleep 4; done

# 4. SWITCHBOARD
tmux new-session -d -s mayaserver "$RUNSVC && cd /workspace/maya-server && MAYA_BRAIN=http://127.0.0.1:8765 python3 -u app.py > /root/maya-server.log 2>&1"
for i in $(seq 1 20); do c=$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health 2>/dev/null); [ "$c" = "200" ] && { echo SWITCHBOARD_UP; break; }; sleep 3; done

echo "===== MAYA BOOT DONE $(date -u) 8010=$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8010/) 8765=$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/) 8000=$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health) ====="
