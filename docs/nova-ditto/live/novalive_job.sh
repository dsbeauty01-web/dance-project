#!/usr/bin/env bash
# novalive_job.sh -- the FIXED pipeline for session novalive-intro (2026-11-01).
#
# Goal: record the REAL commercial game intro (beta/freeze?intro=freeze) as a genuine
# conversation, with Ditto drawing her lips on a full-body body driven by a motion bank.
#
# The pod has Nova's PRODUCTION volume 1ditrne6cb mounted at /workspace, so:
#   * nothing pre-existing is deleted or moved; the one production file this touches is
#     /workspace/lk_bridge.py, which is backed up by ditto_bridge_patch.py and reverted at the end;
#   * everything this job creates lives in /workspace/novalive_out + our own /workspace/in uploads;
#   * Ditto installs to the CONTAINER disk (/root/ditto), never the volume.
#
# ORDER MATTERS. lk_bridge.py with NOVA_FACE=ditto raises if the Ditto server is not already
# ready (no silent fallbacks), so Ditto comes up FIRST and boot.sh is started only after it is
# serving. That means ONE boot of the stack, no restarts, and boot.sh keeps owning the four live
# credentials it exports -- this job never reads or prints them.
set -uo pipefail
IN=/workspace/in; OUT=/workspace/novalive_out; MT=/root/mt; LOG=/root/logs
mkdir -p "$OUT" "$MT/maya-ops/lt" "$MT/bench/replace_musetalk_alt" "$LOG"
say(){ local m="[job $(date -u +%H:%M:%S)] $*"; echo "$m"; echo "$m" >> "$OUT/STAGES"; }
: > "$OUT/STAGES"

need="novalive_job.sh ditto_server.py ditto_up.sh ditto_wide.py motion_bank.py ditto_fullbody.py \
sitecustomize.py nova_ditto.py ditto_bridge_patch.py live_intro_harness.py rt_lk.py \
nova_fb_bank.mp4 nova_fb_bank.json PAYLOAD_DONE"
say "stage 0: waiting for the payload"
for i in $(seq 1 240); do
  ok=1; for f in $need; do [ -s "$IN/$f" ] || ok=0; done
  [ $ok = 1 ] && break; sleep 5
