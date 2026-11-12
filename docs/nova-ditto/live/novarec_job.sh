#!/usr/bin/env bash
# novarec_job.sh -- session novarec, 2026-11-01. ONE pod. ONE job: the mp4.
#
# Everything here is built on facts the previous session (novafix-intro) measured and wrote
# down in docs/LIVE-INTRO.md and docs/nova-ditto/live/torchfix/README.md:
#   * the volume's pages are RESTORED (beta/freeze.html 147542 B, 0 zero-byte files)
#   * Ditto comes ready on nova_fb_bank in 150-175 s, out_wh 1074x1920
#   * the bridge patch applies cleanly in the order --revert -> --probe -> --apply
#   * THE blocker was ONE file: torch/lib/libtorch_global_deps.so. It is stage 1 here.
#   * boot.sh's step 3 pip gate is `import flask,edge_tts,websockets` -- it PASSES on this
#     volume, so boot.sh never installs aiortc, and the bridge then dies on
#     `No module named 'aiortc'` (pod4, 04:09). So aiortc/av are repaired in stage 5,
#     BEFORE boot, in both the volume tree and the container.
set -uo pipefail
cd /root || exit 9
IN=/root/in; OUT=/root/novarec_out; MT=/root/mt; LOG=/root/logs
DP=/workspace/_sys/pylibs311_good/dist-packages
mkdir -p "$OUT" "$MT/maya-ops/lt" "$MT/bench/replace_musetalk_alt" "$LOG" /root/rec
say(){ local m="[job $(date -u +%H:%M:%S)] $*"; echo "$m"; echo "$m" >> "$OUT/STAGES"; }
: > "$OUT/STAGES"
RED='s#(https?://)[^/@[:space:]]+@#\1<REDACTED-TOKEN>@#g; s#x-access-token:[A-Za-z0-9_-]+#x-access-token:<REDACTED>#g; s#gh[psuor]_[A-Za-z0-9]{16,}#<REDACTED>#g'

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

# ---------- stage 1: THE TORCH FILE. One cp. Nothing else is attempted on torch. ----------
say "stage 1: putting torch/lib/libtorch_global_deps.so back"
{
  echo "uploaded: $(stat -c %s "$IN/libtorch_global_deps.so") bytes  sha256=$(sha256sum "$IN/libtorch_global_deps.so" | cut -d' ' -f1)"
  echo "expected: 17353 bytes  sha256=2eaab74d60647976a45caf4e0643d8b1b568f7202aa1cc861fdff70cea8dbf48"
  echo "--- before ---"
  ls -l "$DP/torch/lib/libtorch_global_deps.so" 2>&1
  PYTHONPATH="$DP" python3 -c "import torch;print('torch',torch.__version__)" 2>&1 | tail -2
} > "$OUT/torchfix.txt" 2>&1
cp "$IN/libtorch_global_deps.so" "$DP/torch/lib/libtorch_global_deps.so"
CPRC=$?
{
  echo "--- cp rc=$CPRC ---"
  ls -l "$DP/torch/lib/libtorch_global_deps.so" 2>&1
  echo "--- after ---"
  for m in torch torchvision; do
    printf '%-12s ' "$m"
    PYTHONPATH="$DP" python3 -c "import $m;print('OK',$m.__version__)" 2>&1 | tail -1
  done
} >> "$OUT/torchfix.txt" 2>&1
cat "$OUT/torchfix.txt"
TOK=$(PYTHONPATH="$DP" python3 -c "import torch,torchvision;print('BOTH_OK')" 2>&1 | tail -1)
say "stage 1: $TOK"
if [ "$TOK" != "BOTH_OK" ]; then
  say "stage 1 FAILED -- torch/torchvision still do not import. The exact error:"
  PYTHONPATH="$DP" python3 -c "import torch" 2>&1 | tail -4 | while read -r l; do say "    $l"; done
  PYTHONPATH="$DP" python3 -c "import torchvision" 2>&1 | tail -4 | while read -r l; do say "    $l"; done
  echo TORCH_FAILED > "$OUT/TORCH"
  say "STOPPING as instructed: not improvising further torch work."
  echo 12 > "$OUT/RC"; exit 12
