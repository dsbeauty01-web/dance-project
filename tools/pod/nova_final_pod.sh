#!/bin/bash
# tools/pod/nova_final_pod.sh — the ONE-SHOT proof pod for NOVA-FINAL (2026-11-12, Refael: "Nova: the new skill and full
# switch to Ditto"). Same shape as tools/pod/freeze4_pod.sh (Maya's SoulX image, no network volume, nothing of Maya's is
# changed). It:
#   1. arms a self-stop (NF_WATCH_MIN, default 55) and serves ONLY /root/out on :8099 (results, no keys)
#   2. clones this branch sparsely, starts the Ditto install (prebuilt pack) at once, then Chrome/Xvfb/Pulse + python deps
#   3. Ditto on her Ditto-Gold-gated talk body (tools/pod/assets/nova_talk_wide.mp4, gold_gate body PASS) with the Gold
#      recipe flags; the brain (pod/rt_lk.py, NOVA_FACE_SOULX=1 NOVA_FACE_DUAL=1); the face server FACE_RENDERER=dual
#   4. SPEED: 45 s of the live loop in wide mode (silence) -> Ditto ms per chunk, late chunks, underruns
#   5. W: her real voice (the two arrival lines, EN + HE) through the live face server in wide mode -> the Ditto cut the
#      gold gate reads (exactly the frames + voice that were published, 1080x1920)
#   6. A: the real run — beta/freeze4 in Chrome: intro WIDE (Ditto) -> game start with the PiP SoulX face -> ending WIDE,
#      recorded with sound (x11grab + PulseAudio)
#   7. writes /root/out/DONE and waits to be terminated
# Keys come in as pod env; this script never echoes them. No `set -x`.
OUT=/root/out; mkdir -p $OUT
exec >>$OUT/boot.log 2>&1
echo "===== NOVA-FINAL POD $(date -u) pod=${RUNPOD_POD_ID:-?} ====="
stage(){ echo "STAGE $(date -u +%H:%M:%S) $*"; echo "$(date -u +%H:%M:%S) $*" >> $OUT/STAGES; }

WATCH=${NF_WATCH_MIN:-55}
( sleep $((WATCH*60)); echo "WATCHDOG fired after ${WATCH} min" >> $OUT/STAGES
  runpodctl remove pod "$RUNPOD_POD_ID" 2>/dev/null \
  || curl -s -X DELETE "https://rest.runpod.io/v1/pods/$RUNPOD_POD_ID" -H "Authorization: Bearer $RUNPOD_API_KEY" ) >/dev/null 2>&1 &
( cd $OUT && nohup python3 -m http.server 8099 >/dev/null 2>&1 & )
stage "boot (watchdog ${WATCH} min) nproc=$(nproc) $(cat /sys/fs/cgroup/cpu.max 2>/dev/null)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader >> $OUT/STAGES 2>&1

PY=${PY:-/opt/ltenv/bin/python}; [ -x "$PY" ] || PY=python3
export SOULX_ROOT=${SOULX_ROOT:-/opt/soulxroot}
MO=/opt/maya-ops/lt; [ -f $MO/flashhead_renderer.py ] || MO=/opt/maya/repo/maya-ops/lt
export FACE_RENDERER_DIR=$MO

# 1) this branch, sparse
BR=${NF_BRANCH:-nova-final}
git clone -q --depth 1 --filter=blob:none --no-checkout -b "$BR" https://github.com/dsbeauty01-web/dance-project /root/repo \
 && cd /root/repo && git sparse-checkout set --no-cone '/beta/*.html' '/beta/*.css' '/beta/*.js' '/beta/lib/' '/beta/freeze2/' '/shared/' \
      '/freezegame/' '/audio/freeze2/' '/audio/intro/*.mp4' '/test/clips/' '/pod/' '/tools/pod/' && git checkout -q "$BR"
R=/root/repo; stage "repo $(cd $R && git rev-parse --short HEAD) body $(ls -la $R/tools/pod/assets/nova_talk_wide.mp4 | awk '{print $5}')"

