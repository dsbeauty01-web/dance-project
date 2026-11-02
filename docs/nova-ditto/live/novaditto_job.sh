#!/usr/bin/env bash
# novaditto_job.sh -- session novaditto-final, 2026-11-02. ONE deliverable: an mp4 of Nova's
# COMMERCIAL intro with DITTO as the face engine, her voice audible, a kid answering in chat.
#
# WHAT IS DIFFERENT FROM novarec_job2.sh (the session that got the mp4 but on MuseTalk):
#
# 1. THE BODY is from_maya/assets/nova_idle.mp4 -- the one already proven live on Ditto in the
#    Maya build. 1080x1920 @25, 69 frames, 2.76 s. prebake_gate.py was run on it OFF-POD (CPU
#    only, no money): verdict SOFTEN (PASS or SOFTEN is the bar), face 316 px, 100% face found,
#    mouth_p50 0.0085 (closed), hand_pct 0.0; the two SOFTEN checks are rot_v_p95 1.93 and
#    smo_res_p95 2.07. No new body is generated and no fal money is spent.
#    No motion bank, no full-body shim (DITTO_FB_ON unset): this body needs neither.
#
# 2. THE AUDIO BUG IS FIXED IN THE BRIDGE PATCH. The 2026-11-01 patch stamped each audio frame
#    at DEQUEUE instead of ARRIVAL, so every frame paid the whole 1800 ms offset again --
#    measured in novarec_bridge.log as 100 audio frames per 1000 video frames (18-20x too
#    slow), which is why both Ditto takes read max_volume -84.3 dB. ditto_bridge_patch.py now
#    has a fifth anchor A5 at the engine socket's 'A' branch which (a) stamps the real arrival
#    time and (b) feeds Ditto IN THE PUBLISHING PROCESS -- the old wiring fed one DittoFace in
#    rt_lk.py and published from a different, never-fed one in lk_bridge.py.
#    So: the BRAIN runs WITHOUT NOVA_FACE and only the BRIDGE gets NOVA_FACE=ditto.
#
# 3. THE PAGE. The commercial greeting is the branch in rt_lk.py that runs when NO intro= is
#    set. beta/freeze.html hardcodes intro=freeze twice and registers the [GAME-MODE] persona,
#    which REPLACES the intro script. The uploaded beta__freeze.html is that page with one
#    query flag, ?commercial=1, suppressing exactly those three things -- the brain's words are
#    untouched. It is installed atomically over the volume's copy, with the original kept, and
#    put back in stage 10.
#
# 4. boot.sh's DEPLOY STEP IS SKIPPED in the wrapper. It is what truncated /workspace/pages on
#    2026-11-01 and it prints a URL carrying the volume's deploy token on failure. /workspace
#    /pages is whole (86 files) and this job never risks it.
#
# 5. THE RECORDER draws one frame per DECODED frame (requestVideoFrameCallback + captureStream(0)
#    + requestFrame) instead of repainting on a 40 ms timer, and measures its own output:
#    max_volume and duplicate-frame percent, both with ffmpeg.
#
# The CMD channel from novarec is kept: PUT a shell script to /root/in/CMD and it runs once.
set -uo pipefail
cd /root || exit 9
IN=/root/in; OUT=/root/novaditto_out; MT=/root/mt; LOG=/root/logs
DP=/workspace/_sys/pylibs311_good/dist-packages
TFX=/root/torchfix
mkdir -p "$OUT" "$MT/maya-ops/lt" "$MT/bench/replace_musetalk_alt" "$LOG" /root/rec
say(){ local m="[job $(date -u +%H:%M:%S)] $*"; echo "$m"; echo "$m" >> "$OUT/STAGES"; }
: > "$OUT/STAGES"
RED='s#(https?://)[^/@[:space:]]+@#\1<REDACTED-TOKEN>@#g; s#x-access-token:[A-Za-z0-9_-]+#x-access-token:<REDACTED>#g; s#gh[psuor]_[A-Za-z0-9]{16,}#<REDACTED>#g'

# ---------- stage 0b: the CMD channel, up before anything can go wrong ----------
( while true; do
    if [ -s "$IN/CMD" ]; then
      ts=$(date -u +%H%M%S); mv "$IN/CMD" "/root/cmd.$ts.sh" 2>/dev/null \
        && bash "/root/cmd.$ts.sh" > "$OUT/CMD_OUT.$ts" 2>&1
      echo "rc=$?" >> "$OUT/CMD_OUT.$ts"
    fi
    sleep 3
  done ) &