fi
echo TORCH_OK > "$OUT/TORCH"

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
  export PYTHONPATH="$IN"
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

# ---------- stage 4: Chromium. SERIAL after apt (that was attempt 2's bug 1). ----------
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
say "stage 5: repairing $DP (container pip, PYTHONPATH unset)"
python3 -I "$IN/repair_pylibs.py" --dist-packages "$DP" --repair --rounds 24 \
  --targets "flask,livekit.api,livekit.rtc,aiohttp,requests,numpy,edge_tts,pip,websockets,soundfile,av,aiortc,cv2" \
  --report "$OUT/pylibs_repair.json" > "$OUT/pylibs_repair.txt" 2>&1
say "stage 5: repair rc=$?"
# belt and braces: the CONTAINER must also be able to import aiortc/av, because boot.sh's
# own pip step is gated on `import flask,edge_tts,websockets` and never runs on this volume.
env -u PYTHONPATH python3 -c "import aiortc" 2>/dev/null \
  || env -u PYTHONPATH python3 -m pip install -q aiortc av >> "$OUT/pylibs_repair.txt" 2>&1
{ for m in torch torchvision aiortc av flask edge_tts websockets numpy cv2 scipy soundfile livekit.rtc pip; do
    printf '%-14s ' "$m"
    PYTHONPATH="$DP" python3 -c "import $m;print('OK',getattr($m,'__version__','?'))" 2>&1 | tail -1
  done; } > "$OUT/imports.txt" 2>&1
cat "$OUT/imports.txt"
say "stage 5: $(grep -c ' OK ' "$OUT/imports.txt") of 13 import OK"

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
boot_once(){   # $1 = tag, $2 = face
  for pat in "[r]t_lk.py" "[l]k_bridge.py" "[b]oot.sh" "[a]pp.py"; do pkill -f "$pat" 2>/dev/null; done
  sleep 3
  export NOVA_DEPLOY_BRANCH=nova-ditto NOVA_DITTO_DELAY_SITE=bridge
  if [ "$2" = ditto ]; then export NOVA_FACE=ditto; else unset NOVA_FACE; fi
  unset PYTHONPATH
  setsid nohup bash /workspace/boot.sh > "$OUT/bootwrap.$1.log" 2>&1 < /dev/null &
  for i in $(seq 1 72); do        # 6 min
    [ "$(curl -s -m 4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/ 2>/dev/null)" = "200" ] && return 0
    sleep 5
  done
  return 1
}
# the deploy inside boot.sh rewrites /workspace/pages. On 2026-11-01 an out-of-quota volume
# made every cp truncate its target. Guard it: if freeze.html comes back small, put the
# uploaded copy back (the harness does the same check again before it opens the page).
page_guard(){
  local f=/workspace/pages/beta/freeze.html
  local sz; sz=$(stat -c %s "$f" 2>/dev/null || echo 0)
  say "    page guard: beta/freeze.html = $sz bytes"
  if [ "$sz" -lt 100000 ] && [ -s "$IN/beta__freeze.html" ]; then
    cp "$IN/beta__freeze.html" "$f.novarec-new" && mv "$f.novarec-new" "$f"
    say "    page guard: RESTORED from the uploaded copy -> $(stat -c %s "$f") bytes"
  fi
}
BRAIN=0
say "stage 7: boot.sh (NOVA_FACE=$FACE)"
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
  say "stage 7: boot.sh round 2"
  if boot_once 2 "$FACE"; then BRAIN=1; say "stage 7: BRAIN_UP on round 2"; fi