# 2a) Ditto: prebuilt pack (ditto_up.sh DITTO_PACK) — Ditto Gold recipe flags (ditto-lips skill §5.6, Nova values from
#     tools/pod/ditto_take8/nova_take8.env). [CLI-FILL] DITTO_CHUNK=10 / DITTO_TAKE_TIMEOUT=0.35: the co-host's live chunk
#     (ditto_up log 2026-11-10: chunk_frames 10), so the render thread can stay one chunk ahead in 0.4 s steps.
export MAYA_LOGS=$OUT/ditto DITTO_PACK=${DITTO_PACK:-ditto-pack-v2} DITTO_SRC=$R/tools/pod/assets/nova_talk_wide.mp4
export DITTO_AMP=${DITTO_AMP:-0.6} DITTO_GRAIN=0 DITTO_MASK=lower DITTO_PASTE_GATE=1 DITTO_PASTE_OFF_MS=80 DITTO_PASTE_XFADE_MS=120 \
       DITTO_ON_RMS=0.012 DITTO_FAST_CLOSE=1 DITTO_DEBT_FIX=1 DITTO_FAST_PRIME=1 DITTO_PRIME=${DITTO_PRIME:-35} DITTO_CHUNK=${DITTO_CHUNK:-10} \
       DITTO_TAKE_TIMEOUT=${DITTO_TAKE_TIMEOUT:-0.35} DITTO_VAD=1 DITTO_EYE_HOLD=1 DITTO_THREADS=${DITTO_THREADS:-6} DITTO_STATS_EVERY=25
mkdir -p $MAYA_LOGS
( t=$(date +%s); for i in 1 2; do bash $R/tools/pod/ditto_take8/ditto_up.sh > $OUT/ditto_up.log 2>&1 && break; sleep 5; done
  echo "rc=$? after $(( $(date +%s) - t )) s" >> $OUT/ditto_up.log ) &
DPID=$!

# 2b) SoulX weights (baked into the image, else fetch)
( if [ -s "$SOULX_ROOT/ACTIVATE.sh" ] && [ -d "$SOULX_ROOT/models/SoulX-FlashHead-1_3B" ]; then echo "weights baked" > $OUT/weights.txt
  else echo "weights NOT baked - fetching" > $OUT/weights.txt; timeout 1200 $PY $MO/soulx_fetch.py --root "$SOULX_ROOT" --jobs 4 >> $OUT/weights.txt 2>&1; fi ) &
WPID=$!

# 2c) system packages + Chrome + python deps
export DEBIAN_FRONTEND=noninteractive
timeout 400 bash -c 'apt-get update -qq && apt-get install -y -qq xvfb pulseaudio ca-certificates fonts-noto-color-emoji fonts-dejavu-core >/dev/null 2>&1'; stage "apt done $?"
wget -q -O /root/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && timeout 300 apt-get install -y -qq /root/chrome.deb >/dev/null 2>&1
stage "chrome: $(google-chrome --version 2>&1)"
$PY -m pip install -q --no-cache-dir livekit livekit-api aiohttp playwright >/dev/null 2>&1; stage "pip done $? ($($PY -c 'import livekit.rtc,livekit.api,aiohttp,playwright;print("ok")' 2>&1 | tail -1))"

P=/workspace/pages; mkdir -p $P/beta $P/test /workspace/audio
cp $R/beta/freeze4.html $R/beta/play.css $P/beta/ && cp -r $R/beta/lib $R/beta/freeze2 $P/beta/ && cp -r $R/shared $P/shared \
 && cp -r $R/freezegame $P/freezegame && cp -r $R/audio/freeze2 /workspace/audio/freeze2 && cp -r $R/test/clips $P/test/clips \
 && cp $R/pod/rt_lk.py /workspace/rt_lk.py
stage "deployed $?"

# 3) the brain — its own room; the face engine on :8010 (dual)
cd /workspace
LK_ROOM=nova-final ENGINE_URL=http://127.0.0.1:8010 NOVA_FACE_SOULX=1 NOVA_FACE_DUAL=1 NOVA_TEST_CLIPS=1 \
  setsid nohup $PY -u rt_lk.py > $OUT/rtlk.log 2>&1 < /dev/null &
Xvfb :99 -screen 0 1280x720x24 -nolisten tcp >/dev/null 2>&1 &
export DISPLAY=:99
pulseaudio -D --exit-idle-time=-1 --system=false --disallow-exit >/dev/null 2>&1 || pulseaudio -D --system --exit-idle-time=-1 --disallow-exit >/dev/null 2>&1
sleep 2; pactl load-module module-null-sink sink_name=rec >/dev/null 2>&1; pactl set-default-sink rec >/dev/null 2>&1
ffmpeg -loglevel error -y -f lavfi -i anullsrc=r=48000:cl=mono -t 10 /root/silence.wav
# her real voice for W: the two arrival lines (EN, HE) at 16 kHz mono
for l in en he; do f=$R/audio/intro/nova-arrival.mp4; [ $l = he ] && f=$R/audio/intro/nova-arrival-he.mp4
  ffmpeg -loglevel error -y -i $f -vn -ac 1 -ar 16000 /root/line_$l.wav; done
stage "screen+sound+lines: $(ls /root/line_*.wav | wc -l) lines"

