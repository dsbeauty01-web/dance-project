#!/usr/bin/env bash
# job1.sh -- nova-take8 step 1: re-render Nova's EN arrival clip with the take-8 Ditto recipe.
# Everything lives under /root. The network volume (/workspace) is NOT read or written by this job.
set -uo pipefail
O=/root/out; I=/root/in; mkdir -p $O/logs
say(){ echo "$(date -u +%T) $*" | tee -a $O/STATUS; }
say "job1 start"
# system libs + ffmpeg: apt with a hard cap, static ffmpeg in parallel (maya prof_job.sh 2026-11-10 fix)
( timeout -k 5 300 bash -c 'apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends libgl1 libegl1 libgles2 libglib2.0-0' > $O/logs/apt.log 2>&1; echo "apt rc=$?" >> $O/logs/apt.log ) &
PA=$!
( curl -fsSL -m 240 https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz \
   | tar -xJ --strip-components=2 -C /usr/local/bin --wildcards '*/bin/ffmpeg' '*/bin/ffprobe'; echo "ffstatic rc=$?" > $O/logs/ffstatic.log ) &
PF=$!
# the maya-lt layout ditto_server.py expects: HERE/../../bench/replace_musetalk_alt/ditto_wide.py
M=/root/m; mkdir -p $M/maya-ops/lt $M/bench/replace_musetalk_alt
cp $I/ditto_server.py $I/ditto_up.sh $I/motion_bank.py $I/ditto_pack_get.py $I/drive_gate.py $M/maya-ops/lt/
cp $I/ditto_wide.py $M/bench/replace_musetalk_alt/
set -a; . $I/nova_take8.env; set +a
unset DITTO_PACK MAYA_ASSETS_TOKEN
export DITTO_ROOT=/root/ditto MAYA_LOGS=$O/logs DITTO_SRC=$I/body_t8.mp4
wait $PF; say "$(cat $O/logs/ffstatic.log) ffmpeg=$(command -v ffmpeg)"
wait $PA; say "$(tail -1 $O/logs/apt.log)"
say "ditto_up (take-8 server, body_t8) ..."
bash $M/maya-ops/lt/ditto_up.sh > $O/logs/ditto_up.log 2>&1; rc=$?
say "ditto_up rc=$rc: $(tail -1 $O/logs/ditto_up.log | cut -c1-300)"
[ $rc = 0 ] || { say "FAILED ditto_up"; echo FAILED > $O/DONE1; exit 1; }
python3 -c "import numpy" 2>/dev/null || pip install -q numpy
say "render A: take-8 server + sharpened body"
python3 $I/render_intro.py $I/intro_en.wav $O/nova-arrival-take8.mp4 > $O/renderA.json 2>> $O/logs/render.log; say "render A rc=$? $(cut -c1-200 $O/renderA.json)"
# B: same server + settings, ORIGINAL body -> separates the body's share from the server's
pkill -f "[d]itto_server.py"; sleep 3
export DITTO_SRC=$I/body_orig.mp4
bash $M/maya-ops/lt/ditto_up.sh >> $O/logs/ditto_up.log 2>&1; say "ditto_up B rc=$?"
python3 $I/render_intro.py $I/intro_en.wav $O/nova-arrival-take8-origbody.mp4 > $O/renderB.json 2>> $O/logs/render.log; say "render B rc=$? $(cut -c1-200 $O/renderB.json)"
cp $O/logs/ditto_server.log $O/ditto_server.log 2>/dev/null
say "job1 done"; echo OK > $O/DONE1
