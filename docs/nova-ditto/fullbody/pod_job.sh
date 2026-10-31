#!/usr/bin/env bash
# novaditto-fb job. The pod has Nova's PRODUCTION volume 1ditrne6cb mounted at /workspace, so:
#   * nothing on the volume is deleted, moved or overwritten;
#   * everything this job creates lives in /workspace/novaditto_fb_out (podsrv serves it) and
#     /workspace/in (podsrv's own upload dir, created by START);
#   * Ditto's ~6 GB install goes on the CONTAINER disk (/root/ditto), never the volume.
# Order is highest-value-first: each stage writes its result before the next one starts, so a
# failure late still leaves the earlier evidence pullable.
set -uo pipefail
IN=/workspace/in; MT=/root/mt; LOG=/root/logs; OUT=/workspace/novaditto_fb_out
mkdir -p "$MT/maya-ops/lt" "$MT/bench/replace_musetalk_alt" "$OUT" "$LOG"
say(){ echo "[job $(date -u +%H:%M:%S)] $*"; }

need="ditto_server.py ditto_up.sh ditto_wide.py ditto_fullbody.py sitecustomize.py drive.py recon.sh ditto_bridge_patch.py body_a.mp4 body_dance.mp4 audio.f32 PAYLOAD_DONE"
say "waiting for the payload"
for i in $(seq 1 240); do
  ok=1; for f in $need; do [ -s "$IN/$f" ] || ok=0; done
  [ $ok = 1 ] && break; sleep 5
done
for f in $need; do [ -s "$IN/$f" ] || { say "MISSING $f -- abort"; exit 11; }; done
say "payload complete"

# ---------- stage 1+2: read-only recon of the volume, and the bridge probe ----------
if [ "${SKIP_RECON:-0}" != "1" ]; then
  bash "$IN/recon.sh" > "$OUT/recon.log" 2>&1
  say "recon rc=$? -- $(wc -l < "$OUT/recon.log") lines"
  sed -n '1,200p' "$OUT/recon.log"
else
  say "recon skipped (done on the previous pod; the volume is left alone)"
fi

# ---------- stage 3: Ditto on the full-body bodies ----------
cp "$IN/ditto_server.py" "$IN/ditto_up.sh" "$MT/maya-ops/lt/"
cp "$IN/ditto_wide.py" "$MT/bench/replace_musetalk_alt/"
chmod +x "$MT/maya-ops/lt/ditto_up.sh"
md5sum "$MT/maya-ops/lt/ditto_server.py" "$MT/bench/replace_musetalk_alt/ditto_wide.py" "$IN/ditto_fullbody.py" | tee "$OUT/payload_md5.txt"

say "installing python3.10 dev headers -- Ditto builds core/utils/blend with pyximport at import"
(apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3.10-dev build-essential) > "$OUT/aptdev.log" 2>&1
if [ -e /usr/include/python3.10/Python.h ]; then say "Python.h OK"; else say "WARN Python.h STILL MISSING"; tail -5 "$OUT/aptdev.log"; fi

export PYTHONPATH="$IN:${PYTHONPATH:-}"
export DITTO_FB_ON=1 DITTO_FB_SHIM="$IN" DITTO_FB_BENCH="$MT/bench/replace_musetalk_alt"
export DITTO_FB_UP="${FB_UP:-3.0}"
export DITTO_ROOT=/root/ditto MAYA_LOGS="$LOG" DITTO_PORT=8031
export DITTO_AMP=0.6 DITTO_CHUNK=25 DITTO_PRIME=35 DITTO_VAD=1 DITTO_THREADS=6 DITTO_EYE_HOLD=1 DITTO_WAIT_SEC=1500

run_body () {            # tag, src, frames, explicit box
  local tag="$1" src="$2" nf="$3" box="$4" rc=0
  say "=== $tag: src=$(basename "$src") box=$box frames=$nf"
  export DITTO_SRC="$src" DITTO_FB_BOX="$box"
  pkill -f ditto_server.py 2>/dev/null; sleep 2; : > "$LOG/ditto_server.log"
  bash "$MT/maya-ops/lt/ditto_up.sh" > "$OUT/ditto_up_$tag.log" 2>&1; rc=$?
  curl -s -m 10 127.0.0.1:8031/health > "$OUT/health_$tag.json" 2>&1
  cp "$LOG/ditto_server.log" "$OUT/ditto_server_$tag.log" 2>/dev/null
  say "$tag ditto_up rc=$rc health=$(head -c 500 "$OUT/health_$tag.json")"
  if [ "$rc" != 0 ]; then say "$tag SERVER FAILED"; tail -40 "$OUT/ditto_up_$tag.log"; tail -40 "$OUT/ditto_server_$tag.log" 2>/dev/null; return 1; fi
  "$DITTO_ROOT/env/bin/python" "$IN/drive.py" "$IN/audio.f32" "$OUT/$tag.mp4" "$nf" > "$OUT/drive_$tag.log" 2>&1
  say "$tag drive rc=$? $(tail -1 "$OUT/drive_$tag.log")"
  curl -s -m 10 127.0.0.1:8031/health > "$OUT/health_${tag}_end.json" 2>&1
  cp "$LOG/ditto_server.log" "$OUT/ditto_server_$tag.log" 2>/dev/null
  ls -la "$OUT/$tag.mp4" 2>/dev/null
}

run_body fullbody_calm  "$IN/body_a.mp4"     "${FB_FRAMES:-1600}"       "$FB_BOX"
run_body fullbody_dance "$IN/body_dance.mp4" "${FB_DANCE_FRAMES:-500}"  "$FB_BOX_DANCE"

pkill -f ditto_server.py 2>/dev/null
say "ALL DONE"; ls -la "$OUT"
say "waiting up to 20 min for /workspace/in/PULLED, then cleaning our footprint off the volume"
for i in $(seq 1 240); do [ -s "$IN/PULLED" ] && break; sleep 5; done
# only things THIS job created: the uniquely-named out dir and our uploads. /workspace/logs and
# every pre-existing Nova file are left exactly as found.
rm -rf "$OUT"
rm -f "$IN"/*.mp4 "$IN"/*.f32 "$IN"/*.py "$IN"/*.sh "$IN"/PAYLOAD_DONE "$IN"/PULLED
say "volume footprint cleaned: $(ls -la "$IN" | wc -l) entries left in in/"