fi
page_guard
for f in /root/boot.log /root/bridge.log /root/rtlk.log /root/app.log; do
  [ -s "$f" ] && sed -E "$RED" "$f" > "$OUT/$(basename "$f")"
done
[ "$BRAIN" = 1 ] && echo UP > "$OUT/STACK" || { say "stage 7 FAILED: :8765 never answered 200"; echo FAILED > "$OUT/STACK"; }
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

# ---------- stage 9: THE RECORDING. Up to two takes: ditto, then musetalk on request. ----------
run_harness(){   # $1 = tag
  say "stage 9: RECORDING take $1 (engine=$(cat "$OUT/FACE"))"
  rm -f /root/rec/*.part "$OUT/HARNESS_DONE"
  env -u PYTHONPATH python3 "$IN/real_harness.py" --out "$OUT" --inbox "$IN" --rec-dir /root/rec \
     --max-s "${REC_MAX_S:-260}" \
     --url "http://127.0.0.1:8765/beta/freeze?intro=freeze|http://127.0.0.1:8765/freeze?intro=freeze" \
     > "$OUT/harness.$1.log" 2>&1
  local rc=$?
  say "stage 9: take $1 harness rc=$rc -- $(tail -1 "$OUT/harness.$1.log")"
  for n in live_intro.mp4 live_intro.json ws.jsonl console.log STATUS page_end.png; do
    [ -e "$OUT/$n" ] && cp "$OUT/$n" "$OUT/take$1.$n" 2>/dev/null
  done
  say "stage 9: take $1 mp4 = $(stat -c %s "$OUT/live_intro.mp4" 2>/dev/null || echo 0) bytes"
}

if [ "$BRAIN" != 1 ]; then
  say "stage 9: no stack -> NO RECORDING. Not pretending otherwise."
else
  say "stage 9: waiting up to 15 min for /root/in/GO"
  for i in $(seq 1 180); do [ -e "$IN/GO" ] && break; sleep 5; done
  if [ ! -e "$IN/GO" ]; then say "stage 9: no GO -- skipping"; else
    run_harness 1
    # off-pod fallback switch: if Ditto carried no audio, PUT GO_MUSETALK and we redo the
    # same conversation on MuseTalk rather than hand back nothing.
    say "stage 9: waiting up to 6 min for /root/in/GO_MUSETALK (or /root/in/NO_MORE)"
    for i in $(seq 1 72); do [ -e "$IN/GO_MUSETALK" ] && break; [ -e "$IN/NO_MORE" ] && break; sleep 5; done
    if [ -e "$IN/GO_MUSETALK" ]; then
      say "stage 9: switching to MuseTalk on request"
      python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert_to_mt.txt" 2>&1
      say "stage 9: revert rc=$? -- $(grep -E 'REVERTED|no .bak' "$OUT/revert_to_mt.txt" | head -1)"
      echo musetalk > "$OUT/FACE"
      if boot_once mt musetalk; then
        say "stage 9: BRAIN_UP on MuseTalk"
        rm -f "$IN/STOP"
        run_harness 2
      else
        say "stage 9: MuseTalk boot failed -- keeping take 1"
      fi
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
say "ALL DONE -- waiting up to 20 min for /root/in/PULLED, then reverting"

# ---------- stage 10: leave the production volume as found ----------
for i in $(seq 1 240); do [ -s "$IN/PULLED" ] && break; sleep 5; done
python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert.txt" 2>&1
say "stage 10: revert lk_bridge.py rc=$? -- $(grep -E 'REVERTED|no .bak' "$OUT/revert.txt" | head -1)"
rm -f /workspace/lk_bridge.py.bak-ditto-* /workspace/nova_ditto.py
md5sum /workspace/lk_bridge.py /workspace/rt_lk.py > "$OUT/volume_md5_end.txt" 2>&1
say "stage 10 DONE: $(tr '\n' ' ' < "$OUT/volume_md5_end.txt")"
echo 0 > "$OUT/RC"