say "stage 0b: CMD channel open (PUT /put/CMD -> runs once -> novaditto_out/CMD_OUT.<hhmmss>)"

need="novalive_job.sh repair_pylibs.py real_harness.py ditto_bridge_patch.py nova_ditto.py boot_wrap.py \
ditto_server.py ditto_up.sh ditto_wide.py motion_bank.py nova_idle.mp4 nova_idle.gate.json \
beta__freeze.html libtorch_global_deps.so PAYLOAD_DONE"
say "stage 0: waiting for the payload"
for i in $(seq 1 240); do
  ok=1; for f in $need; do [ -s "$IN/$f" ] || ok=0; done
  [ $ok = 1 ] && break; sleep 5
done
for f in $need; do [ -s "$IN/$f" ] || { say "MISSING $f -- abort"; exit 11; }; done
say "stage 0 OK: $(ls -1 "$IN" | wc -l) files, nova_idle.mp4 = $(stat -c %s "$IN/nova_idle.mp4") bytes"

# ---------- stage 1a: MEASURE the torch tree. No guessing. ----------
say "stage 1a: measuring the volume's torch tree"
{
  for p in /workspace /workspace/_sys "$DP" "$DP/torch" "$DP/torch/lib"; do
    printf '%-70s ' "$p"; ls -ld "$p" 2>&1 | tail -1
  done
  echo; echo "### .so count and total size under $DP/torch"
  find "$DP/torch" -name '*.so*' -type f 2>/dev/null | wc -l
  du -sh "$DP/torch" 2>/dev/null
  echo; echo "### write probe on the volume (1 MB)"
  dd if=/dev/zero of="$DP/.novaditto_write_probe" bs=1M count=1 2>&1 | tail -1
  rm -f "$DP/.novaditto_write_probe"
  echo; echo "### container disk"; df -h / | tail -1
  echo; echo "### volume"; df -h /workspace | tail -1
} > "$OUT/torch_tree.txt" 2>&1
cat "$OUT/torch_tree.txt"
NSO=$(find "$DP/torch" -name '*.so*' -type f 2>/dev/null | wc -l)
say "stage 1a: torch/lib exists? $([ -d "$DP/torch/lib" ] && echo yes || echo NO) ; .so under torch = $NSO"

# ---------- stage 1b: the cheapest branch that actually works ----------
BRANCH=none
if [ -d "$DP/torch/lib" ]; then
  say "stage 1b: BRANCH A -- torch/lib is there, putting the 17 KB file back"
  cp "$IN/libtorch_global_deps.so" "$DP/torch/lib/libtorch_global_deps.so" 2>> "$OUT/torchfix.txt"
  if PYTHONPATH="$DP" python3 -c "import torch,torchvision" 2>>"$OUT/torchfix.txt"; then
    BRANCH=A; say "stage 1b: BRANCH A OK -- torch $(PYTHONPATH="$DP" python3 -c 'import torch;print(torch.__version__)' 2>/dev/null)"
  else
    say "stage 1b: BRANCH A did not fix the import -- falling through to C"
  fi
fi
if [ "$BRANCH" = none ] && PYTHONPATH="$TFX:$DP" python3 -c "import torch,torchvision" 2>/dev/null; then
  BRANCH=C
  say "stage 1b: BRANCH C ALREADY THERE -- $TFX imports torch, skipping the 84 s pip"
