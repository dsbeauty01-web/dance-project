#!/bin/bash
# maya-stack-setup.sh v2 — reconstruct the interactive-stack RUNTIME on a fresh pod.
# IDEMPOTENT: run twice = same result (pip "already satisfied" is a no-op).
# Dep list pulled from the AUTHORITATIVE sources (2026-08-29), not trial-and-error:
#   LiveTalking/requirements.txt + maya-server/requirements.txt + actual imports of
#   app.py (engine) / maya_rt.py (brain) / maya-server/app.py (director).
# Lessons baked in:
#   - `--ignore-installed blinker` (Ubuntu ships blinker 1.4 as distutils; flask's
#      dep resolution aborts the whole install without this).
#   - heavy ML (torch/transformers/diffusers/opencv/librosa/numpy) lives in the
#      persistent _sys overlay — we only INSTALL if missing, never blindly reinstall.
#   - NO heavy parallel builds here (the SRS `make -j` OOM killed a pod — SRS is a
#      separate, dedicated step that writes its binary to the VOLUME).
set -u
OVERLAY=/workspace/_sys/pylibs311_good/dist-packages
export PYTHONPATH="$OVERLAY"
PIP="pip install -q --ignore-installed blinker"

echo "== 1. system libs (apt, idempotent) =="
apt-get update -qq 2>&1 | tail -1
apt-get install -y -qq ffmpeg fonts-dejavu-core wget 2>&1 | tail -1

echo "== 2. web/util deps the engine+brain+director need (from requirements) =="
# lightweight, always ensure present (pip is a no-op if satisfied):
$PIP flask aiortc "aiohttp>=3.9" aiohttp_cors python-dotenv edge_tts \
     "websockets==12.0" dashscope openai av soundfile \
     "fastapi==0.115.6" "uvicorn[standard]==0.34.0" \
     livekit livekit-api 2>&1 | tail -3

echo "== 3. heavy ML deps: install ONLY if not already importable from the overlay =="
ensure(){  # $1 = import name, $2 = pip name
  if python -c "import $1" >/dev/null 2>&1; then echo "  $1: present";
  else echo "  $1: installing ($2)"; $PIP "$2" 2>&1 | tail -1; fi
}
ensure torch torch
ensure cv2 opencv-python-headless
ensure numpy numpy
ensure transformers transformers
ensure diffusers diffusers
ensure librosa librosa
ensure accelerate accelerate

echo "== 4. SRS media server (video output) — NOT built here on purpose =="
if [ -x /workspace/srs/objs/srs ]; then echo "  srs binary present on volume (good)";
else echo "  srs ABSENT — dedicated step next session: clone+build ONCE, copy the";
     echo "  binary to /workspace/srs/objs/srs on the VOLUME so it never rebuilds."; fi

echo "== 5. GATE: verify every import the stack needs =="
python - <<'PY'
eng=["flask","aiortc","aiohttp","aiohttp_cors","dotenv","edge_tts","websockets","av","openai","torch","cv2","numpy","transformers","diffusers","librosa","soundfile"]
brain=["livekit","aiohttp","openai"]
srv=["fastapi","uvicorn"]
bad=[]
for grp,mods in [("engine",eng),("brain",brain),("server",srv)]:
    for m in mods:
        try: __import__(m)
        except Exception as e: bad.append(f"{grp}/{m}: {e.__class__.__name__} {e}")
if bad:
    print("IMPORT GATE FAILED:"); [print("  -",b) for b in bad]; raise SystemExit(1)
print("IMPORT GATE PASS — engine+brain+server deps all import")
PY
rc=$?
echo "== done (rc=$rc) =="
exit $rc
