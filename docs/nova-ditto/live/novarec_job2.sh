#!/usr/bin/env bash
# novarec_job2.sh -- session novarec, 2026-11-02, pod 2. ONE job: the mp4.
#
# WHAT POD 1 MEASURED, 90 s in, and why this script exists:
#   docs/nova-ditto/live/torchfix/README.md says ONE file is missing from the volume's torch
#   and gives the cp. The cp FAILS:
#     cp: cannot create regular file
#       '/workspace/_sys/pylibs311_good/dist-packages/torch/lib/libtorch_global_deps.so':
#       No such file or directory
#   ENOENT on create = the PARENT DIRECTORY is gone, so `torch/lib/` itself was removed by the
#   interrupted `pip install --upgrade torch`, not just that one member. The README's premise
#   is wrong, and no single cp can fix it.
#
# So stage 1 here: measure the tree first, then take the cheapest branch that works.
#   branch A  torch/lib exists and holds the big .so set -> cp the one file in (17 KB).
#   branch C  torch/lib is gone -> a 2.5 GB wheel CANNOT go on this volume (a 2 GB write
#             failed on 2026-11-02), so torch goes on the CONTAINER disk at /root/torchfix
#             (60 GB free) and is put FIRST on PYTHONPATH. The volume is never written.
#             boot.sh hardcodes `export PYTHONPATH=<volume tree>`, so branch C runs a copy of
#             boot.sh at /root/boot_novarec.sh with that ONE line rewritten. Nothing else
#             changes and the volume's boot.sh is untouched.
#
# There is also a CMD channel (stage 0b): PUT a shell script to /root/in/CMD and it runs once,
# output to $OUT/CMD_OUT.<time>. Pod 1 died useless because a one-line question needed a whole
# new pod. This session does not get to make that mistake twice.
set -uo pipefail
cd /root || exit 9
IN=/root/in; OUT=/root/novarec_out; MT=/root/mt; LOG=/root/logs
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
say "stage 0b: CMD channel open (PUT /put/CMD -> runs once -> novarec_out/CMD_OUT.<hhmmss>)"

need="novalive_job.sh repair_pylibs.py real_harness.py ditto_bridge_patch.py nova_ditto.py \
ditto_server.py ditto_up.sh ditto_wide.py motion_bank.py ditto_fullbody.py sitecustomize.py \
nova_fb_bank.mp4 nova_fb_bank.json libtorch_global_deps.so PAYLOAD_DONE"
say "stage 0: waiting for the payload"
for i in $(seq 1 240); do
  ok=1; for f in $need; do [ -s "$IN/$f" ] || ok=0; done
  [ $ok = 1 ] && break; sleep 5
done
for f in $need; do [ -s "$IN/$f" ] || { say "MISSING $f -- abort"; exit 11; }; done
say "stage 0 OK"

# ---------- stage 1a: MEASURE the torch tree. No guessing. ----------
say "stage 1a: measuring the volume's torch tree"
{
  echo "### mounts and the path down to torch"
  for p in /workspace /workspace/_sys /workspace/_sys/pylibs311_good "$DP" "$DP/torch" "$DP/torch/lib"; do
    printf '%-70s ' "$p"; ls -ld "$p" 2>&1 | tail -1
  done
  echo; echo "### $DP/torch, top level (first 40)"
  ls -1 "$DP/torch" 2>&1 | head -40
  echo; echo "### $DP/torch/lib listing"
  ls -la "$DP/torch/lib" 2>&1 | head -40
  echo; echo "### .so count and total size under $DP/torch"
  find "$DP/torch" -name '*.so*' -type f 2>/dev/null | wc -l
  du -sh "$DP/torch" 2>/dev/null
  echo; echo "### is a torch wheel's RECORD still there?"
  ls -1 "$DP" 2>/dev/null | grep -i '^torch' | head
  echo; echo "### write probe on the volume (1 MB)"
  dd if=/dev/zero of="$DP/.novarec_write_probe" bs=1M count=1 2>&1 | tail -1
  rm -f "$DP/.novarec_write_probe"
  echo; echo "### container disk"
  df -h / | tail -1
} > "$OUT/torch_tree.txt" 2>&1
cat "$OUT/torch_tree.txt"
NSO=$(find "$DP/torch" -name '*.so*' -type f 2>/dev/null | wc -l)
say "stage 1a: torch/lib exists? $([ -d "$DP/torch/lib" ] && echo yes || echo NO) ; .so files under torch = $NSO"