fi
if [ "$BRANCH" = none ]; then
  say "stage 1b: BRANCH C -- torch onto the CONTAINER disk at $TFX (the volume is never written)"
  mkdir -p "$TFX"
  ( env -u PYTHONPATH python3 -m pip install --no-input -q --target "$TFX" \
      --index-url https://download.pytorch.org/whl/cu129 \
      "torch==2.9.1+cu129" "torchvision==0.24.1+cu129" ) > "$OUT/torch_container.log" 2>&1
  TRC=$?
  if [ "$TRC" != 0 ]; then
    say "stage 1b: pinned torchvision failed (rc=$TRC), retrying with torch pinned only"
    ( env -u PYTHONPATH python3 -m pip install --no-input -q --target "$TFX" \
        --index-url https://download.pytorch.org/whl/cu129 "torch==2.9.1+cu129" torchvision ) \
        >> "$OUT/torch_container.log" 2>&1
    TRC=$?
  fi
  say "stage 1b: pip rc=$TRC -- $(du -sh "$TFX" 2>/dev/null | cut -f1) on the container disk"
  if PYTHONPATH="$TFX:$DP" python3 -c "import torch,torchvision;print(torch.__version__,torchvision.__version__)" > "$OUT/torch_container_import.txt" 2>&1; then
    BRANCH=C; say "stage 1b: BRANCH C OK -- $(cat "$OUT/torch_container_import.txt")"
  else
    say "stage 1b: BRANCH C FAILED:"; tail -5 "$OUT/torch_container_import.txt" | while read -r l; do say "    $l"; done
  fi
fi
echo "$BRANCH" > "$OUT/BRANCH"
if [ "$BRANCH" = C ]; then PYPATH="$TFX:$DP"; else PYPATH="$DP"; fi
echo "$PYPATH" > "$OUT/PYPATH"
say "stage 1 DONE: branch=$BRANCH  PYTHONPATH=$PYPATH"

# ---------- stage 1c: the boot wrapper -- THREE one-line rewrites, each verified ----------
# (1) the hardcoded PYTHONPATH -> the tree that actually imports torch
# (2) the DEPLOY step -> skipped: it truncated /workspace/pages on 2026-11-01 and prints a URL
#     carrying the volume's deploy token on failure
# (3) lk_bridge.py -> launched with `env NOVA_FACE=ditto` on ITS OWN LINE (both launches), so
#     NOVA_FACE is never in the global environment and the BRAIN cannot see it. The brain must
#     not boot a second DittoFace: the process that publishes has to be the one that is fed,
#     and A5 feeds the bridge's. This is the whole of change (2) in the mission brief.
BOOTSH=/workspace/boot.sh
BOOTUSE=""
if [ -s "$BOOTSH" ]; then
  # boot_wrap.py, not sed: the volume's boot.sh is NOT tools/pod/boot.sh -- it has an inline
  # deploy_from_git() AND an if/elif calling two more deploy scripts, and a sed written against
  # the repo's single-line deploy matched none of them (measured: run 1 of this session).
  # boot_wrap.py neutralises every deploy INVOCATION, tags every bridge launch and asserts the
  # brain is untagged; it refuses to write anything if any of that fails. The diff it saves is
  # redacted, because the volume's boot.sh carries plaintext API keys in export lines.
  python3 -I "$IN/boot_wrap.py" --src "$BOOTSH" --out /root/boot_novaditto.sh \
      --pypath "$PYPATH" --diff "$OUT/bootwrap.diff" > "$OUT/bootwrap.txt" 2>&1
  BWRC=$?
  say "stage 1c: boot_wrap rc=$BWRC -- $(grep -E 'rewrites|REFUSING|WROTE' "$OUT/bootwrap.txt" | head -3 | tr '\n' ' ')"
  [ "$BWRC" = 0 ] && BOOTUSE=/root/boot_novaditto.sh
fi
if [ -z "$BOOTUSE" ]; then
  say "stage 1c: REFUSING to boot -- the wrapper could not be built, and plain boot.sh would"
  say "stage 1c: run the page-truncating deploy and would put NOVA_FACE in the brain's env too."
  sed -E "$RED" "$BOOTSH" > "$OUT/boot.sh.asfound" 2>/dev/null
  echo NO_WRAPPER > "$OUT/STACK"; ls -la "$OUT" > "$OUT/LISTING" 2>&1; echo READY > "$OUT/PULLABLE"
  for i in $(seq 1 300); do [ -s "$IN/PULLED" ] && break; sleep 5; done
  exit 0
fi
say "stage 1c: booting with $BOOTUSE"

# ---------- stage 1d: does the volume's rt_lk.py still HAVE the commercial greeting? ----------
# If it does not, there is no commercial intro to record and I need to know BEFORE the pod costs
# anything more. Nothing is edited here -- this is a read.
{
  echo "### md5"; md5sum /workspace/rt_lk.py /workspace/lk_bridge.py 2>&1
  echo; echo "### the commercial greeting (the no-intro= branch)"
  grep -n "magical" /workspace/rt_lk.py | head -5
  echo; echo "### the intro= branches"
  grep -n '_intro == "freeze"\|_intro = (request.query.get' /workspace/rt_lk.py | head -6
} > "$OUT/rtlk_greet.txt" 2>&1
sed -E "$RED" "$OUT/rtlk_greet.txt" > "$OUT/.g" && mv "$OUT/.g" "$OUT/rtlk_greet.txt"
cat "$OUT/rtlk_greet.txt"
GREET_OK=$(grep -c "magical" "$OUT/rtlk_greet.txt" || true)
say "stage 1d: commercial greeting present in the volume's rt_lk.py? lines matching 'magical' = $GREET_OK"

# ---------- stage 2: the C headers Ditto needs. FOREGROUND: it owns the dpkg lock. ----------
say "stage 2: apt python3.10-dev + build-essential (foreground -- owns the dpkg lock)"
( apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3.10-dev build-essential ) > "$OUT/aptdev.log" 2>&1
[ -e /usr/include/python3.10/Python.h ] && say "stage 2 OK: Python.h present" || say "stage 2 WARN: Python.h MISSING"

# ---------- stage 3: Ditto on nova_idle.mp4, in the background ----------
cp "$IN/ditto_server.py" "$IN/ditto_up.sh" "$IN/motion_bank.py" "$MT/maya-ops/lt/"
cp "$IN/ditto_wide.py" "$MT/bench/replace_musetalk_alt/"
chmod +x "$MT/maya-ops/lt/ditto_up.sh"
say "stage 3: ditto_up.sh in the background -- src nova_idle.mp4 (69 frames, so the prime is short)"
(
  export DITTO_ROOT=/root/ditto MAYA_LOGS="$LOG" DITTO_PORT=8031
  # from_maya/profiles/live_trio_nova.json, verbatim. No DITTO_OUT_W/H: the source size IS the
  # delivered size for this body. No DITTO_BANK and no DITTO_FB_ON: no motion bank, no shim.
  export DITTO_AMP=0.6 DITTO_CHUNK=25 DITTO_PRIME=35 DITTO_VAD=1 DITTO_THREADS=6 DITTO_EYE_HOLD=1
  export DITTO_WAIT_SEC=1500
  export DITTO_SRC="$IN/nova_idle.mp4"
  bash "$MT/maya-ops/lt/ditto_up.sh" > "$OUT/ditto_up.log" 2>&1
  echo "$?" > "$OUT/DITTO_RC"
) &

# ---------- stage 4: Chromium + the harness's own deps. SERIAL after apt. ----------
say "stage 4: playwright + chromium + numpy (serial, after apt released the lock)"
( env -u PYTHONPATH python3 -m pip install -q playwright numpy \
  && env -u PYTHONPATH python3 -m playwright install --with-deps chromium ) > "$OUT/playwright.log" 2>&1 \
  && echo READY > "$OUT/PW_READY"
if [ ! -s "$OUT/PW_READY" ]; then
  say "stage 4: first try failed, retrying chromium without --with-deps"
  ( env -u PYTHONPATH python3 -m playwright install chromium ) >> "$OUT/playwright.log" 2>&1 && echo READY > "$OUT/PW_READY"
fi
env -u PYTHONPATH python3 -c "
from playwright.sync_api import sync_playwright
import numpy
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=['--no-sandbox']); print('CHROMIUM OK', b.version, 'numpy', numpy.__version__); b.close()
" > "$OUT/chromium_check.txt" 2>&1
say "stage 4: $(tail -1 "$OUT/chromium_check.txt")"

