#!/usr/bin/env bash
# MACHINE-CERTIFY test/record_loop.sh — certify_loop + delivery recording (--record).
# Same Edge-owns-the-browser pattern as certify_loop.sh; the runner reloads the page
# once to arm the audio tap, then screencasts the whole session. Graded like any run —
# a delivery video only counts if ITS OWN session is clean.
#   bash test/record_loop.sh <lang> <n> <podid> <ssh_host> <ssh_port>
set -u
LANG_ARG="${1:?lang}"; N="${2:?n}"; POD="${3:?podid}"
HOST="${4:?ssh_host}"; PORT_SSH="${5:?ssh_port}"
DIR="test/sessions/${LANG_ARG}-${N}"
CDP_PORT=$((9500 + (RANDOM % 100)))
EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
[ -f "$EDGE" ] || EDGE="/c/Program Files/Microsoft/Edge/Application/msedge.exe"
URL="https://${POD}-8765.proxy.runpod.net/freeze?test=1&nolog=1"
[ "$LANG_ARG" = "he" ] && URL="${URL}&lang=he"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i $HOME/.ssh/id_ed25519"

OFF=$(ssh $SSH_OPTS -p "$PORT_SSH" root@"$HOST" "wc -c < /root/rtlk.log" 2>/dev/null | tr -d ' \r')
echo "== RECORD session $DIR (pod $POD, rtlk offset $OFF, cdp $CDP_PORT) =="
rm -rf "$DIR"; mkdir -p "$DIR"

PROFILE="$PWD/$DIR/profile-$$"
"$EDGE" --remote-debugging-port=$CDP_PORT --user-data-dir="$PROFILE" \
  --autoplay-policy=no-user-gesture-required --deny-permission-prompts \
  --no-first-run --no-default-browser-check --window-size=1280,800 \
  --mute-audio --headless=new "$URL" > "$DIR/browser.log" 2>&1 &
EDGE_PID=$!
for i in $(seq 1 30); do curl -s -m 2 "http://127.0.0.1:$CDP_PORT/json/version" >/dev/null 2>&1 && break; sleep 1; done
echo "browser up (pid $EDGE_PID)"

node test/run_session.js --lang "$LANG_ARG" --n "$N" --pod "$POD" --out "$DIR" --attach --port "$CDP_PORT" --record
RC=$?

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | Where-Object { \$_.CommandLine -match 'profile-' -and \$_.CommandLine -match '${LANG_ARG}-${N}' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" 2>/dev/null
kill $EDGE_PID 2>/dev/null

ssh $SSH_OPTS -p "$PORT_SSH" root@"$HOST" "tail -c +$((OFF+1)) /root/rtlk.log" 2>/dev/null > "$DIR/rtlk.log"
echo "runner rc=$RC, rtlk delta $(wc -c < "$DIR/rtlk.log" | tr -d ' ') bytes"
node test/grade.js "$DIR"
exit $?
