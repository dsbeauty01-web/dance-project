#!/usr/bin/env bash
# novafix_job3.sh -- session novafix-intro, attempt 3, 2026-11-02. THE RECORDING RUN.
#
# Attempts 1 and 2 bought these facts. Nothing here is guessed.
#   * quota: 2.1 GB freed from the allow-list. A 1 MB write failed before, 512 MB works now.
#   * pages: RESTORED. 0-byte files under /workspace/pages (excluding the previous session's
#     *.novalive-new litter, since cleared) = 0. beta/freeze.html = 147542 bytes.
#   * Ditto: ready in 175 s and 182 s on nova_fb_bank, out_wh 1074x1920.
#   * bridge: attempt 1 applied the patch cleanly, 1c4448b4... -> e9be0f4f...
#   * pylibs: deleting *.pyc broke 6 sourceless packages (flask werkzeug click
#     itsdangerous idna certifi); reinstalling them fixed those, but edge_tts and the
#     volume's vendored pip were still missing, so :8765 never came up.
#
# THE THREE BUGS IN ATTEMPT 2, ALL FIXED HERE:
#   1. apt-get and `playwright install --with-deps` ran in PARALLEL and fought over the
#      dpkg lock, so Chromium never installed ("Could not get lock /var/lib/dpkg/
#      lock-frontend", "Failed to install browsers"). They are SERIAL now.
#   2. apply() re-probes and REFUSES on an already-patched file even though it carries the
#      idempotency marker, so an applied bridge fell back to MuseTalk. So: --revert to the
#      pristine original first, then --probe (must be 4/4), then --apply. Fully verified.
#   3. the repair target list did not reach everything the stack imports. It is wider now,
#      AND boot is SELF-HEALING: if :8765 does not come up, every "No module named 'X'" in
#      the logs is installed and boot is retried, up to 3 rounds.
set -uo pipefail
cd /root || exit 9
IN=/root/in; OUT=/root/novafix_out; MT=/root/mt; LOG=/root/logs
DP=/workspace/_sys/pylibs311_good/dist-packages
mkdir -p "$OUT" "$MT/maya-ops/lt" "$MT/bench/replace_musetalk_alt" "$LOG"
say(){ local m="[job $(date -u +%H:%M:%S)] $*"; echo "$m"; echo "$m" >> "$OUT/STAGES"; }
: > "$OUT/STAGES"
RED='s#(https?://)[^/@[:space:]]+@#\1<REDACTED-TOKEN>@#g; s#x-access-token:[A-Za-z0-9_-]+#x-access-token:<REDACTED>#g; s#gh[psuor]_[A-Za-z0-9]{16,}#<REDACTED>#g'

need="novalive_job.sh repair_pylibs.py real_harness.py ditto_bridge_patch.py nova_ditto.py \
ditto_server.py ditto_up.sh ditto_wide.py motion_bank.py ditto_fullbody.py sitecustomize.py \
nova_fb_bank.mp4 nova_fb_bank.json PAYLOAD_DONE"
say "stage 0: waiting for the payload"
for i in $(seq 1 240); do
  ok=1; for f in $need; do [ -s "$IN/$f" ] || ok=0; done
  [ $ok = 1 ] && break; sleep 5
done
for f in $need; do [ -s "$IN/$f" ] || { say "MISSING $f -- abort"; exit 11; }; done
say "stage 0 OK"

# ---------- stage 1: the C headers Ditto needs. FOREGROUND: it owns the dpkg lock. ----------
say "stage 1: apt python3.10-dev + build-essential (foreground -- owns the dpkg lock)"
( apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3.10-dev build-essential ) > "$OUT/aptdev.log" 2>&1
[ -e /usr/include/python3.10/Python.h ] && say "stage 1 OK: Python.h present" || say "stage 1 WARN: Python.h MISSING"

# ---------- stage 2: Ditto, in the BACKGROUND now that apt has finished ----------
cp "$IN/ditto_server.py" "$IN/ditto_up.sh" "$IN/motion_bank.py" "$MT/maya-ops/lt/"
cp "$IN/ditto_wide.py" "$MT/bench/replace_musetalk_alt/"
chmod +x "$MT/maya-ops/lt/ditto_up.sh"
say "stage 2: ditto_up.sh in the background (ready in ~180 s on this volume)"
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

# ---------- stage 3: Chromium. SERIAL after apt -- this is bug 1. ----------
say "stage 3: playwright + chromium (serial, after apt released the lock)"
( pip install -q playwright && python3 -m playwright install --with-deps chromium ) \
   > "$OUT/playwright.log" 2>&1 && echo READY > "$OUT/PW_READY"