done
for f in $need; do [ -s "$IN/$f" ] || { say "MISSING $f -- abort"; exit 11; }; done
say "stage 0 OK: payload complete"
md5sum "$IN"/*.py "$IN"/*.json 2>/dev/null > "$OUT/payload_md5.txt"

# ---------- stage 1: the C headers Ditto's pyximport needs (cost pod 1 on 2026-10-31) ----------
say "stage 1: python3.10-dev + build-essential"
(apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3.10-dev build-essential) \
  > "$OUT/aptdev.log" 2>&1
[ -e /usr/include/python3.10/Python.h ] && say "stage 1 OK: Python.h present" || say "stage 1 WARN: Python.h MISSING"

# ---------- stage 2: Chromium for the harness, in the background ----------
say "stage 2: playwright + chromium (background)"
( pip install -q playwright >/dev/null 2>&1 && python3 -m playwright install --with-deps chromium \
    && echo READY > "$OUT/PW_READY" ) > "$OUT/playwright.log" 2>&1 &
PW_PID=$!

# ---------- stage 3: the Ditto server, on the motion bank ----------
cp "$IN/ditto_server.py" "$IN/ditto_up.sh" "$IN/motion_bank.py" "$MT/maya-ops/lt/"
cp "$IN/ditto_wide.py" "$MT/bench/replace_musetalk_alt/"
chmod +x "$MT/maya-ops/lt/ditto_up.sh"
export PYTHONPATH="$IN:${PYTHONPATH:-}"
export DITTO_FB_ON=1 DITTO_FB_SHIM="$IN" DITTO_FB_BENCH="$MT/bench/replace_musetalk_alt"
export DITTO_FB_UP="${FB_UP:-3.0}" DITTO_FB_BOX="${FB_BOX:-263,215,763,715}"
export DITTO_ROOT=/root/ditto MAYA_LOGS="$LOG" DITTO_PORT=8031
# the brief's known-good profile, unchanged
export DITTO_AMP=0.6 DITTO_CHUNK=25 DITTO_PRIME=35 DITTO_VAD=1 DITTO_THREADS=6 DITTO_EYE_HOLD=1
export DITTO_WAIT_SEC=1500
# DITTO-FULLBODY section 4: out_wh is reported from the SOURCE FILE, but Ditto resizes to
# max_size 1920 on the long side, so a 1924-high body is delivered at 1074x1920 and anything
# trusting /health reads every frame 2 px too wide (a progressive shear). Stating the truth here
# is one of the two documented fixes and needs no code change.
export DITTO_OUT_W=1074 DITTO_OUT_H=1920
export DITTO_SRC="$IN/nova_fb_bank.mp4" DITTO_BANK="$IN/nova_fb_bank.json"
say "stage 3: ditto_up.sh  src=nova_fb_bank.mp4 bank=nova_fb_bank.json box=$DITTO_FB_BOX"
bash "$MT/maya-ops/lt/ditto_up.sh" > "$OUT/ditto_up.log" 2>&1; DRC=$?
curl -s -m 10 127.0.0.1:8031/health > "$OUT/health_ditto.json" 2>&1
cp "$LOG/ditto_server.log" "$OUT/ditto_server.log" 2>/dev/null
say "stage 3: ditto_up rc=$DRC health=$(head -c 400 "$OUT/health_ditto.json")"
DITTO_OK=0
grep -q '"ready": *true' "$OUT/health_ditto.json" 2>/dev/null && DITTO_OK=1
if [ "$DITTO_OK" != 1 ]; then
  say "stage 3 FAILED -- Ditto is not ready. Falling back to MuseTalk for the recording."
  tail -30 "$OUT/ditto_up.log"; tail -30 "$OUT/ditto_server.log" 2>/dev/null
fi

# ---------- stage 4: the bridge patch (only if Ditto is actually serving) ----------
FACE=musetalk
if [ "$DITTO_OK" = 1 ]; then
  say "stage 4: probing the REAL /workspace/lk_bridge.py"
  python3 "$IN/ditto_bridge_patch.py" --probe --wd "$OUT" > "$OUT/probe.txt" 2>&1; PRC=$?
  say "stage 4: probe rc=$PRC"
  sed -n '1,14p' "$OUT/probe.txt"
  if [ "$PRC" = 0 ]; then
    python3 "$IN/ditto_bridge_patch.py" --apply --sidecar "$IN/nova_ditto.py" --wd "$OUT" \
      > "$OUT/apply.txt" 2>&1; ARC=$?
    say "stage 4: apply rc=$ARC"
    tail -12 "$OUT/apply.txt"
    if [ "$ARC" = 0 ]; then FACE=ditto; else say "stage 4: apply refused -- staying on MuseTalk"; fi
  else
    say "stage 4: the probe does not match this file -- NOT applying. MuseTalk."
  fi
fi
echo "$FACE" > "$OUT/FACE"
say "stage 4 DONE: face engine = $FACE"

# ---------- stage 5: the brain, from this branch ----------
# boot.sh runs deploy_from_git.sh, which resets /workspace/_repo to origin/$NOVA_DEPLOY_BRANCH and
# copies pod/rt_lk.py onto the volume. If the pod's git credentials fail that step deploys the
# CACHED checkout silently (deploy_from_git.sh says so in its own log), which would ship a brain
# whose NOVA_FACE=ditto branch still delays /humanaudio -- on top of the bridge's delay. So the
# intended file is staged here first and verified after boot.sh, and the md5s go in the report.
cp -p /workspace/rt_lk.py "$OUT/rt_lk.volume.before.py" 2>/dev/null
md5sum "$IN/rt_lk.py" /workspace/rt_lk.py > "$OUT/rtlk_md5_before.txt" 2>&1
cp "$IN/rt_lk.py" /workspace/rt_lk.py
say "stage 5: staged this branch's rt_lk.py onto the volume (original kept at $OUT/rt_lk.volume.before.py)"

# ---------- stage 6: the whole Nova stack, ONE boot ----------
say "stage 6: boot.sh (LAW-PODS-9-COLDLOAD: silence under 15 min is loading, not dead)"
export NOVA_DEPLOY_BRANCH=nova-ditto
[ "$FACE" = ditto ] && export NOVA_FACE=ditto || unset NOVA_FACE
export NOVA_DITTO_DELAY_SITE=bridge
setsid nohup bash /workspace/boot.sh > "$OUT/bootwrap.log" 2>&1 < /dev/null &
BRAIN=0
for i in $(seq 1 300); do            # 25 min
  c=$(curl -s -m 4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/ 2>/dev/null)
  if [ "$c" = "200" ]; then BRAIN=1; say "stage 6: BRAIN_UP after $((i*5))s"; break; fi
  if [ $((i % 12)) = 0 ]; then
    say "stage 6: waiting ${i}0s... boot.log=$(wc -c < /root/boot.log 2>/dev/null) app=$(wc -c < /root/app.log 2>/dev/null) bridge=$(wc -c < /root/bridge.log 2>/dev/null)"
    cp /root/boot.log /root/bridge.log /root/rtlk.log "$OUT/" 2>/dev/null
  fi
  sleep 5
done
cp /root/boot.log /root/bridge.log /root/rtlk.log /root/app.log "$OUT/" 2>/dev/null
md5sum "$IN/rt_lk.py" /workspace/rt_lk.py > "$OUT/rtlk_md5_after.txt" 2>&1
curl -s -m 10 127.0.0.1:8031/health > "$OUT/health_ditto_after_boot.json" 2>&1
if [ "$BRAIN" != 1 ]; then say "stage 6 FAILED: :8765 never answered 200"; echo FAILED > "$OUT/STACK"; else echo UP > "$OUT/STACK"; fi
grep -h "NOVA_FACE" "$OUT/bridge.log" "$OUT/rtlk.log" 2>/dev/null | head -5 | while read -r l; do say "    $l"; done

# ---------- stage 7: the harness, on GO ----------
say "stage 7: waiting for /workspace/in/GO (up to 20 min)"
for i in $(seq 1 240); do [ -e "$IN/GO" ] && break; sleep 5; done
if [ ! -e "$IN/GO" ]; then say "stage 7: no GO -- skipping the recording"; else
  [ -s "$OUT/PW_READY" ] || { say "stage 7: waiting on playwright"; wait $PW_PID; }
  say "stage 7: RECORDING -- live_intro_harness.py"
  python3 "$IN/live_intro_harness.py" --out "$OUT" --inbox "$IN" \
      --url "http://127.0.0.1:8765/beta/freeze?intro=freeze" --max-s "${REC_MAX_S:-900}" \
      > "$OUT/harness.log" 2>&1
  say "stage 7: harness rc=$? $(tail -1 "$OUT/harness.log")"
fi
cp /root/bridge.log /root/rtlk.log /root/app.log "$OUT/" 2>/dev/null
cp "$LOG/ditto_server.log" "$OUT/ditto_server_end.log" 2>/dev/null
cp /workspace/gallery/wd/ditto_stats.json "$OUT/ditto_stats.json" 2>/dev/null
curl -s -m 10 127.0.0.1:8031/health > "$OUT/health_ditto_end.json" 2>&1
ls -la "$OUT" > "$OUT/LISTING" 2>&1
say "ALL DONE -- waiting up to 20 min for /workspace/in/PULLED, then cleaning up"

# ---------- stage 8: leave the production volume as found ----------
for i in $(seq 1 240); do [ -s "$IN/PULLED" ] && break; sleep 5; done
if [ "$FACE" = ditto ]; then
  python3 "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert.txt" 2>&1
  say "revert lk_bridge.py rc=$? $(tail -2 "$OUT/revert.txt" | head -1)"
fi
[ -s "$OUT/rt_lk.volume.before.py" ] && cp "$OUT/rt_lk.volume.before.py" /workspace/rt_lk.py && say "rt_lk.py restored to the volume's original"
rm -f /workspace/lk_bridge.py.bak-ditto-* /workspace/nova_ditto.py
rm -rf "$OUT"
rm -f "$IN"/*.mp4 "$IN"/*.json "$IN"/*.py "$IN"/*.sh "$IN"/kid_*.txt "$IN"/GESTURE_* \
      "$IN"/PAYLOAD_DONE "$IN"/PULLED "$IN"/GO "$IN"/STOP
echo "footprint cleaned: $(ls -A "$IN" | wc -l) entries left in in/"
