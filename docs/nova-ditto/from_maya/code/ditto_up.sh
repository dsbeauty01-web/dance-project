#!/usr/bin/env bash
# ditto_up.sh -- bring up ditto_server.py on :${DITTO_PORT:-8031} (lane/live-trio 2026-10-25; only runs when
# SHIM_RENDERER=ditto_renderer:Renderer -- the renderer calls it from __init__, before READY, never on air).
# The golden image has no Ditto. Same stack lane/replace-musetalk-alt proved on nvcr tensorrt:23.10 (bench/pod/stage_rm2.sh),
# here as a py3.10 venv with Ditto's own pinned pip set (environment.yaml): torch 2.5.1 cu121 + TensorRT 8.6.1 from pip
# (the shipped engines are TRT 8.6.1 "Ampere_Plus"). Idempotent: a second call only (re)starts the server.
set -uo pipefail
W=${DITTO_ROOT:-/workspace/ditto}; LOG=${MAYA_LOGS:-/workspace/logs}; mkdir -p "$W" "$LOG"
MO=$(cd "$(dirname "$0")" && pwd); PORT=${DITTO_PORT:-8031}
say(){ echo "[ditto_up $(date -u +%H:%M:%S)] $*"; }
curl -fsS -m2 "http://127.0.0.1:$PORT/health" 2>/dev/null | grep -q '"ready": *true' && { say "already ready"; exit 0; }
export PIP_ROOT_USER_ACTION=ignore HF_HUB_ENABLE_HF_TRANSFER=0 PYTHONUNBUFFERED=1 UV_HTTP_TIMEOUT=300
t0=$(date +%s)
[ -e "$W/.env_failed" ] && { say "FATAL env failed earlier (see ditto_setup_env.log)"; exit 3; }
if [ ! -s "$W/.env_ok" ]; then
  python3 -m pip install -q uv huggingface_hub > "$LOG/ditto_setup_hub.log" 2>&1
  ( [ -d "$W/src/.git" ] || git clone -q https://github.com/antgroup/ditto-talkinghead "$W/src"
    git -C "$W/src" log -1 --format='ditto %H %ci'
    python3 - <<'PY'
import os
from huggingface_hub import snapshot_download
W = os.environ.get("DITTO_ROOT", "/workspace/ditto")
snapshot_download("digital-avatar/ditto-talkinghead", local_dir=f"{W}/ckpt", max_workers=16,
                  allow_patterns=["ditto_trt_Ampere_Plus/*.engine", "ditto_cfg/v0.4_hubert_cfg_trt_online.pkl",
                                  "ditto_onnx/libgrid_sample_3d_plugin.so", "LICENSE", "README.md"])
print("W_OK")
PY
  ) >> "$LOG/ditto_setup_weights.log" 2>&1 &
  PW=$!
  ( set +e; step(){ echo "== $(date -u +%T) $*"; }
    step venv; uv venv -q --clear -p 3.10 "$W/env" || exit 1; . "$W/env/bin/activate"
    step torch; uv pip install -q torch==2.5.1 --index-url https://download.pytorch.org/whl/cu121 || exit 1
    step trt+deps; uv pip install -q --extra-index-url https://pypi.nvidia.com "tensorrt-libs==8.6.1" "tensorrt-bindings==8.6.1" \
         "cuda-python==12.2.1" polygraphy colored librosa==0.10.2.post1 tqdm filetype imageio imageio-ffmpeg \
         opencv-python-headless==4.10.0.84 scikit-image scipy cython einops mediapipe==0.10.14 soundfile || exit 1
    step numpy; uv pip install -q --no-deps numpy==2.0.1
    # TensorRT 8.6 links libcudnn.so.8; torch 2.5.1 pins cuDNN 9 under the SAME pip name -> cuDNN 8.9 goes to its own dir
    step cudnn8; uv pip install -q --no-deps --target "$W/cudnn8" nvidia-cudnn-cu12==8.9.7.29 || exit 1
    SPK=$(python -c "import site; print(site.getsitepackages()[0])")
    LP="$W/cudnn8/nvidia/cudnn/lib"; for d in "$SPK"/tensorrt_libs "$SPK"/nvidia/*/lib; do [ -d "$d" ] && LP="$LP:$d"; done
    export LD_LIBRARY_PATH="$LP:${LD_LIBRARY_PATH:-}"
    for m in torch tensorrt cv2 librosa mediapipe cuda.cudart; do python -c "import $m; print('import ok', '$m', getattr($m, '__version__', ''))" 2>&1 | tail -3; done
    # tensorrt-bindings 8.6.1 ships the module as `tensorrt_bindings`; the `tensorrt` meta sdist (which only re-runs pip) fails
    # to build under a venv. A two-line alias package does what the meta package would.
    python -c "import tensorrt" 2>/dev/null || { step "tensorrt alias -> tensorrt_bindings"
      SPK=$(python -c "import site; print(site.getsitepackages()[0])"); mkdir -p "$SPK/tensorrt"
      printf 'import sys, tensorrt_bindings as _b\nsys.modules[__name__] = _b\n' > "$SPK/tensorrt/__init__.py"
      python -c "import tensorrt; print('tensorrt alias ok', tensorrt.__version__, hasattr(tensorrt, 'Runtime'))" 2>&1 | tail -3; }
    python -c "import torch, tensorrt, cv2, librosa; from cuda import cuda, cudart; print('DITTO_ENV_OK', torch.__version__, tensorrt.__version__, cv2.__version__)" ) >> "$LOG/ditto_setup_env.log" 2>&1 &
  PE=$!
  curl -fsSL -m 120 -o "$W/face_landmarker.task" \
    https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task || say "WARN face_landmarker.task"
  ldconfig -p 2>/dev/null | grep -q libGLESv2.so.2 || { (apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq libgles2 libegl1 libgl1 > /dev/null 2>&1) || say "WARN libgles2/libegl1"; }
  wait $PW $PE
  grep -q W_OK "$LOG/ditto_setup_weights.log" || { touch "$W/.env_failed"; say "FATAL weights"; tail -8 "$LOG/ditto_setup_weights.log"; exit 3; }
  grep -q DITTO_ENV_OK "$LOG/ditto_setup_env.log" || { touch "$W/.env_failed"; say "FATAL env"; tail -20 "$LOG/ditto_setup_env.log"; exit 3; }
  date -u > "$W/.env_ok"; say "setup done in $(( $(date +%s) - t0 )) s ($(du -sh "$W" 2>/dev/null | cut -f1))"
fi
# TensorRT / CUDA runtime libs from the venv's wheels (the image has neither TRT 8.6 nor libcudart 12.1 on the path)
SP=$("$W/env/bin/python" -c "import site; print(site.getsitepackages()[0])")
LP="$W/cudnn8/nvidia/cudnn/lib"; for d in "$SP"/tensorrt_libs "$SP"/nvidia/*/lib; do [ -d "$d" ] && LP="$LP:$d"; done
export LD_LIBRARY_PATH="${LP#:}:${LD_LIBRARY_PATH:-}"
export DITTO_LM=${DITTO_LM:-$W/face_landmarker.task} OMP_NUM_THREADS=${DITTO_THREADS:-6} OPENBLAS_NUM_THREADS=${DITTO_THREADS:-6} MKL_NUM_THREADS=${DITTO_THREADS:-6}
pkill -f ditto_server.py 2>/dev/null
DITTO_PORT=$PORT nohup "$W/env/bin/python" "$MO/ditto_server.py" >> "$LOG/ditto_server.log" 2>&1 &
SPID=$!; say "ditto_server pid $SPID on :$PORT (src ${DITTO_SRC:-?})"
for i in $(seq 1 240); do
  h=$(curl -fsS -m2 "http://127.0.0.1:$PORT/health" 2>/dev/null)
  echo "$h" | grep -q '"ready": *true' && { say "ready after $(( $(date +%s) - t0 )) s: $h"; exit 0; }
  echo "$h" | grep -q '"error": *"' && { say "FATAL server: $h"; tail -30 "$LOG/ditto_server.log"; exit 3; }
  kill -0 $SPID 2>/dev/null || { say "FATAL ditto_server exited"; tail -30 "$LOG/ditto_server.log"; exit 3; }
  sleep 2
done
say "FATAL ditto_server not ready in 480 s"; tail -30 "$LOG/ditto_server.log"; exit 3