# ---------- stage 5: the import set the stack ACTUALLY needs, incl. aiortc ----------
say "stage 5: repairing $DP (container pip, PYTHONPATH unset)"
python3 -I "$IN/repair_pylibs.py" --dist-packages "$DP" --repair --rounds 24 \
  --targets "flask,livekit.api,livekit.rtc,aiohttp,requests,numpy,edge_tts,pip,websockets,soundfile,av,aiortc,cv2" \
  --report "$OUT/pylibs_repair.json" > "$OUT/pylibs_repair.txt" 2>&1
say "stage 5: repair rc=$?"
env -u PYTHONPATH python3 -c "import aiortc" 2>/dev/null \
  || env -u PYTHONPATH python3 -m pip install -q aiortc av >> "$OUT/pylibs_repair.txt" 2>&1
{ for m in torch torchvision aiortc av flask edge_tts websockets numpy cv2 scipy soundfile livekit.rtc pip; do
    printf '%-14s ' "$m"
    PYTHONPATH="$PYPATH" python3 -c "import $m;print('OK',getattr($m,'__version__','?'))" 2>&1 | tail -1
  done; } > "$OUT/imports.txt" 2>&1
cat "$OUT/imports.txt"
say "stage 5: $(grep -c ' OK ' "$OUT/imports.txt") of 13 import OK under PYTHONPATH=$PYPATH"

