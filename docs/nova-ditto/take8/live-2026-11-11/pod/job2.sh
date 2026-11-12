#!/usr/bin/env bash
# job2.sh -- (a) a command channel: /root/in/CMD_<name>.sh runs once, output to /root/out/cmd/<name>.out
#            (b) step 1 again after the Python.h fix (Ditto's Cython blend needs python3.10-dev)
set -uo pipefail
O=/root/out; I=/root/in; M=/root/m; mkdir -p $O/cmd
say(){ echo "$(date -u +%T) $*" | tee -a $O/STATUS; }
( while true; do for f in $I/CMD_*.sh; do [ -s "$f" ] || continue; n=$(basename "$f" .sh); [ -e "$O/cmd/$n.started" ] && continue
    touch "$O/cmd/$n.started"; ( bash "$f" > "$O/cmd/$n.out" 2>&1; echo "rc=$?" >> "$O/cmd/$n.out" ) & done; sleep 3; done ) &
say "job2: CMD channel open"
( DEBIAN_FRONTEND=noninteractive timeout -k 5 400 apt-get install -y -qq --no-install-recommends python3.10-dev build-essential ) > $O/logs/aptdev.log 2>&1
say "apt python3.10-dev rc=$? Python.h=$([ -e /usr/include/python3.10/Python.h ] && echo yes || echo NO)"
set -a; . $I/nova_take8.env; set +a
unset DITTO_PACK MAYA_ASSETS_TOKEN
export DITTO_ROOT=/root/ditto MAYA_LOGS=$O/logs
for v in A B; do
  if [ $v = A ]; then export DITTO_SRC=$I/body_t8.mp4; out=nova-arrival-take8.mp4; else export DITTO_SRC=$I/body_orig.mp4; out=nova-arrival-take8-origbody.mp4; fi
  pkill -f "[d]itto_server.py"; sleep 2
  bash $M/maya-ops/lt/ditto_up.sh >> $O/logs/ditto_up.log 2>&1; rc=$?
  say "ditto_up $v rc=$rc: $(tail -1 $O/logs/ditto_up.log | cut -c1-200)"
  [ $rc = 0 ] || { say "FAILED ditto_up $v"; continue; }
  python3 $I/render_intro.py $I/intro_en.wav $O/$out > $O/render$v.json 2>> $O/logs/render.log
  say "render $v rc=$? $(cut -c1-220 $O/render$v.json)"
  curl -s -m 5 127.0.0.1:8031/health > $O/health_$v.json
done
pkill -f "[d]itto_server.py"
say "job2 done"; echo OK > $O/DONE2
wait