# ---------- stage 1b: the cheapest branch that actually works ----------
BRANCH=none
if [ -d "$DP/torch/lib" ]; then
  say "stage 1b: BRANCH A -- torch/lib is there, putting the 17 KB file back"
  cp "$IN/libtorch_global_deps.so" "$DP/torch/lib/libtorch_global_deps.so" 2>> "$OUT/torchfix.txt"
  say "stage 1b: cp rc=$?"
  if PYTHONPATH="$DP" python3 -c "import torch,torchvision" 2>>"$OUT/torchfix.txt"; then
    BRANCH=A; say "stage 1b: BRANCH A OK -- torch $(PYTHONPATH="$DP" python3 -c 'import torch;print(torch.__version__)' 2>/dev/null)"
  else
    say "stage 1b: BRANCH A did not fix the import -- falling through to C"
  fi
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
        --index-url https://download.pytorch.org/whl/cu129 \
        "torch==2.9.1+cu129" torchvision ) >> "$OUT/torch_container.log" 2>&1
    TRC=$?
  fi
  say "stage 1b: pip rc=$TRC -- $(du -sh "$TFX" 2>/dev/null | cut -f1) on the container disk"
  tail -6 "$OUT/torch_container.log" | while read -r l; do say "    $l"; done
  if PYTHONPATH="$TFX:$DP" python3 -c "import torch,torchvision;print(torch.__version__,torchvision.__version__)" > "$OUT/torch_container_import.txt" 2>&1; then
    BRANCH=C; say "stage 1b: BRANCH C OK -- $(cat "$OUT/torch_container_import.txt")"
  else
    say "stage 1b: BRANCH C FAILED:"; tail -5 "$OUT/torch_container_import.txt" | while read -r l; do say "    $l"; done
  fi
fi
echo "$BRANCH" > "$OUT/BRANCH"

# PYPATH is what every later stage and the boot wrapper must use.
if [ "$BRANCH" = C ]; then PYPATH="$TFX:$DP"; else PYPATH="$DP"; fi
echo "$PYPATH" > "$OUT/PYPATH"
say "stage 1 DONE: branch=$BRANCH  PYTHONPATH=$PYPATH"
if [ "$BRANCH" = none ]; then
  say "stage 1: NO WORKING TORCH. The stack cannot start. Dumping evidence and holding on the CMD channel."
  echo NO_TORCH > "$OUT/TORCH"
else
  echo "OK $BRANCH" > "$OUT/TORCH"
fi

# the boot wrapper: boot.sh byte-for-byte except the one hardcoded PYTHONPATH line.
BOOTSH=/workspace/boot.sh
if [ "$BRANCH" = C ] && [ -s "$BOOTSH" ]; then
  sed "s#^export PYTHONPATH=/workspace/_sys/pylibs311_good/dist-packages\$#export PYTHONPATH=$PYPATH#" \
      "$BOOTSH" > /root/boot_novarec.sh
  if grep -q "^export PYTHONPATH=$PYPATH\$" /root/boot_novarec.sh; then
    BOOTUSE=/root/boot_novarec.sh
    say "stage 1: boot wrapper /root/boot_novarec.sh -- the ONE PYTHONPATH line rewritten, diff:"
    diff <(cat "$BOOTSH") /root/boot_novarec.sh | head -6 | while read -r l; do say "    $l"; done
  else
    BOOTUSE="$BOOTSH"; say "stage 1: WARN -- could not rewrite the PYTHONPATH line, using boot.sh as is"
  fi
else
  BOOTUSE="$BOOTSH"
fi
say "stage 1: booting with $BOOTUSE"

# ---------- stage 2: the C headers Ditto needs. FOREGROUND: it owns the dpkg lock. ----------
say "stage 2: apt python3.10-dev + build-essential (foreground -- owns the dpkg lock)"
( apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3.10-dev build-essential ) > "$OUT/aptdev.log" 2>&1
[ -e /usr/include/python3.10/Python.h ] && say "stage 2 OK: Python.h present" || say "stage 2 WARN: Python.h MISSING"