wait $DPID; stage "ditto: $(tail -2 $OUT/ditto_up.log | tr '\n' ' ' | cut -c1-300)"
curl -s -m5 http://127.0.0.1:8031/health > $OUT/ditto_health_boot.json
wait $WPID; stage "weights: $(head -1 $OUT/weights.txt)"
[ -s "$SOULX_ROOT/ACTIVATE.sh" ] && . "$SOULX_ROOT/ACTIVATE.sh"
cd $R/tools/pod
FACE_RENDERER=dual FACE_START_MODE=wide LK_ROOM=nova-final FACE_OUT=$OUT/face FACE_RECORD=1 FACE_TEST_HOOKS=1 \
  setsid nohup $PY -u nova_face.py > $OUT/face.log 2>&1 < /dev/null &
for i in $(seq 1 200); do c=$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8010/); [ "$c" = "200" ] && break; sleep 5; done
stage "face :8010 http=$c $(curl -s -m4 http://127.0.0.1:8010/ | cut -c1-200)"

# 4) SPEED — the live loop in wide mode, silence (Ditto's cost does not depend on the words)
curl -s -m60 -X POST "http://127.0.0.1:8010/finish?tag=boot" > /dev/null; sleep 45
curl -s -m5 http://127.0.0.1:8010/ > $OUT/speed_face.json; curl -s -m5 http://127.0.0.1:8031/health > $OUT/speed_ditto.json
top -b -n1 | head -20 > $OUT/speed_top.txt; nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader >> $OUT/speed_top.txt
stage "speed: $(python3 -c "import json;d=json.load(open('$OUT/speed_face.json'));print({k:d.get(k) for k in ('wide_render_ms_p50','wide_render_ms_p95','wide_chunks_late','wide_chunks','underruns')})")"

# 5) W — her real voice through the live face server, wide (Ditto) — the cut for the gold gate
curl -s -m60 -X POST "http://127.0.0.1:8010/finish?tag=speed" > /dev/null
python3 - <<'PYW' >> $OUT/W.log 2>&1
import time, wave, urllib.request
def post(f):
    b = open(f, "rb").read(); bnd = "NFW"
    d = (f"--{bnd}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.wav\"\r\nContent-Type: audio/wav\r\n\r\n").encode() + b + f"\r\n--{bnd}--\r\n".encode()
    urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8010/humanaudio", data=d, method="POST",
                           headers={"Content-Type": f"multipart/form-data; boundary={bnd}"}), timeout=20).read()
    w = wave.open(f); return w.getnframes() / w.getframerate()
time.sleep(2)
for f in ["/root/line_en.wav", "/root/line_he.wav", "/root/line_en.wav", "/root/line_he.wav"]:
    d = post(f); print(time.strftime("%H:%M:%S"), "line", f, round(d, 2), flush=True); time.sleep(d + 1.6)
time.sleep(3)
PYW
curl -s -m5 http://127.0.0.1:8010/ > $OUT/W_face.json; curl -s -m5 http://127.0.0.1:8031/health > $OUT/W_ditto.json
curl -s -m120 -X POST "http://127.0.0.1:8010/finish?tag=W" > $OUT/W_finish.json
stage "W: $(cut -c1-200 $OUT/W_finish.json)"

# 6) A — the real run in Chrome (intro wide -> game with PiP -> ending wide), recorded with sound
export OUT
cd $R/tools/pod && timeout 480 $PY nova_final_proof.py A > $OUT/A.log 2>&1; stage "A exit $?"
curl -s -m5 http://127.0.0.1:8010/ > $OUT/A_face.json; curl -s -m5 http://127.0.0.1:8031/health > $OUT/A_ditto.json
curl -s -m120 -X POST "http://127.0.0.1:8010/finish?tag=A" > $OUT/A_finish.json
stage "A finish: $(cut -c1-200 $OUT/A_finish.json)"

# 7) small copies to pull (the 1080 Ditto cuts at CRF 18; the page recording as recorded)
cd $OUT/face
for t in W A; do [ -s wide_published_$t.mp4 ] && ffmpeg -loglevel error -y -i wide_published_$t.mp4 -c:v libx264 -preset medium -crf 18 -c:a aac -b:a 128k -movflags +faststart $OUT/nova-wide-ditto-$t-1080.mp4; done
[ -s face_published_A.mp4 ] && cp face_published_A.mp4 $OUT/nova-pip-soulx-A.mp4
ls -la $OUT/*.mp4 >> $OUT/STAGES
cp $OUT/rtlk.log $OUT/rtlk_copy.log 2>/dev/null
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader >> $OUT/STAGES 2>&1
stage "DONE"; touch $OUT/DONE
sleep infinity
