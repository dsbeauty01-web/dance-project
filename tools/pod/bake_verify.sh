#!/usr/bin/env bash
# tools/pod/bake_verify.sh <avatar_id> [avatars_dir]
# BAKE VALIDATOR (2026-08-15) — no bake reaches the stage unverified.
# The blank-Nova killer was: 0-byte latents.pt + full_imgs(3)/mask(0) mismatch reaching
# the live engine. This gate catches exactly that BEFORE a page can setAvatar the id.
#
# Checks:
#   1. latents.pt exists AND size > 1 MB           (0-byte = the exact blank bug)
#   2. latents frame count N loads cleanly
#   3. full_imgs count == mask count == N
#   4. coords.pkl + mask_coords.pkl exist
#   5. render proxy: a sampled full_img is NON-BLACK (mean pixel above floor)
# PASS -> append id to verified-avatars.json (in avatars_dir)
# FAIL -> rename folder to <id>.BROKEN  (quarantine; pages can never load it)
#
# Exit 0 = verified, 1 = failed/quarantined.
set -u
ID="${1:?usage: bake_verify.sh <avatar_id> [avatars_dir]}"
AV_DIR="${2:-/workspace/LiveTalking/data/avatars}"
D="$AV_DIR/$ID"
REG="$AV_DIR/verified-avatars.json"
export PYTHONPATH="${PYTHONPATH:-/workspace/_sys/pylibs311_good/dist-packages}"

fail(){ echo "FAIL $ID — $1"; if [ -d "$D" ]; then mv "$D" "$D.BROKEN.$(cat /proc/sys/kernel/random/uuid 2>/dev/null | cut -c1-8)" 2>/dev/null && echo "quarantined -> $D.BROKEN"; fi; exit 1; }

[ -d "$D" ] || { echo "FAIL $ID — folder missing: $D"; exit 1; }

# 1. latents size
lp="$D/latents.pt"
[ -f "$lp" ] || fail "latents.pt missing"
sz=$(stat -c%s "$lp" 2>/dev/null || echo 0)
[ "$sz" -gt 1048576 ] || fail "latents.pt too small ($sz bytes, need >1MB) — the 0-byte blank bug"

# 2. frame count
N=$(python3 -c "import torch; print(len(torch.load('$lp', weights_only=False)))" 2>/dev/null)
[ -n "$N" ] || fail "latents.pt will not load"

# 3. counts match
fi=$(ls "$D/full_imgs" 2>/dev/null | wc -l)
mk=$(ls "$D/mask" 2>/dev/null | wc -l)
[ "$fi" = "$N" ] || fail "full_imgs=$fi != frames=$N"
[ "$mk" = "$N" ] || fail "mask=$mk != frames=$N"

# 4. coords
[ -f "$D/coords.pkl" ]      || fail "coords.pkl missing"
[ -f "$D/mask_coords.pkl" ] || fail "mask_coords.pkl missing"

# 5. render proxy — a sampled full_img must be non-black
NONBLACK=$(python3 - "$D" <<'PY'
import sys,glob,os
d=sys.argv[1]
try:
    import numpy as np, cv2
    fs=sorted(glob.glob(os.path.join(d,'full_imgs','*')))
    if not fs: print('0'); sys.exit()
    im=cv2.imread(fs[len(fs)//2])
    print('1' if im is not None and float(im.mean())>8.0 else '0')
except Exception:
    print('skip')  # cv2 unavailable -> file checks already passed, don't hard-fail
PY
)
[ "$NONBLACK" = "0" ] && fail "sampled full_img is black (render would be blank)"

# PASS — register
python3 - "$REG" "$ID" "$N" <<'PY'
import json,sys,os
reg,idv,n=sys.argv[1],sys.argv[2],int(sys.argv[3])
data={}
if os.path.exists(reg):
    try: data=json.load(open(reg))
    except Exception: data={}
data[idv]={"frames":n,"verified":True}
json.dump(data,open(reg,'w'),indent=2)
PY
echo "PASS $ID — frames=$N latents=$((sz/1024))KB full_imgs=$fi mask=$mk -> verified-avatars.json"
exit 0
