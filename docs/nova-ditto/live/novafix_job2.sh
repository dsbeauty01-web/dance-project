#!/usr/bin/env bash
# novafix_job2.sh -- session novafix-intro, attempt 2, 2026-11-02.
#
# What attempt 1 (pod mcyb9x7k84u18p) achieved and what it broke, both measured:
#
#   WON  the quota: 2.1 GB freed from the allow-list. Before: a 1 MB write failed with
#        Errno 122. After: 512 MB writes fine (2 GB still does not).
#   WON  the pages: the normal deploy at NOVA_DEPLOY_BRANCH=nova-ditto rewrote them.
#        72 of 86 files that were 0 bytes are non-zero; beta/freeze.html is 147542 bytes.
#        The 14 left at 0 are all *.novalive-new -- the PREVIOUS session's abandoned temp
#        files, not pages, and nothing references them.
#   WON  the face engine: Ditto ready in 175 s on the full-body bank, and the bridge patch
#        probed 4/4 and APPLIED (rc=0) -- the step the quota blocked on 2026-11-01.
#   BROKE the python tree. Deleting *.pyc is safe for a normal install and was NOT safe
#        here: /workspace/_sys/pylibs311_good/dist-packages is MIXED, and part of it is in
#        the legacy sourceless layout where pkg/mod.pyc IS the module. The stack died at
#        import -- "No module named 'idna.core'" in the bridge, "No module named 'flask'"
#        and a broken volume pip at boot -- so :8765 never came up and nothing was recorded.
#
# So this job repairs the tree FIRST (stage R), with the CONTAINER's pip and PYTHONPATH
# unset, because the volume's own pip is one of the broken packages. free_quota.py has been
# corrected at source: a loose .pyc is never touched, and a __pycache__ entry is deleted
# only when the matching .py really is in the parent directory.
set -uo pipefail
cd /root || exit 9
IN=/root/in; OUT=/root/novafix_out; MT=/root/mt; LOG=/root/logs
DP=/workspace/_sys/pylibs311_good/dist-packages
mkdir -p "$OUT" "$MT/maya-ops/lt" "$MT/bench/replace_musetalk_alt" "$LOG"
say(){ local m="[job $(date -u +%H:%M:%S)] $*"; echo "$m"; echo "$m" >> "$OUT/STAGES"; }
: > "$OUT/STAGES"

need="novalive_job.sh repair_pylibs.py free_quota.py live_intro_harness.py \
ditto_bridge_patch.py nova_ditto.py ditto_server.py ditto_up.sh ditto_wide.py motion_bank.py \
ditto_fullbody.py sitecustomize.py nova_fb_bank.mp4 nova_fb_bank.json PAYLOAD_DONE"
say "stage 0: waiting for the payload"
for i in $(seq 1 240); do
  ok=1; for f in $need; do [ -s "$IN/$f" ] || ok=0; done
  [ $ok = 1 ] && break; sleep 5
done
for f in $need; do [ -s "$IN/$f" ] || { say "MISSING $f -- abort"; exit 11; }; done
say "stage 0 OK"

# ---------- background: the two slow installs, and Ditto, all at once ----------
say "bg: python3.10-dev + build-essential"
( apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3.10-dev build-essential && echo READY > "$OUT/DEV_READY" ) > "$OUT/aptdev.log" 2>&1 &
say "bg: playwright + chromium"
( pip install -q playwright >/dev/null 2>&1 \
    && python3 -m playwright install --with-deps chromium \
    && echo READY > "$OUT/PW_READY" ) > "$OUT/playwright.log" 2>&1 &

# =========================================================== STAGE R: REPAIR THE TREE =====
say "stage R1: diagnosing $DP (read only)"
python3 -I "$IN/repair_pylibs.py" --dist-packages "$DP" --diagnose \
   --report "$OUT/pylibs_diagnose.json" > "$OUT/pylibs_diagnose.txt" 2>&1
