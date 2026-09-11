#!/bin/bash
# minimal Nova boot for a fresh pod: bridge + brain (rt_lk serves /beta/wave + /token).
# Skips the MuseTalk engine (app.py) so the game+lights come up fast; add the avatar later.
exec >>/root/fb.log 2>&1
echo "===== FB START $(date -u) ====="
export DEBIAN_FRONTEND=noninteractive
export PYTHONPATH=/workspace/_sys/pylibs311_good/dist-packages
export LIVEKIT_URL="wss://novadance-1a7u3xfz.livekit.cloud"
export LIVEKIT_API_KEY="APIfmdVn6S68j4o"
export LIVEKIT_API_SECRET="PVfUjrXMfk7aCEf4U44o3dZrt9pWwROFbmSampyQIe4B"
export LK_ROOM="nova-live"
export LK_BRIDGE_HOST="127.0.0.1"; export LK_BRIDGE_PORT="9999"
export OPENAI_API_KEY="$(sed -n 's/^export OPENAI_API_KEY=\"\(.*\)\"/\1/p' /workspace/boot.sh)"
export ENGINE_URL="http://127.0.0.1:8010"; export RT_MODEL="gpt-realtime"
cd /workspace
pkill -9 -f lk_bridge.py 2>/dev/null; pkill -9 -f rt_lk.py 2>/dev/null; sleep 1
setsid nohup python -u lk_bridge.py >/root/bridge.log 2>&1 </dev/null &
echo "bridge launched, waiting..."
for i in $(seq 1 20); do python -c "import socket;s=socket.socket();s.settimeout(2);s.connect(('127.0.0.1',9999));s.close()" 2>/dev/null && { echo "BRIDGE_UP"; break; }; sleep 3; done
setsid nohup python -u rt_lk.py >/root/rtlk.log 2>&1 </dev/null &
echo "rt_lk launched, waiting for :8765..."
for i in $(seq 1 45); do c=$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/ 2>/dev/null); [ "$c" = "200" ] && { echo "BRAIN_UP"; break; }; sleep 4; done
echo "===== FB DONE local:8765=$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/) ====="