# ---------- stage 6: the bridge -- revert to pristine, probe 5/5, then apply ----------
say "stage 6: --revert to the pristine original (a previous session may have left it patched)"
python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert_pre.txt" 2>&1
say "stage 6: revert rc=$? -- $(grep -E 'REVERTED|no .bak' "$OUT/revert_pre.txt" | head -1)"
say "stage 6: waiting for Ditto to be ready before touching the bridge"
DITTO_OK=0
for i in $(seq 1 90); do
  curl -s -m 8 127.0.0.1:8031/health > "$OUT/health_ditto.json" 2>/dev/null
  grep -q '"ready": *true' "$OUT/health_ditto.json" 2>/dev/null && { DITTO_OK=1; say "stage 6: Ditto ready after $((i*5))s"; break; }
  [ -s "$OUT/DITTO_RC" ] && [ "$(cat "$OUT/DITTO_RC")" != 0 ] && { say "stage 6: ditto_up.sh exited rc=$(cat "$OUT/DITTO_RC")"; break; }
  sleep 5
done
cp "$LOG/ditto_server.log" "$OUT/ditto_server.log" 2>/dev/null
cat "$OUT/health_ditto.json" 2>/dev/null | head -c 900
echo
if [ "$DITTO_OK" != 1 ]; then
  say "stage 6: DITTO NOT READY. The mission forbids a MuseTalk fallback, so there is no take."
  tail -30 "$OUT/ditto_up.log" 2>/dev/null | while read -r l; do say "    $l"; done
  tail -20 "$LOG/ditto_server.log" 2>/dev/null | while read -r l; do say "    $l"; done
  echo NO_DITTO > "$OUT/FACE"
  ls -la "$OUT" > "$OUT/LISTING" 2>&1; echo READY > "$OUT/PULLABLE"
  say "HOLDING on the CMD channel for diagnosis -- no video will be produced."
  for i in $(seq 1 300); do [ -s "$IN/PULLED" ] && break; sleep 5; done
  exit 0
fi

python3 -I "$IN/ditto_bridge_patch.py" --probe --wd "$OUT" > "$OUT/probe.txt" 2>&1; PRC=$?
say "stage 6: probe rc=$PRC"; grep -E "md5|A[1-5] |already patched" "$OUT/probe.txt" | head -10
if [ "$PRC" != 0 ]; then
  say "stage 6: probe is not 5/5 -- NOT applying. No Ditto take is possible; holding for diagnosis."
  echo NO_PATCH > "$OUT/FACE"
  ls -la "$OUT" > "$OUT/LISTING" 2>&1; echo READY > "$OUT/PULLABLE"
  for i in $(seq 1 300); do [ -s "$IN/PULLED" ] && break; sleep 5; done
  exit 0
fi
python3 -I "$IN/ditto_bridge_patch.py" --apply --sidecar "$IN/nova_ditto.py" --wd "$OUT" \
  > "$OUT/apply.txt" 2>&1; ARC=$?
say "stage 6: apply rc=$ARC -- $(grep -E 'APPLIED|already patched|REFUSING' "$OUT/apply.txt" | head -1)"
if [ "$ARC" != 0 ]; then
  say "stage 6: apply refused -- no Ditto take. Reverting and holding."
  python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert_early.txt" 2>&1
  echo NO_PATCH > "$OUT/FACE"; ls -la "$OUT" > "$OUT/LISTING" 2>&1; echo READY > "$OUT/PULLABLE"
  for i in $(seq 1 300); do [ -s "$IN/PULLED" ] && break; sleep 5; done
  exit 0
fi
echo ditto > "$OUT/FACE"
say "stage 6 DONE: face engine = ditto"

