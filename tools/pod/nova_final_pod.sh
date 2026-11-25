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
      '/freezegame/' '/audio/freeze2/' '/audio/intro/*.mp4' '/test/clips/' '/pod/' '/tools/pod/' '/media/wave-ref.mp4' '/media/upperbody-ref.mp4' '/audio/says/' '/audio/react/' '/models/' '/nova-session-rec.js' '/nova-ending.js' '/pod-registry.js' '/nova-joined-small.mp4' && git checkout -q "$BR"
R=/root/repo; stage "repo $(cd $R && git rev-parse --short HEAD) body $(ls -la $R/tools/pod/assets/nova_talk_wide.mp4 | awk '{print $5}')"
# NOVA-FASTBOOT (NF_VOLUME_DIR set by the launcher's NF_VOLUME=<id>; unset = the old boot, unchanged): the heavy parts
# come from Nova's network volume, see tools/pod/nova_fastboot.sh and docs/NOVA-FASTBOOT.md
NFB=""; [ -n "${NF_VOLUME_DIR:-}" ] && { NFB=1; . $R/tools/pod/nova_fastboot.sh; }

# 2a) Ditto: prebuilt pack (ditto_up.sh DITTO_PACK) — Ditto Gold recipe flags (ditto-lips skill §5.6, Nova values from
#     tools/pod/ditto_take8/nova_take8.env). [CLI-FILL] DITTO_CHUNK=10 / DITTO_TAKE_TIMEOUT=0.35: the co-host's live chunk
#     (ditto_up log 2026-11-10: chunk_frames 10), so the render thread can stay one chunk ahead in 0.4 s steps.
export MAYA_LOGS=$OUT/ditto DITTO_PACK=${DITTO_PACK:-ditto-pack-v2} DITTO_SRC=$R/tools/pod/assets/nova_talk_wide.mp4
# ── NOVA-AUDIT (2026-11-22, branch nova-audit; docs/NOVA-ERRORS-2026-11-22.md). Refael on nova_approve.mp4: "slow like shit,
#    not the correct intro (the ORIGINAL is with the LIGHT ON HER SHOULDER), she needs to be more calm, not move much".
#    Every fix is behind its own flag, default off in the code; THIS build turns them on here (NF_AUDIT=0 = the old build).
#    · NF_CALM=1   her wide talk body = tools/pod/assets/nova_talk_calm.mp4 (the calm full body, docs/nova-ditto/fullbody/
#                  nova_fullbody_calm.mp4 framed 1.3x like nova_talk_wide) — motion 0.17 vs 4.3 per frame (25x calmer)
#    · face server FACE_VOICE_PREBUF_MS / FACE_REC_THREAD / FACE_PUB_STEADY (tools/pod/nova_face.py) — voice holes, publish stalls
#    · page flags shoulder + fpsprobe (beta/freeze4-flags.js written below) · NF_REC_FIX=1 the proof recorder (freeze4_proof.py)
NF_AUDIT=${NF_AUDIT:-1}
if [ "$NF_AUDIT" = 1 ] && [ "${NF_CALM:-1}" = 1 ] && [ -s $R/tools/pod/assets/nova_talk_calm.mp4 ]; then export DITTO_SRC=$R/tools/pod/assets/nova_talk_calm.mp4; fi
# NOVA-GO5 (2026-11-24) · NF_CLOSED=1 (default on with NF_GO5): the same calm body with her mouth CLOSED on every frame
#   (maya-lt bench/lips_pro/close_mouth_stable.py, ref frame 66, sigma 2, face found in an upscaled crop: 252/252).
#   Ditto Gold: nova_talk_calm.mp4 body BLOCK (mouth open 3.6 % of frames) -> takes BLOCK (87 open frames in silence);
#   nova_talk_calm_closed.mp4 body PASS (open 0.0 %, jitter 0.07). The original file is kept.
if [ "${NF_GO5:-1}" = 1 ] && [ "${NF_CLOSED:-1}" = 1 ] && [ "$(basename "$DITTO_SRC")" = nova_talk_calm.mp4 ] && [ -s $R/tools/pod/assets/nova_talk_calm_closed.mp4 ]; then export DITTO_SRC=$R/tools/pod/assets/nova_talk_calm_closed.mp4; fi
# NOVA-LIVE2 speed (Refael 2026-11-25 "how can you reduce it to 2 s"): the face voice cushion 400 -> 200 ms under NF_LIVE2. [CLI-FILL]
[ "${NF_LIVE2:-0}" = 1 ] && export FACE_VOICE_PREBUF_MS=${FACE_VOICE_PREBUF_MS:-200}
[ "$NF_AUDIT" = 1 ] && export NF_PROOF_REPLAY=${NF_PROOF_REPLAY:-own-right-up,frozen-body,dance-hype,still-sway} NF_REC_FIX=${NF_REC_FIX:-1} FACE_VOICE_PREBUF_MS=${FACE_VOICE_PREBUF_MS:-400} FACE_REC_THREAD=${FACE_REC_THREAD:-1} FACE_PUB_STEADY=${FACE_PUB_STEADY:-1} FACE_WIDE_SOURCE=${FACE_WIDE_SOURCE:-camera} FACE_WIDE_TS=${FACE_WIDE_TS:-1}
# ── NOVA-GO2 (2026-11-23; docs/NOVA-FIX-2026-11-23.md): NF_GO2=1 (default on in this build; 0 = the nova-go build as it was)
#    · FACE_WIDE_SMOOTH=1  her wide track: one layer (no simulcast), keep the frame rate (tools/pod/nova_face.py)
#    · FACE_WIDE_PREP=1    wide frames resized/converted in the render thread, not in the 25 fps publish loop
#    · page flag ambstill  the blurred room behind her live body is held still (the page's own frame-rate cost)
#    · page flags warmgate (reveal only on a smooth stream) · matchcut (no size jump at the game hand-over) · heneutral (Hebrew plural)
NF_GO2=${NF_GO2:-1}
[ "$NF_AUDIT" = 1 ] && [ "$NF_GO2" = 1 ] && export FACE_WIDE_SMOOTH=${FACE_WIDE_SMOOTH:-1} FACE_WIDE_PREP=${FACE_WIDE_PREP:-1}
stage "audit flags: NF_AUDIT=$NF_AUDIT body=$(basename $DITTO_SRC) prebuf=${FACE_VOICE_PREBUF_MS:-0} rec_thread=${FACE_REC_THREAD:-0} pub_steady=${FACE_PUB_STEADY:-0} wide_source=${FACE_WIDE_SOURCE:-screenshare} wide_ts=${FACE_WIDE_TS:-0} rec_fix=${NF_REC_FIX:-0} go2=${NF_GO2} wide_smooth=${FACE_WIDE_SMOOTH:-0} wide_prep=${FACE_WIDE_PREP:-0}"
# DITTO_FACE_ROBUST=1: her face is 205 px in a 1080x1920 frame -> the full-frame detector at 0.5 misses frame 0 (pod run
#   2026-11-12 #1: "mediapipe: no face in the first source frame"; the chef bank's same 205 px case, ditto_wide.py). Local: 118/121.
export DITTO_FACE_ROBUST=1 DITTO_AMP=${DITTO_AMP:-0.6} DITTO_GRAIN=0 DITTO_MASK=lower DITTO_PASTE_GATE=1 DITTO_PASTE_OFF_MS=80 DITTO_PASTE_XFADE_MS=120 \
       DITTO_ON_RMS=0.012 DITTO_FAST_CLOSE=1 DITTO_DEBT_FIX=1 DITTO_FAST_PRIME=1 DITTO_PRIME=${DITTO_PRIME:-35} DITTO_CHUNK=${DITTO_CHUNK:-10} \
       DITTO_TAKE_TIMEOUT=${DITTO_TAKE_TIMEOUT:-0.35} DITTO_VAD=1 DITTO_EYE_HOLD=1 DITTO_THREADS=${DITTO_THREADS:-6} DITTO_STATS_EVERY=25