# ---------- stage 3: Ditto, in the BACKGROUND now that apt has finished ----------
cp "$IN/ditto_server.py" "$IN/ditto_up.sh" "$IN/motion_bank.py" "$MT/maya-ops/lt/"
cp "$IN/ditto_wide.py" "$MT/bench/replace_musetalk_alt/"
chmod +x "$MT/maya-ops/lt/ditto_up.sh"
say "stage 3: ditto_up.sh in the background (ready in 150-175 s on this volume)"
(
  export PYTHONPATH="$IN:$PYPATH"
  export DITTO_FB_ON=1 DITTO_FB_SHIM="$IN" DITTO_FB_BENCH="$MT/bench/replace_musetalk_alt"
  export DITTO_FB_UP="${FB_UP:-3.0}" DITTO_FB_BOX="${FB_BOX:-263,215,763,715}"
  export DITTO_ROOT=/root/ditto MAYA_LOGS="$LOG" DITTO_PORT=8031
  export DITTO_AMP=0.6 DITTO_CHUNK=25 DITTO_PRIME=35 DITTO_VAD=1 DITTO_THREADS=6 DITTO_EYE_HOLD=1
  export DITTO_WAIT_SEC=1500
  export DITTO_OUT_W=1074 DITTO_OUT_H=1920        # DITTO-FULLBODY section 4
  export DITTO_SRC="$IN/nova_fb_bank.mp4" DITTO_BANK="$IN/nova_fb_bank.json"
  bash "$MT/maya-ops/lt/ditto_up.sh" > "$OUT/ditto_up.log" 2>&1
  echo "$?" > "$OUT/DITTO_RC"
) &

# ---------- stage 4: Chromium. SERIAL after apt (attempt 2's bug 1). ----------
say "stage 4: playwright + chromium (serial, after apt released the lock)"
( env -u PYTHONPATH python3 -m pip install -q playwright \
  && env -u PYTHONPATH python3 -m playwright install --with-deps chromium ) > "$OUT/playwright.log" 2>&1 \
  && echo READY > "$OUT/PW_READY"
if [ ! -s "$OUT/PW_READY" ]; then
  say "stage 4: first try failed, retrying chromium without --with-deps"
  ( env -u PYTHONPATH python3 -m playwright install chromium ) >> "$OUT/playwright.log" 2>&1 && echo READY > "$OUT/PW_READY"
fi
env -u PYTHONPATH python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=['--no-sandbox']); print('CHROMIUM OK', b.version); b.close()
" > "$OUT/chromium_check.txt" 2>&1
say "stage 4: $(tail -1 "$OUT/chromium_check.txt")"

# ---------- stage 5: the import set the stack ACTUALLY needs, incl. aiortc ----------
# boot.sh's own pip step is gated on `import flask,edge_tts,websockets`, which PASSES on this
# volume, so boot.sh never installs aiortc and the bridge dies on it (pod4, 04:09). Fixed here.
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

# ---------- stage 6: the bridge -- revert to pristine, probe 4/4, then apply ----------
say "stage 6: --revert to the pristine original (a previous session left it patched)"
python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert_pre.txt" 2>&1
say "stage 6: revert rc=$? -- $(grep -E 'REVERTED|no .bak' "$OUT/revert_pre.txt" | head -1)"
say "stage 6: waiting for Ditto to be ready before touching the bridge"
DITTO_OK=0
for i in $(seq 1 60); do
  curl -s -m 8 127.0.0.1:8031/health > "$OUT/health_ditto.json" 2>/dev/null
  grep -q '"ready": *true' "$OUT/health_ditto.json" 2>/dev/null && { DITTO_OK=1; say "stage 6: Ditto ready after $((i*5))s"; break; }
  sleep 5
done
cp "$LOG/ditto_server.log" "$OUT/ditto_server.log" 2>/dev/null
[ "$DITTO_OK" = 1 ] || { say "stage 6: Ditto NOT ready -- MuseTalk"; tail -20 "$OUT/ditto_up.log"; }