sed -n '1,45p' "$OUT/pylibs_diagnose.txt"

say "stage R2: repairing -- container pip, PYTHONPATH unset, straight into the volume tree"
python3 -I "$IN/repair_pylibs.py" --dist-packages "$DP" --repair \
   --targets "flask,livekit.api,livekit.rtc,aiohttp,requests,numpy" --rounds 16 \
   --report "$OUT/pylibs_repair.json" > "$OUT/pylibs_repair.txt" 2>&1; RRC=$?
say "stage R2: repair rc=$RRC"
cat "$OUT/pylibs_repair.txt"
# did it actually land? import the two the stack really needs, with the real PYTHONPATH.
for m in flask livekit.api livekit.rtc aiohttp; do
  r=$(PYTHONPATH="$DP" python3 -c "import $m; print('OK')" 2>&1 | tail -1)
  say "stage R3: import $m -> $r"
  echo "$m $r" >> "$OUT/IMPORTS"
done
du -sbx /workspace > "$OUT/du_after_repair.txt" 2>&1
say "stage R3: volume now $(cut -f1 "$OUT/du_after_repair.txt") bytes"

# =========================================================== STAGE B: pages still good? ===
say "stage B: confirming the restored pages are still non-zero"
{ for f in /workspace/pages/beta/freeze.html /workspace/pages/shared/light-engine.js \
           /workspace/pages/models/pose_landmarker_lite.task /workspace/pages/upperbody.html \
           /workspace/pages/beta/wave.html /workspace/pages/shared/pose-engine.js; do
    printf '%-52s %s bytes\n' "$f" "$(stat -c %s "$f" 2>/dev/null || echo MISSING)"
  done
  echo "0-byte files under /workspace/pages (excluding the previous session's *.novalive-new):"
  find /workspace/pages -type f -size 0 ! -name '*.novalive-new' 2>/dev/null | head -30
  echo "count: $(find /workspace/pages -type f -size 0 ! -name '*.novalive-new' 2>/dev/null | wc -l)"
} > "$OUT/pages_check.txt" 2>&1
cat "$OUT/pages_check.txt"
# the previous session's abandoned temp files: 0 bytes, referenced by nothing. Clear the litter.
find /workspace/pages -type f -size 0 -name '*.novalive-new' -delete 2>/dev/null
say "stage B: cleared $(find /workspace/pages -name '*.novalive-new' 2>/dev/null | wc -l) remaining *.novalive-new"

# =========================================================== STAGE C: the face engine =====
say "stage C1: Ditto on the full-body motion bank"
for i in $(seq 1 60); do [ -s "$OUT/DEV_READY" ] && break; sleep 5; done
[ -e /usr/include/python3.10/Python.h ] && say "  Python.h present" || say "  WARN Python.h MISSING"
cp "$IN/ditto_server.py" "$IN/ditto_up.sh" "$IN/motion_bank.py" "$MT/maya-ops/lt/"
cp "$IN/ditto_wide.py" "$MT/bench/replace_musetalk_alt/"
chmod +x "$MT/maya-ops/lt/ditto_up.sh"
export PYTHONPATH="$IN:${PYTHONPATH:-}"
export DITTO_FB_ON=1 DITTO_FB_SHIM="$IN" DITTO_FB_BENCH="$MT/bench/replace_musetalk_alt"
export DITTO_FB_UP="${FB_UP:-3.0}" DITTO_FB_BOX="${FB_BOX:-263,215,763,715}"
export DITTO_ROOT=/root/ditto MAYA_LOGS="$LOG" DITTO_PORT=8031
export DITTO_AMP=0.6 DITTO_CHUNK=25 DITTO_PRIME=35 DITTO_VAD=1 DITTO_THREADS=6 DITTO_EYE_HOLD=1
export DITTO_WAIT_SEC=1500
export DITTO_OUT_W=1074 DITTO_OUT_H=1920        # DITTO-FULLBODY section 4
export DITTO_SRC="$IN/nova_fb_bank.mp4" DITTO_BANK="$IN/nova_fb_bank.json"
bash "$MT/maya-ops/lt/ditto_up.sh" > "$OUT/ditto_up.log" 2>&1; DIRC=$?
curl -s -m 10 127.0.0.1:8031/health > "$OUT/health_ditto.json" 2>&1
cp "$LOG/ditto_server.log" "$OUT/ditto_server.log" 2>/dev/null
say "stage C1: ditto_up rc=$DIRC health=$(head -c 260 "$OUT/health_ditto.json")"
DITTO_OK=0; grep -q '"ready": *true' "$OUT/health_ditto.json" 2>/dev/null && DITTO_OK=1
[ "$DITTO_OK" = 1 ] || { say "stage C1: Ditto NOT ready -- MuseTalk for the recording"; tail -25 "$OUT/ditto_up.log"; }