mkdir -p $MAYA_LOGS
if [ -n "$NFB" ]; then nfb_ditto_start; else
( t=$(date +%s); for i in 1 2; do bash $R/tools/pod/ditto_take8/ditto_up.sh > $OUT/ditto_up.log 2>&1 && break; sleep 5; done
  echo "rc=$? after $(( $(date +%s) - t )) s" >> $OUT/ditto_up.log ) &
DPID=$!
fi

# 2b) SoulX weights (baked into the image, else fetch)
[ -n "$NFB" ] || ( if [ -s "$SOULX_ROOT/ACTIVATE.sh" ] && [ -d "$SOULX_ROOT/models/SoulX-FlashHead-1_3B" ]; then echo "weights baked" > $OUT/weights.txt
  else echo "weights NOT baked - fetching" > $OUT/weights.txt; timeout 1200 $PY $MO/soulx_fetch.py --root "$SOULX_ROOT" --jobs 4 >> $OUT/weights.txt 2>&1; fi ) &
[ -n "$NFB" ] || WPID=$!

# 2c) system packages + Chrome + python deps
export DEBIAN_FRONTEND=noninteractive
# fast boot (common image): also python3.10 for /opt/ltenv (+ -dev: triton compiles a C helper against Python.h at the
# SoulX warm-up; without it the face server dies with "Python.h: No such file", prep pod 2026-11-22), ffmpeg, libs
NFB_APT=""; [ -n "$NFB" ] && NFB_APT="python3.10 python3.10-dev ffmpeg wget libgl1 libglib2.0-0 libsndfile1"
timeout 400 bash -c "apt-get update -qq && apt-get install -y -qq xvfb pulseaudio ca-certificates fonts-noto-color-emoji fonts-dejavu-core $NFB_APT" > $OUT/apt1.log 2>&1; AE=$?; stage "apt done $AE"
# pod alkbue4ll59ugx 2026-11-23: apt timed out (124) on a slow mirror -> no Xvfb / ffmpeg, the proof and the recordings died. One more try.
if [ $AE != 0 ] || ! command -v Xvfb >/dev/null || ! command -v ffmpeg >/dev/null; then
  timeout 600 bash -c "dpkg --configure -a >/dev/null 2>&1; apt-get update -qq; apt-get install -y -qq xvfb pulseaudio ca-certificates fonts-noto-color-emoji fonts-dejavu-core $NFB_APT >/dev/null 2>&1"; stage "apt retry done $? xvfb=$(command -v Xvfb) ffmpeg=$(command -v ffmpeg)"; fi