# ---------- stage 6b: the COMMERCIAL page, installed atomically, original kept ----------
PG=/workspace/pages/beta/freeze.html
say "stage 6b: installing the ?commercial=1 page over $PG (original kept at /root/freeze.html.orig)"
if [ -s "$PG" ]; then
  cp -p "$PG" /root/freeze.html.orig
  md5sum "$PG" /root/freeze.html.orig "$IN/beta__freeze.html" > "$OUT/page_md5_before.txt" 2>&1
  cp "$IN/beta__freeze.html" "$PG.novaditto-new" && mv "$PG.novaditto-new" "$PG"
  say "stage 6b: $(stat -c %s /root/freeze.html.orig) -> $(stat -c %s "$PG") bytes"
  grep -c "COMMERCIAL" "$PG" > "$OUT/page_commercial_hits.txt" 2>&1
  say "stage 6b: COMMERCIAL guard occurrences in the served page = $(cat "$OUT/page_commercial_hits.txt")"
else
  say "stage 6b: WARN -- $PG is missing or empty; installing the uploaded page anyway"
  mkdir -p "$(dirname "$PG")"; cp "$IN/beta__freeze.html" "$PG"
fi

# ---------- stage 7: boot the stack (bridge sees NOVA_FACE=ditto, brain does not) ----------
boot_once(){   # $1 = tag
  for pat in "[r]t_lk.py" "[l]k_bridge.py" "[b]oot.sh" "[b]oot_novaditto.sh" "[a]pp.py"; do pkill -f "$pat" 2>/dev/null; done
  sleep 3
  export NOVA_DEPLOY_BRANCH=nova-ditto NOVA_DITTO_DELAY_SITE=bridge
  # NOVA_FACE is NOT exported: the wrapper puts it on lk_bridge.py's own launch line, so the
  # brain never sees it and never boots a DittoFace of its own.
  unset NOVA_FACE
  unset PYTHONPATH
  setsid nohup bash "$BOOTUSE" > "$OUT/bootwrap.$1.log" 2>&1 < /dev/null &
  for i in $(seq 1 100); do        # LAW-PODS-9: a cold MuseTalk load is silent for minutes
    [ "$(curl -s -m 4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/ 2>/dev/null)" = "200" ] && return 0
    if [ $((i % 12)) = 0 ]; then
      say "    boot $((i*5))s: :8010=$(curl -s -m3 -o /dev/null -w '%{http_code}' http://127.0.0.1:8010/ 2>/dev/null) :8765=$(curl -s -m3 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/ 2>/dev/null) gpu=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader 2>/dev/null) $(grep -hoE "No module named '[^']+'" /root/boot.log /root/bridge.log /root/rtlk.log /root/app.log 2>/dev/null | sort -u | tr '\n' ' ')"
    fi
    sleep 5
  done
  return 1
}
BRAIN=0
if [ "$BRANCH" = none ]; then
  say "stage 7: skipped -- no working torch"; echo FAILED > "$OUT/STACK"
else
  say "stage 7: boot (bridge NOVA_FACE=ditto, brain env -u NOVA_FACE)"
  if boot_once 1; then BRAIN=1; say "stage 7: BRAIN_UP"; else
    miss=$(grep -hoE "No module named '[^']+'" /root/boot.log /root/bridge.log /root/rtlk.log /root/app.log 2>/dev/null \
           | sed "s/No module named '//;s/'//" | cut -d. -f1 | sort -u | tr '\n' ' ')
    say "stage 7: round 1 did not come up. missing: ${miss:-(nothing named)}"
    for m in $miss; do
      case "$m" in torch|torchvision|torchaudio|triton|onnxruntime|tensorflow|scipy|cv2|transformers|diffusers|jax|jaxlib|pandas|mediapipe)
        say "stage 7: $m on the NEVER_INSTALL list -- reported, not installed"; continue;; esac
      say "stage 7: healing -> pip install $m (container AND tree)"
      env -u PYTHONPATH python3 -m pip install --no-input -q "$m" >> "$OUT/heal.log" 2>&1
      env -u PYTHONPATH python3 -m pip install --no-input -q --target "$DP" --no-deps "$m" >> "$OUT/heal.log" 2>&1
    done
    say "stage 7: boot round 2"
    if boot_once 2; then BRAIN=1; say "stage 7: BRAIN_UP on round 2"; fi
  fi
  [ "$BRAIN" = 1 ] && echo UP > "$OUT/STACK" || { say "stage 7 FAILED: :8765 never answered 200"; echo FAILED > "$OUT/STACK"; }