FACE=musetalk
if [ "$DITTO_OK" = 1 ]; then
  say "stage C2: probing the REAL /workspace/lk_bridge.py"
  python3 -I "$IN/ditto_bridge_patch.py" --probe --wd "$OUT" > "$OUT/probe.txt" 2>&1; PRC=$?
  say "stage C2: probe rc=$PRC"; sed -n '1,12p' "$OUT/probe.txt"
  if [ "$PRC" = 0 ]; then
    python3 -I "$IN/ditto_bridge_patch.py" --apply --sidecar "$IN/nova_ditto.py" --wd "$OUT" \
      > "$OUT/apply.txt" 2>&1; ARC=$?
    say "stage C2: apply rc=$ARC"; tail -8 "$OUT/apply.txt"
    if [ "$ARC" = 0 ]; then FACE=ditto; else
      say "stage C2: apply refused -- REVERTING to the untouched original, staying on MuseTalk"
      python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert_early.txt" 2>&1
    fi
  else
    say "stage C2: probe mismatch -- NOT applying. MuseTalk."
  fi
fi
echo "$FACE" > "$OUT/FACE"
say "stage C DONE: face engine = $FACE"

# =========================================================== STAGE D: stack + recording ===
say "stage D1: boot.sh"
export NOVA_DEPLOY_BRANCH=nova-ditto
export NOVA_DITTO_DELAY_SITE=bridge
[ "$FACE" = ditto ] && export NOVA_FACE=ditto || unset NOVA_FACE
setsid nohup bash /workspace/boot.sh > "$OUT/bootwrap.log" 2>&1 < /dev/null &
BRAIN=0
for i in $(seq 1 156); do          # 13 min, not 25: a dead import shows up in 2
  c=$(curl -s -m 4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/ 2>/dev/null)
  if [ "$c" = "200" ]; then BRAIN=1; say "stage D1: BRAIN_UP after $((i*5))s"; break; fi
  if [ $((i % 12)) = 0 ]; then
    say "stage D1: ${i}0s... boot=$(wc -c < /root/boot.log 2>/dev/null) bridge=$(wc -c < /root/bridge.log 2>/dev/null)"
    grep -hoE "No module named '[^']+'" /root/boot.log /root/bridge.log /root/rtlk.log 2>/dev/null | sort -u | head -6 | while read -r l; do say "    STILL MISSING: $l"; done
  fi
  sleep 5
done
RED='s#(https?://)[^/@[:space:]]+@#\1<REDACTED-TOKEN>@#g; s#x-access-token:[A-Za-z0-9_-]+#x-access-token:<REDACTED>#g; s#gh[psuor]_[A-Za-z0-9]{16,}#<REDACTED>#g'
for f in /root/boot.log /root/bridge.log /root/rtlk.log /root/app.log; do
  [ -s "$f" ] && sed -E "$RED" "$f" > "$OUT/$(basename "$f")"
