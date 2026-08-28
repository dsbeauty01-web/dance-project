#!/bin/bash
# maya-stack-setup.sh — reconstruct the interactive-stack RUNTIME on a fresh pod.
# WHY: 2026-08-28 dry-run attempt found a fresh pod's container is missing the
# engine/brain web+rtc deps (the _sys overlay has torch/cv2/av but NOT flask,
# aiortc, aiohttp), and the SRS binary was gone (only srs_nova.conf remained).
# This script installs the confirmed-missing pieces so bring-up is repeatable.
#
# STATUS: UNVERIFIED — written from the diagnosed gaps; must be RUN ON A POD once
# to confirm the full dep set (app.py / maya_rt.py may import more). Do NOT claim
# green until the import-check at the end passes on a real pod. (ground rule #4)
set -u
export PYTHONPATH=/workspace/_sys/pylibs311_good/dist-packages
FAIL=0

echo "== 1. system libs (apt) =="
apt-get update -qq 2>&1 | tail -1
# ffmpeg for our render/label path; opus/vpx are bundled in aiortc manylinux wheels
apt-get install -y -qq ffmpeg fonts-dejavu-core wget 2>&1 | tail -1

echo "== 2. python web/rtc deps NOT in the _sys overlay (confirmed missing 08-28) =="
# flask + aiortc were the two that broke the engine; the rest are the usual
# LiveTalking/maya-server runtime set. Pin loosely; tighten after a verified run.
pip install -q flask aiohttp "aiortc>=1.6" av soundfile requests websockets \
    edge-tts python-multipart uvicorn fastapi 2>&1 | tail -3

echo "== 3. SRS media server (binary was missing; conf persists) =="
if [ -x /workspace/srs/trunk/objs/srs ]; then
  echo "  srs binary present, skipping"
else
  echo "  srs binary MISSING — restore it. Options (need a human/pod decision):"
  echo "   a) rebuild:  cd /workspace/srs/trunk && ./configure && make   (slow)"
  echo "   b) fetch a prebuilt SRS 5.x linux release into objs/srs"
  echo "  srs_nova.conf is present at /workspace/srs_nova.conf"
  # NOTE: not auto-fetching a random binary — pin a trusted SRS release URL here
  # after the human approves the version.
fi

echo "== 4. verify the engine/brain imports (the real gate) =="
python - <<'PY'
mods = ["flask","aiohttp","aiortc","av","soundfile","requests","websockets"]
bad = []
for m in mods:
    try: __import__(m)
    except Exception as e: bad.append(f"{m}: {e}")
if bad:
    print("IMPORT CHECK FAILED:"); [print("  -", b) for b in bad]; raise SystemExit(1)
print("IMPORT CHECK PASS:", ", ".join(mods))
PY
rc=$?
[ $rc -ne 0 ] && FAIL=1

echo "== done =="
[ $FAIL -eq 0 ] && echo "SETUP OK (imports green) — SRS still needs step 3 if missing" \
                || echo "SETUP INCOMPLETE — see failures above"
exit $FAIL