fi
for f in /root/boot.log /root/bridge.log /root/rtlk.log /root/app.log; do
  [ -s "$f" ] && sed -E "$RED" "$f" > "$OUT/$(basename "$f")"
done
grep -hE "NOVA_FACE|\[DITTO" "$OUT/bridge.log" "$OUT/rtlk.log" 2>/dev/null | head -8 | while read -r l; do say "    $l"; done
# the brain must NOT have booted a face of its own
RTLK_FACE=$(grep -c "NOVA_FACE] ditto" "$OUT/rtlk.log" 2>/dev/null || true)
BR_FACE=$(grep -c "NOVA_FACE] ditto" "$OUT/bridge.log" 2>/dev/null || true)
say "stage 7: 'NOVA_FACE] ditto' lines -- bridge=$BR_FACE (want >=1)  brain=$RTLK_FACE (want 0)"

# ---------- stage 8: THE PAGE ASSERTION ----------
say "stage 8: curling the page the brain serves"
{ for p in "/beta/freeze?commercial=1" "/beta/freeze" "/" "/health"; do
    code=$(curl -s -m 15 -o /tmp/_pg -w '%{http_code}' "http://127.0.0.1:8765$p")
    sz=$(stat -c %s /tmp/_pg 2>/dev/null || echo 0)
    jt=$(grep -c "JUDGE-TRUTH" /tmp/_pg 2>/dev/null || true)
    cm=$(grep -c "COMMERCIAL" /tmp/_pg 2>/dev/null || true)
    printf '%-30s http=%s  %s bytes  JUDGE-TRUTH=%s  COMMERCIAL=%s  first100=%s\n' "$p" "$code" "$sz" "${jt:-0}" "${cm:-0}" "$(head -c 100 /tmp/_pg | tr '\n' ' ')"
  done; } > "$OUT/page_probe.txt" 2>&1
cat "$OUT/page_probe.txt"
curl -s -m 20 "http://127.0.0.1:8765/beta/freeze?commercial=1" -o "$OUT/freeze.served.html"
PSZ=$(stat -c %s "$OUT/freeze.served.html" 2>/dev/null || echo 0)
PJT=$(grep -c JUDGE-TRUTH "$OUT/freeze.served.html" 2>/dev/null || echo 0)
PCM=$(grep -c COMMERCIAL "$OUT/freeze.served.html" 2>/dev/null || echo 0)
if [ "$PSZ" -gt 100000 ] && [ "$PJT" -gt 0 ] && [ "$PCM" -gt 0 ]; then
  echo "PASS $PSZ bytes JUDGE-TRUTH x$PJT COMMERCIAL x$PCM" > "$OUT/PAGE_ASSERT"
else
  echo "FAIL $PSZ bytes JUDGE-TRUTH x$PJT COMMERCIAL x$PCM" > "$OUT/PAGE_ASSERT"
fi
say "stage 8: PAGE_ASSERT $(cat "$OUT/PAGE_ASSERT")"