# NOVA-LIVE2 pod ut59hiszu2jnsp 2026-11-25: both tries failed in 3 s (exit 100, not a timeout) -> no Xvfb, proof A never ran.
# A third try that logs the error, sets aside the image's extra apt sources (a broken third-party list fails the whole
# update), retries downloads, and asks only for what the proof needs.
if ! command -v Xvfb >/dev/null; then
  mkdir -p /root/apt-off; mv /etc/apt/sources.list.d/* /root/apt-off/ 2>/dev/null
  timeout 600 bash -c "rm -f /var/lib/dpkg/lock* /var/lib/apt/lists/lock; dpkg --configure -a; apt-get -o Acquire::Retries=5 update; apt-get -o Acquire::Retries=5 install -y --no-install-recommends xvfb pulseaudio fonts-dejavu-core $NFB_APT" > $OUT/apt3.log 2>&1
  stage "apt try 3 done $? xvfb=$(command -v Xvfb) | $(grep -E '^(E:|W:)' $OUT/apt3.log | head -3 | tr '\n' ' ' | cut -c1-200)"
fi
wget -q -O /root/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && timeout 300 apt-get install -y -qq /root/chrome.deb >/dev/null 2>&1
stage "chrome: $(google-chrome --version 2>&1)"
stage "hw: gpu=$(nvidia-smi --query-gpu=name,clocks.max.sm,memory.total,driver_version --format=csv,noheader 2>&1 | head -1) cpu=$(lscpu 2>/dev/null | grep -m1 'Model name' | cut -d: -f2 | xargs) nproc=$(nproc) load=$(cut -d' ' -f1-3 /proc/loadavg)"
# NOVA-TRACE: GPU/CPU load every 2 s for the whole run (players-per-machine headroom)
( while true; do echo "$(date +%s) $(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits 2>/dev/null | head -1) $(cut -d' ' -f1 /proc/loadavg)" >> $OUT/load.txt; sleep 2; done ) &
[ -n "$NFB" ] && nfb_wait_ltenv
$PY -m pip install -q --no-cache-dir livekit livekit-api aiohttp playwright >/dev/null 2>&1; stage "pip done $? ($($PY -c 'import livekit.rtc,livekit.api,aiohttp,playwright;print("ok")' 2>&1 | tail -1))"

P=/workspace/pages; mkdir -p $P/beta $P/test /workspace/audio
mkdir -p /workspace/media && cp $R/media/*.mp4 /workspace/media/ ; cp $R/beta/wave.html $R/beta/upperbody.html $R/beta/novasays.html $P/beta/; cp $R/beta/novasays*.js $P/beta/; cp -r $R/audio/says /workspace/audio/says
mkdir -p $P/models && cp $R/models/* $P/models/; cp $R/beta/upgroove.html $P/up-groove.html; cp $R/nova-session-rec.js $R/nova-ending.js $R/pod-registry.js $R/nova-joined-small.mp4 $P/
cp $R/beta/freeze4.html $R/beta/play.css $P/beta/ && { cp $R/beta/freeze4-flags.js $P/beta/ 2>/dev/null || echo 'window.__F4_FLAGS = {};' > $P/beta/freeze4-flags.js; } && cp -r $R/beta/lib $R/beta/freeze2 $P/beta/ && cp -r $R/shared $P/shared \
 && cp -r $R/freezegame $P/freezegame && cp -r $R/audio/freeze2 /workspace/audio/freeze2 && cp -r $R/audio/react /workspace/audio/react && cp -r $R/test/clips $P/test/clips \
 && cp $R/pod/rt_lk.py /workspace/rt_lk.py
stage "deployed $?"
# NOVA-AUDIT page flags for this build (the repo copy has them all off)
[ "$NF_AUDIT" = 1 ] && echo "window.__F4_FLAGS = { shoulder: ${NF_SHOULDER:-true}, fpsprobe: true, pipfresh: true };   // written by nova_final_pod.sh (NOVA-AUDIT build)" > $P/beta/freeze4-flags.js
[ "$NF_AUDIT" = 1 ] && [ "$NF_GO2" = 1 ] && echo "window.__F4_FLAGS = { shoulder: ${NF_SHOULDER:-true}, fpsprobe: true, pipfresh: true, warmgate: true, matchcut: true, heneutral: true, ambstill: true, noblink: true };   // written by nova_final_pod.sh (NOVA-GO2 build)" > $P/beta/freeze4-flags.js
# ── NOVA-GO4 (2026-11-23; docs/NOVA-FIX-2026-11-23b.md): NF_GO4=1 (default on in this build; 0 = the nova-go3 build as it was)
#    · page flag split  — split screen from the first second (his camera is no longer blown up over her half)
#    · page flag hear   — one microphone stream, audio unlocked in the Play tap, the microphone chip + watch, a tight echo
#                         guard, "Ready?" waits for his yes, his words outrank her game line, the page log goes to the brain
#    · NOVA_HEAR=1      — pod/rt_lk.py: she answers the child in the intro, in the game's gaps and at the ending
NF_GO4=${NF_GO4:-1}
[ "$NF_AUDIT" = 1 ] && [ "$NF_GO2" = 1 ] && [ "$NF_GO4" = 1 ] && echo "window.__F4_FLAGS = { shoulder: ${NF_SHOULDER:-true}, fpsprobe: true, pipfresh: true, warmgate: true, matchcut: true, heneutral: true, ambstill: true, noblink: true, split: true, hear: true, rec: ${NF_REC:-true} };   // written by nova_final_pod.sh (NOVA-GO4 build)" > $P/beta/freeze4-flags.js
#    · page flag rec + NOVA_REC=1 — the player's whole game as one mp4: the tab (both halves + sound + his voice) is recorded in
#      his browser, sent here in pieces, and served as https://<pod>-8099.proxy.runpod.net/play-<session>.mp4  (NF_REC=false = off)
[ "$NF_GO4" = 1 ] && export NOVA_HEAR=${NOVA_HEAR:-1}
[ "$NF_GO4" = 1 ] && [ "${NF_REC:-true}" = true ] && export NOVA_REC=1 NOVA_REC_DIR=$OUT NF_REC_PROOF=1
# ── NOVA-GO5 (2026-11-24; docs/NOVA-GO5-2026-11-24.md): NF_GO5=1 (default on in this build; 0 = the nova-go4 build as it was)
#    · page flag v2vintro + NOVA_V2V_INTRO=1 — her APPROVED live intro: she greets and asks the name, waits, gives the name
#      back and chats in her own words, and the NAME arms the shoulder light (origin/main INTRO-V2V, LAWS.md law-shoulder)
NF_GO5=${NF_GO5:-1}
[ "$NF_GO5" = 1 ] && [ "$NF_GO4" = 1 ] && grep -q 'hear: true' $P/beta/freeze4-flags.js && sed -i 's/ };/, v2vintro: true, react: true };/' $P/beta/freeze4-flags.js && export NOVA_V2V_INTRO=${NOVA_V2V_INTRO:-1} NOVA_FAST_KID=${NOVA_FAST_KID:-1} NOVA_UTT_MAP=${NOVA_UTT_MAP:-1} NOVA_TX_CONF=${NOVA_TX_CONF:-1} NOVA_RT_EFFORT=${NOVA_RT_EFFORT:-minimal} NOVA_TRACE=${NOVA_TRACE:-1}
# NOVA-LIVE2 (2026-11-25, docs/NOVA-LIVE2-2026-11-25.md): NF_LIVE2=1 -> early-start answers (held until the turn is validated),
#   smart listening sounds (page flag live2), her relaxed attitude, her ElevenLabs voice Kymmiee in English (page flag eleven,
#   brain NOVA_TTS=eleven), and the confidence cut OFF (-9, log only): Refael's own clear "Okay" scored -2.80 on his laptop mic 2026-11-25 = inside the noise range, so the cut drops real players.
[ "${NF_LIVE2:-0}" = 1 ] && grep -q 'react: true' $P/beta/freeze4-flags.js && sed -i 's/react: true };/react: true, live2: true, eleven: true };/' $P/beta/freeze4-flags.js && export NOVA_LIVE2=1 NOVA_TTS=${NOVA_TTS:-eleven} NOVA_TX_CONF_MIN=${NOVA_TX_CONF_MIN:--9}
[ "${NF_LIVE2:-0}" = 1 ] && stage "live2: flags $(grep -o 'live2[^}]*' $P/beta/freeze4-flags.js) tts=${NOVA_TTS} eleven_key=$([ -n "$ELEVENLABS_API_KEY" ] && echo set || echo MISSING)"
stage "page flags: $(cat $P/beta/freeze4-flags.js | cut -c1-230) | NOVA_HEAR=${NOVA_HEAR:-0} NOVA_V2V_INTRO=${NOVA_V2V_INTRO:-0} NOVA_FAST_KID=${NOVA_FAST_KID:-0}"

# 3) the brain — its own room; the face engine on :8010 (dual)
cd /workspace
# NOVA_KID_EVENTS=1 (2026-11-22, this build only; default off in pod/rt_lk.py): the brain tells the page when a heard
# utterance was not accepted, so the page's live "You: ..." line closes and the intro does not wait for words that never come.
# NOVA_INTRO_ANSWER=1 (same): in the intro she may answer the child in one short sentence (see pod/rt_lk.py INTRO_NOTE).
LK_ROOM=nova-final ENGINE_URL=http://127.0.0.1:8010 NOVA_FACE_SOULX=1 NOVA_FACE_DUAL=1 NOVA_TEST_CLIPS=1 NOVA_KID_EVENTS=${NOVA_KID_EVENTS:-1} NOVA_INTRO_ANSWER=${NOVA_INTRO_ANSWER:-1} NOVA_HEAR=${NOVA_HEAR:-0} NOVA_V2V_INTRO=${NOVA_V2V_INTRO:-0} NOVA_FAST_KID=${NOVA_FAST_KID:-0} NOVA_UTT_MAP=${NOVA_UTT_MAP:-0} NOVA_TX_CONF=${NOVA_TX_CONF:-0} NOVA_RT_EFFORT=${NOVA_RT_EFFORT:-} NOVA_TRACE=${NOVA_TRACE:-0} NOVA_LIVE2=${NOVA_LIVE2:-0} NOVA_TTS=${NOVA_TTS:-} NOVA_TX_CONF_MIN=${NOVA_TX_CONF_MIN:--1.6} NOVA_REC=${NOVA_REC:-0} NOVA_REC_DIR=$OUT \
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
# the proof's CHILD line (2026-11-22): Refael's own first words to her, "Hi Nova, can you hear me?", as a recording the
# proof browser plays into the page's microphone after her intro. Made with the OpenAI speech API (the key is already
# this pod's env; it is never echoed), else espeak-ng. No line = the proof says so and runs without it.
curl -s -m 40 https://api.openai.com/v1/audio/speech -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini-tts","voice":"ash","input":"Hi Nova, can you hear me?","response_format":"wav"}' -o /root/kid_raw.wav 2>/dev/null
ffmpeg -loglevel error -y -i /root/kid_raw.wav -ac 1 -ar 48000 /root/kid_line.wav 2>/dev/null
KIDSRC=openai-tts
if [ ! -s /root/kid_line.wav ]; then KIDSRC=espeak-ng
  timeout 120 apt-get install -y -qq espeak-ng >/dev/null 2>&1; espeak-ng -s 150 -w /root/kid_raw.wav "Hi Nova, can you hear me?" 2>/dev/null
  ffmpeg -loglevel error -y -i /root/kid_raw.wav -ac 1 -ar 48000 /root/kid_line.wav 2>/dev/null; fi
[ -s /root/kid_line.wav ] && cp /root/kid_line.wav $OUT/kid_line.wav
# NOVA-GO4: the child also speaks in the GAME and at the ENDING (same voice, same API; no file = that line is skipped)
if [ "${NF_GO4:-1}" = 1 ]; then
  # NOVA-GO5: + the NAME answer; NF_PROOF_LANG=he = the child speaks Hebrew
  if [ "${NF_PROOF_LANG:-en}" = he ]; then KL1="game|נובה, את שומעת אותי?"; KL2="end|תודה נובה, היה כיף!"; KL3="name|היי נובה! קוראים לי שוקי."
  else KL1="game|Nova, can you hear me?"; KL2="end|Thank you Nova, that was fun!"; KL3="name|Hi Nova! My name is Shuki."; fi
  for kl in "$KL1" "$KL2" "$KL3"; do kn=${kl%%|*}; kt=${kl#*|}
    curl -s -m 40 https://api.openai.com/v1/audio/speech -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
      -d "{\"model\":\"gpt-4o-mini-tts\",\"voice\":\"ash\",\"input\":\"$kt\",\"response_format\":\"wav\"}" -o /root/kid_raw_$kn.wav 2>/dev/null
    ffmpeg -loglevel error -y -i /root/kid_raw_$kn.wav -ac 1 -ar 48000 /root/kid_$kn.wav 2>/dev/null; done
  stage "kid game/end/name lines: $(ls -la /root/kid_game.wav /root/kid_end.wav /root/kid_name.wav 2>/dev/null | awk '{print $5}' | tr '\n' ' ') bytes"
fi
stage "kid line ($KIDSRC): $(ls -la /root/kid_line.wav 2>/dev/null | awk '{print $5}') bytes"

wait $DPID; stage "ditto: $(tail -2 $OUT/ditto_up.log | tr '\n' ' ' | cut -c1-300)"
curl -s -m5 http://127.0.0.1:8031/health > $OUT/ditto_health_boot.json
grep -q '"ready": *true' $OUT/ditto_health_boot.json || { stage "FAILED: Ditto not ready ($(cut -c1-200 $OUT/ditto_health_boot.json))"; stage "DONE"; touch $OUT/DONE; sleep infinity; }
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
[ "${NF_SKIP_W:-0}" = 1 ] && echo skip > /root/skipw
[ -f /root/skipw ] || python3 - <<'PYW' >> $OUT/W.log 2>&1
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
[ "${NF_SKIP_A:-0}" = 1 ] || { cd $R/tools/pod && timeout 480 $PY nova_final_proof.py A > $OUT/A.log 2>&1; stage "A exit $?"; }
curl -s -m5 http://127.0.0.1:8010/ > $OUT/A_face.json; curl -s -m5 http://127.0.0.1:8031/health > $OUT/A_ditto.json
curl -s -m120 -X POST "http://127.0.0.1:8010/finish?tag=A" > $OUT/A_finish.json
stage "A finish: $(cut -c1-200 $OUT/A_finish.json)"
# NOVA-GO4 rec: the proof browser recorded its own tab like a player would; the brain closes the file 20 s after the last piece
if [ "${NOVA_REC:-0}" = 1 ] && [ "${NF_SKIP_A:-0}" != 1 ]; then
  for i in $(seq 1 30); do ls $OUT/play-*.mp4 >/dev/null 2>&1 && break; sleep 4; done; sleep 3
  PM=$(ls -t $OUT/play-*.mp4 2>/dev/null | head -1)
  stage "player recording: ${PM:-NONE} $(ls $OUT/play 2>/dev/null | tr '\n' ' ') $([ -n "$PM" ] && ffprobe -v error -show_entries stream=codec_type,codec_name,width,height:format=duration,size -of csv=p=0 $PM 2>&1 | tr '\n' ' ') | $(grep -a '\[REC\]' $OUT/rtlk.log | tail -2 | tr '\n' ' ' | cut -c1-200)"
  [ -n "$PM" ] && ffmpeg -loglevel error -y -i $PM -af volumedetect -vn -f null - 2> $OUT/play_volume.txt; ffmpeg -loglevel info -y -i $PM -af volumedetect -vn -f null - 2>&1 | grep -a "mean_volume\|max_volume" | tr '\n' ' ' > $OUT/play_volume.txt
  stage "player recording sound: $(cat $OUT/play_volume.txt | cut -c1-160)"
fi

# 6b) G — every other converted game: a short real run each (the child = her own reference clip as a fake camera)
for g in ${NF_GAMES:-wave upperbody}; do
  src=/workspace/media/$g-ref.mp4; [ $g = novasays ] && src=/workspace/media/wave-ref.mp4; [ $g = upgroove ] && src=$P/nova-joined-small.mp4
  ffmpeg -loglevel error -y -i $src -vf "scale=640:-2,fps=25" -t 90 -q:v 5 /root/kid_$g.mjpeg
  cd $R/tools/pod && timeout 240 $PY nova_final_proof.py $g /root/kid_$g.mjpeg > $OUT/G_$g.log 2>&1; stage "G $g exit $? $(grep recorded $OUT/G_$g.log)"
  curl -s -m5 http://127.0.0.1:8010/ > $OUT/G_${g}_face.json; curl -s -m120 -X POST "http://127.0.0.1:8010/finish?tag=$g" > $OUT/G_${g}_finish.json
done

# 7) small copies to pull (the 1080 Ditto cuts at CRF 18; the page recording as recorded)
cd $OUT/face
for t in W A ${NF_GAMES:-wave upperbody}; do [ -s wide_published_$t.mp4 ] && ffmpeg -loglevel error -y -i wide_published_$t.mp4 -c:v libx264 -preset medium -crf 18 -c:a aac -b:a 128k -movflags +faststart $OUT/nova-wide-ditto-$t-1080.mp4; done
[ -s face_published_A.mp4 ] && cp face_published_A.mp4 $OUT/nova-pip-soulx-A.mp4
# NOVA-AUDIT: a small copy of exactly what the pod PUBLISHED in the A run (repeats are measured on it vs the browser recording)
[ -s wide_published_A.mp4 ] && ffmpeg -loglevel error -y -i wide_published_A.mp4 -vf scale=540:-2 -c:v libx264 -preset medium -crf 20 -an $OUT/nova-wide-published-A-540.mp4
ls -la $OUT/*.mp4 >> $OUT/STAGES
cp $OUT/rtlk.log $OUT/rtlk_copy.log 2>/dev/null
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader >> $OUT/STAGES 2>&1
[ -n "$NFB" ] && nfb_save
stage "DONE"; touch $OUT/DONE
sleep infinity