if [ -s "$OUT/PW_READY" ]; then say "stage 3 OK: chromium installed"; else
  say "stage 3: first try failed, retrying chromium without --with-deps"
  ( python3 -m playwright install chromium ) >> "$OUT/playwright.log" 2>&1 && echo READY > "$OUT/PW_READY"
  [ -s "$OUT/PW_READY" ] && say "stage 3 OK on retry" || { say "stage 3 FAILED"; tail -6 "$OUT/playwright.log"; }
fi
python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=['--no-sandbox']); print('CHROMIUM OK', b.version); b.close()
" > "$OUT/chromium_check.txt" 2>&1
say "stage 3: $(tail -1 "$OUT/chromium_check.txt")"

# ---------- stage 4: finish the pylibs repair (wider target list) ----------
say "stage 4: repairing $DP -- container pip, PYTHONPATH unset"
python3 -I "$IN/repair_pylibs.py" --dist-packages "$DP" --repair --rounds 24 \
  --targets "flask,livekit.api,livekit.rtc,aiohttp,requests,numpy,edge_tts,pip,websockets,soundfile,av,scipy,cv2,torch" \
  --report "$OUT/pylibs_repair.json" > "$OUT/pylibs_repair.txt" 2>&1
say "stage 4: repair rc=$?"
grep -E "^  (import|installed|  )" "$OUT/pylibs_repair.txt" | tail -20

# ---------- stage 5: the bridge -- revert to pristine, probe 4/4, then apply ----------
say "stage 5: --revert to the pristine original (attempt 1 left it patched)"
python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert_pre.txt" 2>&1
say "stage 5: revert rc=$? -- $(grep -E 'REVERTED|no .bak' "$OUT/revert_pre.txt" | head -1)"
say "stage 5: waiting for Ditto to be ready before touching the bridge"
DITTO_OK=0
for i in $(seq 1 90); do
  curl -s -m 8 127.0.0.1:8031/health > "$OUT/health_ditto.json" 2>/dev/null
  grep -q '"ready": *true' "$OUT/health_ditto.json" 2>/dev/null && { DITTO_OK=1; say "stage 5: Ditto ready after $((i*5))s"; break; }
  sleep 5
done
cp "$LOG/ditto_server.log" "$OUT/ditto_server.log" 2>/dev/null
[ "$DITTO_OK" = 1 ] || { say "stage 5: Ditto NOT ready -- MuseTalk"; tail -20 "$OUT/ditto_up.log"; }

FACE=musetalk
if [ "$DITTO_OK" = 1 ]; then
  python3 -I "$IN/ditto_bridge_patch.py" --probe --wd "$OUT" > "$OUT/probe.txt" 2>&1; PRC=$?
  say "stage 5: probe rc=$PRC"; grep -E "md5|A[1-4]|already patched" "$OUT/probe.txt" | head -8
  if [ "$PRC" = 0 ]; then
    python3 -I "$IN/ditto_bridge_patch.py" --apply --sidecar "$IN/nova_ditto.py" --wd "$OUT" \
      > "$OUT/apply.txt" 2>&1; ARC=$?
    say "stage 5: apply rc=$ARC -- $(grep -E 'APPLIED|already patched|REFUSING' "$OUT/apply.txt" | head -1)"
    if [ "$ARC" = 0 ]; then FACE=ditto; else
      say "stage 5: apply refused -- REVERTING and staying on MuseTalk"
      python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert_early.txt" 2>&1
    fi
  else
    say "stage 5: probe is not 4/4 -- NOT applying, REVERTING, MuseTalk"
    python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert_early.txt" 2>&1
  fi
fi
echo "$FACE" > "$OUT/FACE"
say "stage 5 DONE: face engine = $FACE"

# ---------- stage 6: boot the stack, and HEAL whatever import it still trips on ----------
boot_once(){
  for pat in "[r]t_lk.py" "[l]k_bridge.py" "[b]oot.sh"; do pkill -f "$pat" 2>/dev/null; done
  sleep 3
  export NOVA_DEPLOY_BRANCH=nova-ditto NOVA_DITTO_DELAY_SITE=bridge
  [ "$FACE" = ditto ] && export NOVA_FACE=ditto || unset NOVA_FACE
  unset PYTHONPATH
  setsid nohup bash /workspace/boot.sh > "$OUT/bootwrap.$1.log" 2>&1 < /dev/null &
  for i in $(seq 1 72); do        # 6 min per round
    [ "$(curl -s -m 4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/ 2>/dev/null)" = "200" ] && return 0
    sleep 5
  done
  return 1
}
BRAIN=0
for round in 1 2 3; do
  say "stage 6: boot.sh round $round (NOVA_FACE=$FACE)"
  if boot_once "$round"; then BRAIN=1; say "stage 6: BRAIN_UP on round $round"; break; fi
  miss=$(grep -hoE "No module named '[^']+'" /root/boot.log /root/bridge.log /root/rtlk.log /root/app.log 2>/dev/null \
         | sed "s/No module named '//;s/'//" | cut -d. -f1 | sort -u | tr '\n' ' ')
  say "stage 6: round $round did not come up. missing: ${miss:-(nothing named)}"
  [ -z "$miss" ] && { say "stage 6: nothing left to install -- giving up on more rounds"; break; }
  for m in $miss; do
    say "stage 6: healing -> pip install $m into the tree"
    env -u PYTHONPATH python3 -m pip install --no-input -q --target "$DP" --upgrade --no-deps "$m" \
      >> "$OUT/heal.log" 2>&1 || say "stage 6:   pip $m failed (see heal.log)"
  done
