#!/bin/bash
# bring up the MuseTalk avatar engine (app.py) + re-bridge, so Nova's face shows. rt_lk already runs.
exec >>/root/avatar.log 2>&1
echo "===== AVATAR START $(date -u) ====="
export DEBIAN_FRONTEND=noninteractive
export PYTHONPATH=/workspace/_sys/pylibs311_good/dist-packages
export LIVEKIT_URL="wss://novadance-1a7u3xfz.livekit.cloud"
export LIVEKIT_API_KEY="APIfmdVn6S68j4o"
export LIVEKIT_API_SECRET="PVfUjrXMfk7aCEf4U44o3dZrt9pWwROFbmSampyQIe4B"
export LK_ROOM="nova-live"
export LK_BRIDGE_HOST="127.0.0.1"; export LK_BRIDGE_PORT="9999"
export OPENAI_API_KEY="$(sed -n 's/^export OPENAI_API_KEY=\"\(.*\)\"/\1/p' /workspace/boot.sh)"
export ENGINE_URL="http://127.0.0.1:8010"; export RT_MODEL="gpt-realtime"
which ffmpeg >/dev/null 2>&1 || { apt-get update -qq; apt-get install -y -qq ffmpeg; }
cd /workspace/LiveTalking
pkill -9 -f "app.py --transport" 2>/dev/null; sleep 1
setsid nohup python -u app.py --transport livekit --model musetalk --avatar_id nova_idle --max_session 1 --batch_size 8 --listenport 8010 >/root/app.log 2>&1 </dev/null &
echo "app.py launched, waiting for :8010 (MuseTalk model load)..."
for i in $(seq 1 160); do c=$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8010/ 2>/dev/null); [ "$c" != "000" ] && [ -n "$c" ] && { echo "APP_UP $c after $((i*5))s"; break; }; sleep 5; done
# re-bridge now that app.py feeds frames (avoid LiveKit idle-timeout)
pkill -9 -f lk_bridge.py; sleep 2; cd /workspace
setsid nohup python -u lk_bridge.py >/root/bridge.log 2>&1 </dev/null &
sleep 3
echo "===== AVATAR DONE app8010=$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8010/) bridge=$(pgrep -f lk_bridge.py|head -1) ====="