FACE=musetalk
if [ "$DITTO_OK" = 1 ]; then
  python3 -I "$IN/ditto_bridge_patch.py" --probe --wd "$OUT" > "$OUT/probe.txt" 2>&1; PRC=$?
  say "stage 6: probe rc=$PRC"; grep -E "md5|A[1-4]|already patched" "$OUT/probe.txt" | head -8
  if [ "$PRC" = 0 ]; then
    python3 -I "$IN/ditto_bridge_patch.py" --apply --sidecar "$IN/nova_ditto.py" --wd "$OUT" \
      > "$OUT/apply.txt" 2>&1; ARC=$?
    say "stage 6: apply rc=$ARC -- $(grep -E 'APPLIED|already patched|REFUSING' "$OUT/apply.txt" | head -1)"
    if [ "$ARC" = 0 ]; then FACE=ditto; else
      say "stage 6: apply refused -- REVERTING and staying on MuseTalk"
      python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert_early.txt" 2>&1
    fi
  else
    say "stage 6: probe is not 4/4 -- NOT applying, REVERTING, MuseTalk"
    python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert_early.txt" 2>&1
  fi
fi
echo "$FACE" > "$OUT/FACE"
say "stage 6 DONE: face engine = $FACE"

# ---------- stage 7: boot the stack ----------
page_guard(){
  local f=/workspace/pages/beta/freeze.html
  local sz; sz=$(stat -c %s "$f" 2>/dev/null || echo 0)
  say "    page guard: beta/freeze.html = $sz bytes"
  if [ "$sz" -lt 100000 ] && [ -s "$IN/beta__freeze.html" ]; then
    cp "$IN/beta__freeze.html" "$f.novarec-new" && mv "$f.novarec-new" "$f"
    say "    page guard: RESTORED from the uploaded copy -> $(stat -c %s "$f") bytes"
  fi
}
boot_once(){   # $1 = tag, $2 = face
  for pat in "[r]t_lk.py" "[l]k_bridge.py" "[b]oot.sh" "[b]oot_novarec.sh" "[a]pp.py"; do pkill -f "$pat" 2>/dev/null; done
  sleep 3
  export NOVA_DEPLOY_BRANCH=nova-ditto NOVA_DITTO_DELAY_SITE=bridge
  if [ "$2" = ditto ]; then export NOVA_FACE=ditto; else unset NOVA_FACE; fi
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
  say "stage 7: skipped -- no working torch"
  echo FAILED > "$OUT/STACK"
else
  say "stage 7: boot (NOVA_FACE=$FACE)"
  if boot_once 1 "$FACE"; then BRAIN=1; say "stage 7: BRAIN_UP"; else
    page_guard
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
    if boot_once 2 "$FACE"; then BRAIN=1; say "stage 7: BRAIN_UP on round 2"; fi
  fi
  page_guard
  [ "$BRAIN" = 1 ] && echo UP > "$OUT/STACK" || { say "stage 7 FAILED: :8765 never answered 200"; echo FAILED > "$OUT/STACK"; }
fi
for f in /root/boot.log /root/bridge.log /root/rtlk.log /root/app.log; do
  [ -s "$f" ] && sed -E "$RED" "$f" > "$OUT/$(basename "$f")"
done
grep -h "NOVA_FACE" "$OUT/bridge.log" "$OUT/rtlk.log" 2>/dev/null | head -4 | while read -r l; do say "    $l"; done

# ---------- stage 8: THE PAGE ASSERTION (never completed before) ----------
say "stage 8: curling the page the brain serves"
{ for p in "/beta/freeze?intro=freeze" "/freeze?intro=freeze" "/" "/health"; do
    code=$(curl -s -m 15 -o /tmp/_pg -w '%{http_code}' "http://127.0.0.1:8765$p")
    sz=$(stat -c %s /tmp/_pg 2>/dev/null || echo 0)
    jt=$(grep -c "JUDGE-TRUTH" /tmp/_pg 2>/dev/null || true)
    printf '%-28s http=%s  %s bytes  JUDGE-TRUTH=%s  first100=%s\n' "$p" "$code" "$sz" "${jt:-0}" "$(head -c 100 /tmp/_pg | tr '\n' ' ')"
  done; } > "$OUT/page_probe.txt" 2>&1
cat "$OUT/page_probe.txt"
curl -s -m 20 "http://127.0.0.1:8765/beta/freeze?intro=freeze" -o "$OUT/freeze.served.html"
PSZ=$(stat -c %s "$OUT/freeze.served.html" 2>/dev/null || echo 0)
PJT=$(grep -c JUDGE-TRUTH "$OUT/freeze.served.html" 2>/dev/null || echo 0)
if [ "$PSZ" -gt 0 ] && [ "$PJT" -gt 0 ]; then
  echo "PASS $PSZ bytes JUDGE-TRUTH x$PJT" > "$OUT/PAGE_ASSERT"
else
  echo "FAIL $PSZ bytes JUDGE-TRUTH x$PJT" > "$OUT/PAGE_ASSERT"
fi
say "stage 8: PAGE_ASSERT $(cat "$OUT/PAGE_ASSERT")"

# ---------- stage 9: THE RECORDING ----------
run_harness(){   # $1 = tag
  say "stage 9: RECORDING take $1 (engine=$(cat "$OUT/FACE"))"
  rm -f /root/rec/*.part "$OUT/HARNESS_DONE" "$IN/STOP"
  env -u PYTHONPATH python3 "$IN/real_harness.py" --out "$OUT" --inbox "$IN" --rec-dir /root/rec \
     --max-s "${REC_MAX_S:-260}" \
     --url "http://127.0.0.1:8765/beta/freeze?intro=freeze|http://127.0.0.1:8765/freeze?intro=freeze" \
     > "$OUT/harness.$1.log" 2>&1
  local rc=$?
  say "stage 9: take $1 harness rc=$rc -- $(tail -1 "$OUT/harness.$1.log")"
  for n in live_intro.mp4 live_intro.webm live_intro.json ws.jsonl console.log STATUS page_end.png; do
    [ -e "$OUT/$n" ] && cp "$OUT/$n" "$OUT/take$1.$n" 2>/dev/null
  done
  say "stage 9: take $1 mp4 = $(stat -c %s "$OUT/take$1.live_intro.mp4" 2>/dev/null || echo 0) bytes"
  echo READY > "$OUT/TAKE$1_READY"
}
if [ "$BRAIN" != 1 ]; then
  say "stage 9: no stack -> NO RECORDING. Not pretending otherwise."
else
  say "stage 9: waiting up to 15 min for /root/in/GO"
  for i in $(seq 1 180); do [ -e "$IN/GO" ] && break; sleep 5; done
  if [ ! -e "$IN/GO" ]; then say "stage 9: no GO -- skipping"; else
    run_harness 1
    say "stage 9: waiting up to 8 min for /root/in/GO2 (another take) or /root/in/NO_MORE"
    for i in $(seq 1 96); do
      [ -e "$IN/GO2" ] && break; [ -e "$IN/NO_MORE" ] && break; sleep 5
    done
    if [ -e "$IN/GO2" ]; then
      WANT=$(cat "$IN/GO2" 2>/dev/null | tr -d '[:space:]')
      say "stage 9: second take requested, engine=${WANT:-same}"
      if [ "$WANT" = musetalk ] && [ "$FACE" = ditto ]; then
        python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert_to_mt.txt" 2>&1
        say "stage 9: revert rc=$? -- $(grep -E 'REVERTED|no .bak' "$OUT/revert_to_mt.txt" | head -1)"
        echo musetalk > "$OUT/FACE"
        boot_once mt musetalk && say "stage 9: BRAIN_UP on MuseTalk" || say "stage 9: MuseTalk boot failed"
      fi
      run_harness 2
    fi
  fi
fi
for f in /root/bridge.log /root/rtlk.log /root/app.log; do
  [ -s "$f" ] && sed -E "$RED" "$f" > "$OUT/$(basename "$f")"
done
cp "$LOG/ditto_server.log" "$OUT/ditto_server_end.log" 2>/dev/null
curl -s -m 10 127.0.0.1:8031/health > "$OUT/health_ditto_end.json" 2>&1
ls -la "$OUT" > "$OUT/LISTING" 2>&1
echo READY > "$OUT/PULLABLE"
say "ALL DONE -- waiting up to 25 min for /root/in/PULLED, then reverting"

# ---------- stage 10: leave the production volume as found ----------
for i in $(seq 1 300); do [ -s "$IN/PULLED" ] && break; sleep 5; done
python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert.txt" 2>&1
say "stage 10: revert lk_bridge.py rc=$? -- $(grep -E 'REVERTED|no .bak' "$OUT/revert.txt" | head -1)"
rm -f /workspace/lk_bridge.py.bak-ditto-* /workspace/nova_ditto.py
md5sum /workspace/lk_bridge.py /workspace/rt_lk.py > "$OUT/volume_md5_end.txt" 2>&1
say "stage 10 DONE: $(tr '\n' ' ' < "$OUT/volume_md5_end.txt")"
echo 0 > "$OUT/RC"
