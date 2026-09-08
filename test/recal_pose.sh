#!/usr/bin/env bash
# DETECTION-MIGRATE test/recal_pose.sh — one recalibration phase, locally (no pod):
#   local static server (repo root) -> Edge detached (certify_loop.sh pattern:
#   node-spawned Chrome dies on this machine) -> node test/recal_pose.js -> teardown.
#   bash test/recal_pose.sh math|video
set -u
PHASE="${1:?phase math|video}"
CDP_PORT=$((9500 + (RANDOM % 100)))
HTTP_PORT=8123
DIR="test/sessions/recal-$PHASE"
EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
[ -f "$EDGE" ] || EDGE="/c/Program Files/Microsoft/Edge/Application/msedge.exe"
URL="http://127.0.0.1:${HTTP_PORT}/beta/freeze.html?test=1&nolog=1"
[ "$PHASE" = "video" ] && URL="${URL}&pose=1"
rm -rf "$DIR"; mkdir -p "$DIR"

python -m http.server "$HTTP_PORT" --bind 127.0.0.1 > "$DIR/http.log" 2>&1 &
HTTP_PID=$!

CAM_FLAGS=""
if [ "$PHASE" = "video" ]; then
  Y4M="$PWD/test/sessions/cam_person.y4m"
  [ -f "$Y4M" ] || { echo "missing $Y4M (ffmpeg step)"; kill $HTTP_PID; exit 3; }
  Y4M_WIN=$(cygpath -w "$Y4M" 2>/dev/null || echo "$Y4M")
  # NOTE (2026-09-08): the flag is --use-fake-device-for-media-STREAM on current Chromium;
  # the old -capture spelling is silently ignored (real devices enumerate, gum hangs).
  CAM_FLAGS="--use-fake-ui-for-media-stream --use-fake-device-for-media-stream --use-file-for-fake-video-capture=$Y4M_WIN"
  # Edge refuses fake capture on this machine even with the right flag; Chrome honors it.
  EDGE="/c/Program Files/Google/Chrome/Application/chrome.exe"
fi

PROFILE="$PWD/$DIR/profile-$$"
"$EDGE" --remote-debugging-port=$CDP_PORT --user-data-dir="$PROFILE" \
  --autoplay-policy=no-user-gesture-required --no-first-run --no-default-browser-check \
  --window-size=1280,800 --mute-audio --headless=new $CAM_FLAGS "$URL" > "$DIR/browser.log" 2>&1 &
EDGE_PID=$!
for i in $(seq 1 30); do curl -s -m 2 "http://127.0.0.1:$CDP_PORT/json/version" >/dev/null 2>&1 && break; sleep 1; done
echo "browser up (pid $EDGE_PID, cdp $CDP_PORT)"

node test/recal_pose.js --phase "$PHASE" --port "$CDP_PORT" --out "$DIR"
RC=$?

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe' OR Name='chrome.exe'\" | Where-Object { \$_.CommandLine -match 'profile-' -and \$_.CommandLine -match 'recal-${PHASE}' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" 2>/dev/null
kill $EDGE_PID 2>/dev/null
kill $HTTP_PID 2>/dev/null
echo "recal $PHASE rc=$RC"
exit $RC