# ---------- stage 9: THE TAKES ----------
run_harness(){   # $1 = tag, $2 = max seconds
  say "stage 9: RECORDING take $1 (engine=$(cat "$OUT/FACE"), max ${2}s)"
  rm -f /root/rec/*.part "$OUT/HARNESS_DONE" "$IN/STOP"
  : > "$OUT/bridge_audio_before.$1.txt"
  grep -c "audio published" /root/bridge.log >> "$OUT/bridge_audio_before.$1.txt" 2>/dev/null || true
  env -u PYTHONPATH python3 "$IN/real_harness.py" --out "$OUT" --inbox "$IN" --rec-dir /root/rec \
     --max-s "$2" \
     --url "http://127.0.0.1:8765/beta/freeze?commercial=1" \
     > "$OUT/harness.$1.log" 2>&1
  local rc=$?
  say "stage 9: take $1 harness rc=$rc -- $(tail -1 "$OUT/harness.$1.log")"
  for n in live_intro.mp4 live_intro.webm live_intro.json ws.jsonl console.log STATUS page_end.png; do
    [ -e "$OUT/$n" ] && cp "$OUT/$n" "$OUT/take$1.$n" 2>/dev/null
  done
  for f in /root/bridge.log /root/rtlk.log /root/app.log; do
    [ -s "$f" ] && sed -E "$RED" "$f" > "$OUT/$(basename "$f" .log).take$1.log"
  done
  cp "/workspace/gallery/wd/ditto_stats.json" "$OUT/ditto_stats.take$1.json" 2>/dev/null
  say "stage 9: take $1 mp4 = $(stat -c %s "$OUT/take$1.live_intro.mp4" 2>/dev/null || echo 0) bytes"
  say "stage 9: take $1 $(grep -o 'VERIFY .*' "$OUT/take$1.STATUS" 2>/dev/null | tail -1)"
  echo READY > "$OUT/TAKE$1_READY"
}
audio_proof(){
  AIN=$(grep -oE "audio IN [0-9]+" /root/bridge.log 2>/dev/null | tail -1 | awk '{print $3}')
  AN=$(grep -oE "audio published [0-9]+" /root/bridge.log 2>/dev/null | tail -1 | awk '{print $3}')
  say "stage 9: AUDIO PROOF -- engine->bridge 'audio IN' = ${AIN:-0} frames, LiveKit 'audio published' = ${AN:-0} frames"
  echo "audio_IN=${AIN:-0} audio_published=${AN:-0}" > "$OUT/AUDIO_PROOF"
  [ "${AN:-0}" -ge 100 ] 2>/dev/null && echo OK >> "$OUT/AUDIO_PROOF" || echo WEAK >> "$OUT/AUDIO_PROOF"
}
if [ "$BRAIN" != 1 ]; then
  say "stage 9: no stack -> NO RECORDING. Not pretending otherwise."
else
  say "stage 9: take 0 is the AUDIO PROOF run -- she greets, nobody answers, 45 s"
  run_harness 0 45
  audio_proof
  say "stage 9: waiting up to 15 min for /root/in/GO (the real take)"
  for i in $(seq 1 180); do [ -e "$IN/GO" ] && break; sleep 5; done
  if [ ! -e "$IN/GO" ]; then say "stage 9: no GO -- skipping the real take"; else
    run_harness 1 "${REC_MAX_S:-110}"
    audio_proof
    say "stage 9: waiting up to 8 min for /root/in/GO2 or /root/in/NO_MORE"
    for i in $(seq 1 96); do [ -e "$IN/GO2" ] && break; [ -e "$IN/NO_MORE" ] && break; sleep 5; done
    if [ -e "$IN/GO2" ]; then run_harness 2 "${REC_MAX_S2:-110}"; audio_proof; fi
  fi
fi
cp "$LOG/ditto_server.log" "$OUT/ditto_server_end.log" 2>/dev/null
curl -s -m 10 127.0.0.1:8031/health > "$OUT/health_ditto_end.json" 2>&1
cp "/workspace/gallery/wd/ditto_stats.json" "$OUT/ditto_stats_end.json" 2>/dev/null
cp "/workspace/gallery/wd/ditto.log" "$OUT/ditto_sidecar.log" 2>/dev/null
for f in /root/bridge.log /root/rtlk.log /root/app.log; do
  [ -s "$f" ] && sed -E "$RED" "$f" > "$OUT/$(basename "$f")"
done
ls -la "$OUT" > "$OUT/LISTING" 2>&1
echo READY > "$OUT/PULLABLE"
say "ALL DONE -- waiting up to 25 min for /root/in/PULLED, then putting everything back"

# ---------- stage 10: leave the production volume as found ----------
for i in $(seq 1 300); do [ -s "$IN/PULLED" ] && break; sleep 5; done
python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert.txt" 2>&1
say "stage 10: revert lk_bridge.py rc=$? -- $(grep -E 'REVERTED|no .bak' "$OUT/revert.txt" | head -1)"
rm -f /workspace/lk_bridge.py.bak-ditto-* /workspace/nova_ditto.py
if [ -s /root/freeze.html.orig ]; then
  cp /root/freeze.html.orig "$PG.novaditto-restore" && mv "$PG.novaditto-restore" "$PG"
  say "stage 10: page restored -> $(stat -c %s "$PG") bytes"
fi
md5sum /workspace/lk_bridge.py /workspace/rt_lk.py "$PG" > "$OUT/volume_md5_end.txt" 2>&1
cat "$OUT/volume_md5_end.txt"
say "stage 10 DONE: $(tr '\n' ' ' < "$OUT/volume_md5_end.txt")"
echo 0 > "$OUT/RC"