done
for f in /root/boot.log /root/bridge.log /root/rtlk.log /root/app.log; do
  [ -s "$f" ] && sed -E "$RED" "$f" > "$OUT/$(basename "$f")"
done
[ "$BRAIN" = 1 ] && echo UP > "$OUT/STACK" || { say "stage 6 FAILED: :8765 never answered 200"; echo FAILED > "$OUT/STACK"; }
grep -h "NOVA_FACE" "$OUT/bridge.log" "$OUT/rtlk.log" 2>/dev/null | head -4 | while read -r l; do say "    $l"; done

# ---------- stage 7: the live-page evidence, then the recording ----------
say "stage 7: what the brain serves"
{ for p in "/beta/freeze?intro=freeze" "/freeze?intro=freeze" "/" "/health"; do
    code=$(curl -s -m 12 -o /tmp/_pg -w '%{http_code}' "http://127.0.0.1:8765$p")
    sz=$(stat -c %s /tmp/_pg 2>/dev/null || echo 0)
    jt=$(grep -c "JUDGE-TRUTH" /tmp/_pg 2>/dev/null || true)
    printf '%-28s http=%s  %s bytes  JUDGE-TRUTH=%s  first100=%s\n' "$p" "$code" "$sz" "${jt:-0}" "$(head -c 100 /tmp/_pg | tr '\n' ' ')"
  done; } > "$OUT/page_probe.txt" 2>&1
cat "$OUT/page_probe.txt"
curl -s -m 15 "http://127.0.0.1:8765/beta/freeze?intro=freeze" -o "$OUT/freeze.served.html"
say "stage 7: /beta/freeze served $(stat -c %s "$OUT/freeze.served.html" 2>/dev/null) bytes, JUDGE-TRUTH x$(grep -c JUDGE-TRUTH "$OUT/freeze.served.html" 2>/dev/null || echo 0)"

if [ "$BRAIN" != 1 ]; then
  say "stage 7: no stack -> NO RECORDING. Not pretending otherwise."
else
  say "stage 7: waiting up to 12 min for /root/in/GO"
  for i in $(seq 1 144); do [ -e "$IN/GO" ] && break; sleep 5; done
  if [ ! -e "$IN/GO" ]; then say "stage 7: no GO -- skipping"; else
    say "stage 7: RECORDING (engine=$FACE)"
    python3 "$IN/real_harness.py" --out "$OUT" --inbox "$IN" --rec-dir /root/rec \
       --max-s "${REC_MAX_S:-210}" \
       --url "http://127.0.0.1:8765/beta/freeze?intro=freeze|http://127.0.0.1:8765/freeze?intro=freeze" \
       > "$OUT/harness.log" 2>&1
    say "stage 7: harness rc=$? -- $(tail -1 "$OUT/harness.log")"
  fi
fi
for f in /root/bridge.log /root/rtlk.log /root/app.log; do
  [ -s "$f" ] && sed -E "$RED" "$f" > "$OUT/$(basename "$f")"
done
cp "$LOG/ditto_server.log" "$OUT/ditto_server_end.log" 2>/dev/null
curl -s -m 10 127.0.0.1:8031/health > "$OUT/health_ditto_end.json" 2>&1
ls -la "$OUT" > "$OUT/LISTING" 2>&1
say "ALL DONE -- waiting up to 20 min for /root/in/PULLED, then reverting"

# ---------- stage 8: leave the production volume as found ----------
for i in $(seq 1 240); do [ -s "$IN/PULLED" ] && break; sleep 5; done
if [ "$FACE" = ditto ]; then
  python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert.txt" 2>&1
  say "stage 8: revert lk_bridge.py rc=$? -- $(grep -E 'REVERTED|no .bak' "$OUT/revert.txt" | head -1)"
fi
rm -f /workspace/lk_bridge.py.bak-ditto-* /workspace/nova_ditto.py
md5sum /workspace/lk_bridge.py /workspace/rt_lk.py > "$OUT/volume_md5_end.txt" 2>&1
say "stage 8 DONE: $(tr '\n' ' ' < "$OUT/volume_md5_end.txt")"
echo 0 > "$OUT/RC"
