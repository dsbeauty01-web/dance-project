#!/usr/bin/env bash
# novalive_job2.sh -- attempt 2, 2026-11-01. RECORD ONLY.
#
# What attempt 1 proved, on the pod, measured:
#   * Nova's production volume 1ditrne6cb is OUT OF QUOTA. Every write to /workspace fails with
#     OSError Errno 122 / "Disk quota exceeded". That is why podsrv would not start from the
#     volume, why ditto_bridge_patch.py --apply died, and why boot.sh's own deploy step TRUNCATED
#     the pages it was copying ("cp: failed to close /workspace/pages/...") and left
#     /beta/freeze answering 200 with an empty body.
#   * Ditto itself is fine: it booted on the full-body motion bank in 191 s, ready, bank loaded.
#     It cannot reach the LIVE path because that needs lk_bridge.py patched ON THE VOLUME.
#
# So this job writes NOTHING to the volume -- no patch, no rt_lk overlay (attempt 1's overlay
# truncated /workspace/rt_lk.py before boot.sh's deploy repaired it; never again), no Ditto.
# It inventories the pages read-only, boots the stack, and records whichever page actually serves.
set -uo pipefail
IN=/root/in; OUT=/root/novalive_out; LOG=/root/logs
mkdir -p "$OUT" "$LOG"
say(){ local m="[job $(date -u +%H:%M:%S)] $*"; echo "$m"; echo "$m" >> "$OUT/STAGES"; }
: > "$OUT/STAGES"

need="novalive_job.sh live_intro_harness.py PAYLOAD_DONE"
say "stage 0: waiting for the payload"
for i in $(seq 1 120); do
  ok=1; for f in $need; do [ -s "$IN/$f" ] || ok=0; done
  [ $ok = 1 ] && break; sleep 5
done
for f in $need; do [ -s "$IN/$f" ] || { say "MISSING $f -- abort"; exit 11; }; done
say "stage 0 OK"

# ---------- stage 1: playwright, in the background ----------
( pip install -q playwright >/dev/null 2>&1 && python3 -m playwright install --with-deps chromium \
    && echo READY > "$OUT/PW_READY" ) > "$OUT/playwright.log" 2>&1 &
say "stage 1: playwright + chromium (background)"

# ---------- stage 2: read-only inventory of what the volume can actually serve ----------
say "stage 2: page inventory (READ ONLY -- nothing is written to /workspace)"
{ echo "== df /workspace"; df -h /workspace
  echo; echo "== quota probe (write 1 byte to a temp name, then remove it)"
  if echo x > /workspace/.novalive_quota_probe 2>/dev/null; then echo "WRITABLE"; rm -f /workspace/.novalive_quota_probe; else echo "NOT WRITABLE (quota)"; fi
  echo; echo "== /workspace/pages"; ls -la /workspace/pages 2>&1 | head -40
  echo; echo "== /workspace/pages/beta"; ls -la /workspace/pages/beta 2>&1 | head -40
  echo; echo "== sizes of the pages rt_lk serves"
  for f in /workspace/pages/beta/freeze.html /workspace/pages/freeze.html /workspace/pages/index.html \
           /workspace/pages/beta/wave.html /workspace/pages/upperbody.html; do
    printf '%-44s %s bytes  md5 %s\n' "$f" "$(stat -c %s "$f" 2>/dev/null || echo MISSING)" \
      "$(md5sum "$f" 2>/dev/null | cut -c1-8 || echo -)"
  done
  echo; echo "== shared/ and models/"; ls -la /workspace/pages/shared /workspace/pages/models 2>&1 | head -30
} > "$OUT/pages_inventory.txt" 2>&1
sed -n '1,30p' "$OUT/pages_inventory.txt"
say "stage 2 DONE -- $OUT/pages_inventory.txt"

# ---------- stage 3: the stack, one boot, defaults (MuseTalk) ----------
# NOVA_DEPLOY_BRANCH is still nova-ditto per the mission, but the deploy will fail on quota the
# same way; it is logged, not relied on.
say "stage 3: boot.sh"
export NOVA_DEPLOY_BRANCH=nova-ditto
unset NOVA_FACE
setsid nohup bash /workspace/boot.sh > "$OUT/bootwrap.log" 2>&1 < /dev/null &
BRAIN=0
for i in $(seq 1 240); do
  c=$(curl -s -m 4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/ 2>/dev/null)
  if [ "$c" = "200" ]; then BRAIN=1; say "stage 3: BRAIN_UP after $((i*5))s"; break; fi
  [ $((i % 12)) = 0 ] && say "stage 3: waiting ${i}0s..."
  sleep 5
done
cp /root/boot.log /root/bridge.log /root/rtlk.log /root/app.log "$OUT/" 2>/dev/null
[ "$BRAIN" = 1 ] || say "stage 3 FAILED: :8765 never answered 200"

# what does each candidate page actually return, before the browser ever opens one?
say "stage 3b: what the brain serves right now"
{ for p in "/beta/freeze?intro=freeze" "/freeze?intro=freeze" "/" "/health"; do
    code=$(curl -s -m 8 -o /tmp/_pg -w '%{http_code}' "http://127.0.0.1:8765$p")
    printf '%-28s http=%s  %s bytes  first120=%s\n' "$p" "$code" "$(stat -c %s /tmp/_pg)" "$(head -c 120 /tmp/_pg | tr '\n' ' ')"
  done; } > "$OUT/page_probe.txt" 2>&1
cat "$OUT/page_probe.txt"
cp "$OUT/page_probe.txt" "$OUT/page_probe_copy.txt" 2>/dev/null

# ---------- stage 4: the recording, on GO ----------
say "stage 4: waiting for GO"
for i in $(seq 1 180); do [ -e "$IN/GO" ] && break; sleep 5; done
if [ ! -e "$IN/GO" ]; then say "stage 4: no GO -- skipping"; else
  [ -s "$OUT/PW_READY" ] || { say "stage 4: waiting on playwright"; for i in $(seq 1 60); do [ -s "$OUT/PW_READY" ] && break; sleep 5; done; }
  say "stage 4: RECORDING"
  python3 "$IN/live_intro_harness.py" --out "$OUT" --inbox "$IN" --max-s "${REC_MAX_S:-600}" \
     --url "http://127.0.0.1:8765/beta/freeze?intro=freeze|http://127.0.0.1:8765/freeze?intro=freeze" \
     > "$OUT/harness.log" 2>&1
  say "stage 4: harness rc=$? $(tail -1 "$OUT/harness.log")"
fi
cp /root/bridge.log /root/rtlk.log /root/app.log "$OUT/" 2>/dev/null
ls -la "$OUT" > "$OUT/LISTING" 2>&1
say "ALL DONE -- nothing was written to the production volume by this job"
for i in $(seq 1 240); do [ -s "$IN/PULLED" ] && break; sleep 5; done
say "pulled"
