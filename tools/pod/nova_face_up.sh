#!/usr/bin/env bash
# nova_face_up.sh -- Nova's face engine = DITTO, the one way every boot does it (2026-11-11, session nova-take8c).
#
#   bash tools/pod/nova_face_up.sh [BODY.mp4]          then launch lk_bridge.py with NOVA_FACE=ditto on ITS OWN line
#
# 1. starts the take-8 Ditto server (tools/pod/ditto_take8/) on 127.0.0.1:8031 with nova_take8.env and:
#      DITTO_OUT_W/H 720x1288   = the size lk_bridge publishes (its 2026-10-22 downscale), so the bridge resizes nothing
#      DITTO_FACE_ROBUST=1      = MediaPipe finds her ~155 px room face only with it (prebake_gate: 0 % found without)
#      BODY default             = beta/sources/groove-1080/tests/control-idle2.mp4 (nova_idle2), her calm talk body IN HER ROOM, full figure (Part 3, Refael
#                                 2026-11-11: "wide, her full body in her room, no talking head pre-game")
# 2. applies tools/pod/ditto_bridge_patch.py (A1-A8): Ditto frames, audio fed in the publishing process, the A/V
#    offset paid once, MuseTalk frames not converted (A6), one encoder / simulcast off (A7), face metadata (A8)
#    that shared/nova-face.js turns into the red banner when Ditto is missing.
# Measured (docs/nova-ditto/take8c/): Ditto alone on a Secure 4090 = 408 ms p50 / 475 ms p95 per 1 s chunk.
# It refuses loudly (exit 3) when Ditto does not come up -- no MuseTalk fallback.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); T8="$HERE/ditto_take8"
BODY=${1:-${NOVA_DITTO_BODY:-$HERE/../../beta/sources/groove-1080/tests/control-idle2.mp4}}   # = nova_idle2, her room (same file the take used)
LOG=${MAYA_LOGS:-/root/logs}; mkdir -p "$LOG"
[ -s "$BODY" ] || { echo "[nova_face_up] FATAL: body $BODY missing -- red banner, no fallback"; exit 3; }
# ditto_server.py imports ditto_wide.py from HERE/../../bench/replace_musetalk_alt (the maya-lt layout): build it once.
M=${NOVA_DITTO_TREE:-/root/m}; mkdir -p "$M/maya-ops/lt" "$M/bench/replace_musetalk_alt"
cp "$T8/ditto_server.py" "$T8/ditto_up.sh" "$T8/motion_bank.py" "$T8/ditto_pack_get.py" "$M/maya-ops/lt/"
cp "$T8/ditto_wide.py" "$M/bench/replace_musetalk_alt/"
(
  set -a; . "$T8/nova_take8.env"; set +a; unset DITTO_PACK MAYA_ASSETS_TOKEN
  export DITTO_ROOT=${DITTO_ROOT:-/root/ditto} MAYA_LOGS="$LOG" DITTO_PORT=8031 DITTO_SRC="$BODY" \
         DITTO_OUT_W=${DITTO_OUT_W:-720} DITTO_OUT_H=${DITTO_OUT_H:-1288} DITTO_FACE_ROBUST=${DITTO_FACE_ROBUST:-1}
  bash "$M/maya-ops/lt/ditto_up.sh"
) > "$LOG/nova_face_up.log" 2>&1
rc=$?
tail -1 "$LOG/nova_face_up.log"
[ $rc = 0 ] || { echo "[nova_face_up] FATAL: Ditto did not come up (rc=$rc) -- see $LOG/nova_face_up.log"; exit 3; }
python3 -I "$HERE/ditto_bridge_patch.py" --apply --sidecar "$HERE/nova_ditto.py" --wd "$LOG" > "$LOG/nova_face_patch.log" 2>&1 \
  || { echo "[nova_face_up] FATAL: bridge patch refused -- see $LOG/nova_face_patch.log"; exit 3; }
grep -E "APPLIED|already patched|A[678]" "$LOG/nova_face_patch.log"
echo "[nova_face_up] OK -- start lk_bridge.py with NOVA_FACE=ditto (bridge only; the brain must NOT get NOVA_FACE)"
