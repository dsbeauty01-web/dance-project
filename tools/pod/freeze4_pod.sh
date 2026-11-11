#!/bin/bash
# tools/pod/freeze4_pod.sh — the ONE-SHOT proof pod for FREEZE v4 (b0.27, docs/FREEZE4-SOULX-FACE.md).
# Runs as the pod's start command on Maya's SoulX image (ghcr.io/dsbeauty01-web/maya-lt:soulx-wide-v2 — the image
# Maya's v1 live booted SoulX from; no network volume, nothing of Maya's is changed). It:
#   1. arms a self-stop (FREEZE4_WATCH_MIN, default 50) and serves ONLY /root/out on :8099 (results, no keys)
#   2. installs Chrome + Xvfb + PulseAudio + python deps, clones THIS branch sparsely, deploys the freeze4 page set
#   3. starts the brain (pod/rt_lk.py) with NOVA_FACE_SOULX=1, LK_ROOM=nova-freeze4 (its own LiveKit room)
#   4. B: opens the page BEFORE the face exists → the red banner
#   5. starts tools/pod/nova_face.py (SoulX → LiveKit `nova-face`), waits for READY
#   6. A: the full game, recorded with sound;  C: the face stream paused mid-game → the panel goes red
#   7. writes /root/out/DONE and waits to be terminated
# Keys come in as pod env (OPENAI_API_KEY, LIVEKIT_*); this script never echoes them. No `set -x`.
OUT=/root/out; mkdir -p $OUT
exec >>$OUT/boot.log 2>&1
echo "===== FREEZE4 POD $(date -u) pod=${RUNPOD_POD_ID:-?} ====="
stage(){ echo "STAGE $(date -u +%H:%M:%S) $*"; echo "$(date -u +%H:%M:%S) $*" >> $OUT/STAGES; }

# 1) self-stop + results server
WATCH=${FREEZE4_WATCH_MIN:-50}
( sleep $((WATCH*60)); echo "WATCHDOG fired after ${WATCH} min" >> $OUT/STAGES
  runpodctl remove pod "$RUNPOD_POD_ID" 2>/dev/null \
  || curl -s -X DELETE "https://rest.runpod.io/v1/pods/$RUNPOD_POD_ID" -H "Authorization: Bearer $RUNPOD_API_KEY" ) >/dev/null 2>&1 &
( cd $OUT && nohup python3 -m http.server 8099 >/dev/null 2>&1 & )
stage "boot (watchdog ${WATCH} min)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader >> $OUT/STAGES 2>&1

PY=${PY:-/opt/ltenv/bin/python}
[ -x "$PY" ] || PY=python3
export SOULX_ROOT=${SOULX_ROOT:-/opt/soulxroot}
# Maya's renderer: /opt/maya-ops/lt on soulx-wide-v2, /opt/maya/repo/maya-ops/lt on the golden images
MO=/opt/maya-ops/lt; [ -f $MO/flashhead_renderer.py ] || MO=/opt/maya/repo/maya-ops/lt
export FACE_RENDERER_DIR=$MO; echo "renderer dir $MO $(ls $MO/flashhead_renderer.py 2>&1)" >> $OUT/STAGES

# 2a) SoulX weights: baked into the image when it was built with BAKE_WEIGHTS=1; else fetch (Dockerfile.soulx: ~3 min)
( if [ -s "$SOULX_ROOT/ACTIVATE.sh" ] && [ -d "$SOULX_ROOT/models/SoulX-FlashHead-1_3B" ]; then echo "weights baked" > $OUT/weights.txt
  else echo "weights NOT baked - fetching" > $OUT/weights.txt; timeout 1200 $PY $MO/soulx_fetch.py --root "$SOULX_ROOT" --jobs 4 >> $OUT/weights.txt 2>&1; echo "fetch exit $?" >> $OUT/weights.txt; fi ) &
WPID=$!

# 2b) system packages + Chrome (H.264 for Nova's body clips) + python deps
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get install -y -qq xvfb pulseaudio git wget ca-certificates >/dev/null 2>&1; stage "apt done $?"
wget -q -O /root/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && apt-get install -y -qq /root/chrome.deb >/dev/null 2>&1
stage "chrome: $(google-chrome --version 2>&1)"
$PY -m pip install -q --no-cache-dir livekit livekit-api aiohttp playwright >/dev/null 2>&1; stage "pip done $? ($($PY -c 'import livekit.rtc,livekit.api,aiohttp,playwright;print("ok")' 2>&1 | tail -1))"
ffmpeg -hide_banner -devices 2>/dev/null | grep -E "x11grab|pulse" | tr -s ' ' >> $OUT/STAGES

