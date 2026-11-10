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
# DITTO_PACK=<release tag> (BOOT-FIX 2026-11-05; default empty = unchanged): the whole $W folder -- venv, managed
# python, TRT engines, weights, Ditto source, face_landmarker -- prebuilt by .github/workflows/build-ditto-pack.yml from
# THIS script (same pins), downloaded from the repo's GitHub release in parallel parts and unpacked. No pip, no PyTorch
# index, no Hugging Face at boot: those three are where boots spent 2 to 13+ minutes. Any pack problem is said out loud
# and the normal install below runs instead.
if [ -n "${DITTO_PACK:-}" ] && [ ! -s "$W/.env_ok" ]; then
  if [ "$W" != /workspace/ditto ]; then say "PACK SKIPPED: DITTO_ROOT=$W (the pack is built for /workspace/ditto)"
  else
    tp=$(date +%s); PK=/workspace/.ditto_pack; mkdir -p "$PK"
    if timeout -k 5 "${DITTO_PACK_TIMEOUT:-420}" python3 "$MO/ditto_pack_get.py" "$DITTO_PACK" "$PK" /workspace > "$LOG/ditto_pack.log" 2>&1 \
       && [ -s "$W/.env_ok" ]; then
      rm -rf "$PK"
      SPK=$("$W/env/bin/python" -c "import site; print(site.getsitepackages()[0])" 2>>"$LOG/ditto_pack.log")
      LPK="$W/cudnn8/nvidia/cudnn/lib"; for d in "$SPK"/tensorrt_libs "$SPK"/nvidia/*/lib; do [ -d "$d" ] && LPK="$LPK:$d"; done
      if LD_LIBRARY_PATH="$LPK" "$W/env/bin/python" -c "import torch, tensorrt, cv2, librosa; from cuda import cuda, cudart; print('DITTO_ENV_OK', torch.__version__, tensorrt.__version__, cv2.__version__)" >> "$LOG/ditto_pack.log" 2>&1; then
        say "pack $DITTO_PACK ready in $(( $(date +%s) - tp )) s ($(grep PACK_OK "$LOG/ditto_pack.log" | cut -c1-140))"
      else
        say "PACK FAILED import check -- installing the slow way (see ditto_pack.log)"; rm -rf "$W"; mkdir -p "$W"
      fi
    else
      say "PACK FAILED after $(( $(date +%s) - tp )) s: $(tail -1 "$LOG/ditto_pack.log" | cut -c1-160) -- installing the slow way"
      rm -rf "$PK" "$W"; mkdir -p "$W"
    fi
  fi
fi
if [ ! -s "$W/.env_ok" ]; then
  # the caller's system pip may still be running (prof_job.sh): two pips in one site-packages at once can break both
  [ -n "${DITTO_WAIT_PIP_LOG:-}" ] && { for i in $(seq 1 180); do grep -q "pip rc=" "$DITTO_WAIT_PIP_LOG" 2>/dev/null && break; sleep 2; done; }
  python3 -m pip install -q uv huggingface_hub > "$LOG/ditto_setup_hub.log" 2>&1
  ( [ -d "$W/src/.git" ] || timeout -k 5 300 git clone -q https://github.com/antgroup/ditto-talkinghead "$W/src"
    git -C "$W/src" log -1 --format='ditto %H %ci'
    timeout -k 5 "${DITTO_T_UV:-600}" python3 - <<'PY'
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
    step torch; timeout -k 10 "${DITTO_T_UV:-600}" uv pip install -q torch==2.5.1 --index-url https://download.pytorch.org/whl/cu121 || exit 1
    step trt+deps; timeout -k 10 "${DITTO_T_UV:-600}" uv pip install -q --extra-index-url https://pypi.nvidia.com "tensorrt-libs==8.6.1" "tensorrt-bindings==8.6.1" \
         "cuda-python==12.2.1" polygraphy colored librosa==0.10.2.post1 tqdm filetype imageio imageio-ffmpeg \
         opencv-python-headless==4.10.0.84 scikit-image scipy cython einops mediapipe==0.10.14 soundfile || exit 1
    step numpy; uv pip install -q --no-deps numpy==2.0.1
    # TensorRT 8.6 links libcudnn.so.8; torch 2.5.1 pins cuDNN 9 under the SAME pip name -> cuDNN 8.9 goes to its own dir
    step cudnn8; timeout -k 10 "${DITTO_T_UV:-600}" uv pip install -q --no-deps --target "$W/cudnn8" nvidia-cudnn-cu12==8.9.7.29 || exit 1
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
  # setup-only runs beside prof_job.sh's own apt-get (which installs these libs): a second apt would fight it for the dpkg lock
  [ "${DITTO_SETUP_ONLY:-0}" = 1 ] || ldconfig -p 2>/dev/null | grep -q libGLESv2.so.2 || { (apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq libgles2 libegl1 libgl1 > /dev/null 2>&1) || say "WARN libgles2/libegl1"; }
  wait $PW $PE
  grep -q W_OK "$LOG/ditto_setup_weights.log" || { touch "$W/.env_failed"; say "FATAL weights"; tail -8 "$LOG/ditto_setup_weights.log"; exit 3; }
  grep -q DITTO_ENV_OK "$LOG/ditto_setup_env.log" || { touch "$W/.env_failed"; say "FATAL env"; tail -20 "$LOG/ditto_setup_env.log"; exit 3; }
  date -u > "$W/.env_ok"; say "setup done in $(( $(date +%s) - t0 )) s ($(du -sh "$W" 2>/dev/null | cut -f1))"
fi
# DITTO_SETUP_ONLY=1 (default 0 = unchanged): stop after the venv + weights, start no server. prof_job.sh runs this at
# second 0, in parallel with its repo clone (2-7 min), so the slow torch download is not queued behind the clone.
[ "${DITTO_SETUP_ONLY:-0}" = 1 ] && { say "setup only: env ready, server not started"; exit 0; }
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
