s = open("/dev/shm/t8/src/novaditto_job.sh").read()


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("# novaditto_job.sh -- session novaditto-final, 2026-11-02.",
    "# job3.sh -- session nova-take8, 2026-11-11: novaditto_job.sh (2026-11-02, the run that recorded) with\n"
    "# the take-8 Ditto server + nova_take8.env, the TIMELINE sidecar, body = $BODY, results under\n"
    "# /root/out/live, and a take 2 on the game page (the freeze welcome line). Original header follows.\n"
    "# novaditto_job.sh -- session novaditto-final, 2026-11-02.")
rep('IN=/root/in; OUT=/root/novaditto_out; MT=/root/mt; LOG=/root/logs',
    'IN=/root/in; OUT=/root/out/live; MT=/root/m; LOG=/root/out/logs\nBODY=$(cat /root/in/BODY_NAME)')
# the CMD channel already exists (job2)
rep('''( while true; do
    if [ -s "$IN/CMD" ]; then
      ts=$(date -u +%H%M%S); mv "$IN/CMD" "/root/cmd.$ts.sh" 2>/dev/null \\
        && bash "/root/cmd.$ts.sh" > "$OUT/CMD_OUT.$ts" 2>&1
      echo "rc=$?" >> "$OUT/CMD_OUT.$ts"
    fi
    sleep 3
  done ) &
say "stage 0b: CMD channel open (PUT /put/CMD -> runs once -> novaditto_out/CMD_OUT.<hhmmss>)"''',
    'say "stage 0b: CMD channel is job2\'s (/root/in/CMD_<name>.sh)"')
rep('''need="novalive_job.sh repair_pylibs.py real_harness.py ditto_bridge_patch.py nova_ditto.py boot_wrap.py \\
ditto_server.py ditto_up.sh ditto_wide.py motion_bank.py nova_idle.mp4 nova_idle.gate.json \\
beta__freeze.html libtorch_global_deps.so PAYLOAD_DONE"''',
    '''need="repair_pylibs.py real_harness.py ditto_bridge_patch.py nova_ditto.py boot_wrap.py \\
ditto_server.py ditto_up.sh ditto_wide.py motion_bank.py nova_take8.env $BODY \\
beta__freeze.html libtorch_global_deps.so PAYLOAD_DONE"''')
rep('say "stage 0 OK: $(ls -1 "$IN" | wc -l) files, nova_idle.mp4 = $(stat -c %s "$IN/nova_idle.mp4") bytes"',
    'say "stage 0 OK: $(ls -1 "$IN" | wc -l) files, body $BODY = $(stat -c %s "$IN/$BODY") bytes"')
# stage 3: take-8 server (already laid out in /root/m by job1), take-8 env, the chosen body
rep('''cp "$IN/ditto_server.py" "$IN/ditto_up.sh" "$IN/motion_bank.py" "$MT/maya-ops/lt/"
cp "$IN/ditto_wide.py" "$MT/bench/replace_musetalk_alt/"
chmod +x "$MT/maya-ops/lt/ditto_up.sh"
say "stage 3: ditto_up.sh in the background -- src nova_idle.mp4 (69 frames, so the prime is short)"''',
    '''pkill -f "[d]itto_server.py"; sleep 2
say "stage 3: ditto_up.sh (take-8 server, nova_take8.env) in the background -- src $BODY"''')
rep('''  export DITTO_AMP=0.6 DITTO_CHUNK=25 DITTO_PRIME=35 DITTO_VAD=1 DITTO_THREADS=6 DITTO_EYE_HOLD=1
  export DITTO_WAIT_SEC=1500
  export DITTO_SRC="$IN/nova_idle.mp4"''',
    '''  set -a; . "$IN/nova_take8.env"; set +a; unset DITTO_PACK MAYA_ASSETS_TOKEN
  export DITTO_ROOT=/root/ditto MAYA_LOGS="$LOG" DITTO_PORT=8031
  export DITTO_SRC="$IN/$BODY"''')
# take URL is a parameter; take 2 = the game page (intro=freeze is hardcoded in it: the welcome line)
rep('''run_harness(){   # $1 = tag, $2 = max seconds''', '''run_harness(){   # $1 = tag, $2 = max seconds, $3 = page path''')
rep('''     --url "http://127.0.0.1:8765/beta/freeze?commercial=1" \\
     > "$OUT/harness.$1.log" 2>&1''', '''     --url "http://127.0.0.1:8765${3:-/beta/freeze?commercial=1}" \\
     > "$OUT/harness.$1.log" 2>&1''')
rep('''  say "stage 9: take 0 is the AUDIO PROOF run -- she greets, nobody answers, 45 s"
  run_harness 0 45
  audio_proof''', '''  say "stage 9: take 0 skipped this session (budget): take 1 is the intro"''')
rep('''    if [ -e "$IN/GO2" ]; then run_harness 2 "${REC_MAX_S2:-110}"; audio_proof; fi''',
    '''    if [ -e "$IN/GO2" ]; then rm -f "$IN"/kid_*.txt; run_harness 2 "${REC_MAX_S2:-60}" "/beta/freeze"; audio_proof; fi''')
rep('''cp "/workspace/gallery/wd/ditto_stats.json" "$OUT/ditto_stats.take$1.json" 2>/dev/null''',
    '''cp "/workspace/gallery/wd/ditto_stats.json" "$OUT/ditto_stats.take$1.json" 2>/dev/null
  cp "/workspace/gallery/wd/ditto.log" "$OUT/ditto_sidecar.take$1.log" 2>/dev/null''')
rep('for i in $(seq 1 300); do [ -s "$IN/PULLED" ] && break; sleep 5; done\npython3 -I "$IN/ditto_bridge_patch.py" --revert',
    'for i in $(seq 1 120); do [ -s "$IN/PULLED" ] && break; sleep 5; done\npython3 -I "$IN/ditto_bridge_patch.py" --revert')
open("/dev/shm/t8/up/job3.sh", "w").write(s)
print("job3 written", len(s))