# 2c) this branch, sparse (no media we do not use)
BR=${FREEZE4_BRANCH:-nova-freeze-v4}
git clone -q --depth 1 --filter=blob:none --no-checkout -b "$BR" https://github.com/dsbeauty01-web/dance-project /root/repo \
 && cd /root/repo && git sparse-checkout set --no-cone '/beta/*.html' '/beta/*.css' '/beta/*.js' '/beta/lib/' '/beta/freeze2/' '/shared/' \
      '/freezegame/' '/audio/freeze2/' '/test/clips/' '/pod/' '/tools/pod/' && git checkout -q "$BR"
stage "repo $(cd /root/repo && git rev-parse --short HEAD)"
R=/root/repo; P=/workspace/pages
mkdir -p $P/beta $P/test /workspace/audio
cp $R/beta/freeze4.html $R/beta/play.css $P/beta/ && cp -r $R/beta/lib $R/beta/freeze2 $P/beta/ && cp -r $R/shared $P/shared \
 && cp -r $R/freezegame $P/freezegame && cp -r $R/audio/freeze2 /workspace/audio/freeze2 && cp -r $R/test/clips $P/test/clips \
 && cp $R/pod/rt_lk.py /workspace/rt_lk.py
stage "deployed $? ($(ls $P/freezegame | wc -l) freezegame files)"

# 3) the brain — its own room, the face engine on :8010
cd /workspace
LK_ROOM=nova-freeze4 ENGINE_URL=http://127.0.0.1:8010 NOVA_FACE_SOULX=1 NOVA_TEST_CLIPS=1 \
  setsid nohup $PY -u rt_lk.py > $OUT/rtlk.log 2>&1 < /dev/null &
for i in $(seq 1 40); do c=$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/health); [ "$c" = "200" ] && break; sleep 2; done
stage "brain :8765 health=$c page=$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/beta/freeze4)"

# virtual screen + sound card for the recording
Xvfb :99 -screen 0 1280x720x24 -nolisten tcp >/dev/null 2>&1 &
export DISPLAY=:99
pulseaudio -D --exit-idle-time=-1 --system=false --disallow-exit >/dev/null 2>&1 || pulseaudio -D --system --exit-idle-time=-1 --disallow-exit >/dev/null 2>&1
sleep 2; pactl load-module module-null-sink sink_name=rec >/dev/null 2>&1; pactl set-default-sink rec >/dev/null 2>&1
stage "screen+sound: $(pactl info 2>&1 | grep -i 'default sink' )"
ffmpeg -loglevel error -y -f lavfi -i anullsrc=r=48000:cl=mono -t 10 /root/silence.wav

export OUT
# 4) B — no face yet → red banner
cd /root/repo/tools/pod && timeout 120 $PY freeze4_proof.py B > $OUT/B.log 2>&1; stage "B exit $?"

# 5) the face
wait $WPID; stage "weights: $(head -1 $OUT/weights.txt)"
[ -s "$SOULX_ROOT/ACTIVATE.sh" ] && . "$SOULX_ROOT/ACTIVATE.sh"
cd /root/repo/tools/pod
FACE_RENDERER=flashhead LK_ROOM=nova-freeze4 FACE_OUT=$OUT/face FACE_RECORD=1 FACE_TEST_HOOKS=1 \
  setsid nohup $PY -u nova_face.py > $OUT/face.log 2>&1 < /dev/null &
for i in $(seq 1 180); do c=$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8010/); [ "$c" = "200" ] && break; sleep 5; done
sleep 4; curl -s -m4 http://127.0.0.1:8010/ > $OUT/face_ready.json
stage "face :8010 http=$c $(cut -c1-160 $OUT/face_ready.json)"

# 6) A — the deliverable;  C — stream lost mid-game
timeout 420 $PY freeze4_proof.py A > $OUT/A.log 2>&1; stage "A exit $?"
curl -s -m6 http://127.0.0.1:8010/ > $OUT/face_after_A.json
timeout 180 $PY freeze4_proof.py C > $OUT/C.log 2>&1; stage "C exit $?"
curl -s -m30 -X POST http://127.0.0.1:8010/finish > $OUT/face_finish.json
curl -s -m6 http://127.0.0.1:8010/ > $OUT/face_final.json
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader >> $OUT/STAGES 2>&1
cp $OUT/rtlk.log $OUT/rtlk_copy.log 2>/dev/null
stage "DONE"; touch $OUT/DONE
sleep infinity