done
[ "$BRAIN" = 1 ] && echo UP > "$OUT/STACK" || { say "stage D1 FAILED: :8765 never answered 200"; echo FAILED > "$OUT/STACK"; }
grep -h "NOVA_FACE" "$OUT/bridge.log" "$OUT/rtlk.log" 2>/dev/null | head -4 | while read -r l; do say "    $l"; done

say "stage D2: what the brain serves (the live-page evidence)"
{ for p in "/beta/freeze?intro=freeze" "/freeze?intro=freeze" "/" "/health"; do
    code=$(curl -s -m 10 -o /tmp/_pg -w '%{http_code}' "http://127.0.0.1:8765$p")
    sz=$(stat -c %s /tmp/_pg 2>/dev/null || echo 0)
    jt=$(grep -c "JUDGE-TRUTH" /tmp/_pg 2>/dev/null || true)
    printf '%-28s http=%s  %s bytes  JUDGE-TRUTH=%s  first100=%s\n' "$p" "$code" "$sz" "${jt:-0}" "$(head -c 100 /tmp/_pg | tr '\n' ' ')"
  done; } > "$OUT/page_probe.txt" 2>&1
cat "$OUT/page_probe.txt"
curl -s -m 15 "http://127.0.0.1:8765/beta/freeze?intro=freeze" -o "$OUT/freeze.served.html"
say "stage D2: /beta/freeze = $(stat -c %s "$OUT/freeze.served.html" 2>/dev/null) bytes, JUDGE-TRUTH x$(grep -c JUDGE-TRUTH "$OUT/freeze.served.html" 2>/dev/null || echo 0)"

say "stage D3: waiting up to 20 min for /root/in/GO"
for i in $(seq 1 240); do [ -e "$IN/GO" ] && break; sleep 5; done
if [ ! -e "$IN/GO" ]; then say "stage D3: no GO -- skipping"; else
  [ -s "$OUT/PW_READY" ] || { say "stage D3: waiting on playwright"; for i in $(seq 1 90); do [ -s "$OUT/PW_READY" ] && break; sleep 5; done; }
  say "stage D3: RECORDING (engine=$FACE)"
  python3 "$IN/live_intro_harness.py" --out "$OUT" --inbox "$IN" \
      --rec-dir /root/rec --max-s "${REC_MAX_S:-200}" \
      --url "http://127.0.0.1:8765/beta/freeze?intro=freeze|http://127.0.0.1:8765/freeze?intro=freeze" \
      > "$OUT/harness.log" 2>&1
  say "stage D3: harness rc=$? -- $(tail -1 "$OUT/harness.log")"
fi
for f in /root/bridge.log /root/rtlk.log /root/app.log; do
  [ -s "$f" ] && sed -E "$RED" "$f" > "$OUT/$(basename "$f")"
done
cp "$LOG/ditto_server.log" "$OUT/ditto_server_end.log" 2>/dev/null
curl -s -m 10 127.0.0.1:8031/health > "$OUT/health_ditto_end.json" 2>&1
ls -la "$OUT" > "$OUT/LISTING" 2>&1
say "ALL DONE -- waiting up to 20 min for /root/in/PULLED, then reverting"

# =========================================================== STAGE E: leave as found ======
for i in $(seq 1 240); do [ -s "$IN/PULLED" ] && break; sleep 5; done
if [ "$FACE" = ditto ]; then
  python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert.txt" 2>&1
  say "stage E: revert lk_bridge.py rc=$? -- $(tail -2 "$OUT/revert.txt" | head -1)"
fi
rm -f /workspace/lk_bridge.py.bak-ditto-* /workspace/nova_ditto.py
md5sum /workspace/lk_bridge.py /workspace/rt_lk.py > "$OUT/volume_md5_end.txt" 2>&1
say "stage E DONE: $(tr '\n' ' ' < "$OUT/volume_md5_end.txt")"
echo 0 > "$OUT/RC"
