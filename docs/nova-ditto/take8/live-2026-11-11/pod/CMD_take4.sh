#!/bin/bash
# take 4: take-8 server + nova_take8.env + body_t8, but Ditto renders at 720x1280 (DITTO_OUT_W/H), the size the
# bridge publishes anyway. job4 is stopped first so it cannot revert the bridge mid-take; CMD_restore puts the
# volume back afterwards (same three steps as job4's stage 10).
set -u
pkill -f "[j]ob4.sh"; echo "job4 stopped (restore is CMD_restore)"
O=/root/out/live4; mkdir -p $O /root/rec4
pkill -f "[d]itto_server.py"; sleep 2
( set -a; . /root/in/nova_take8.env; set +a; unset DITTO_PACK MAYA_ASSETS_TOKEN
  export DITTO_ROOT=/root/ditto MAYA_LOGS=$O DITTO_PORT=8031 DITTO_SRC=/root/in/body_t8.mp4 DITTO_OUT_W=720 DITTO_OUT_H=1280
  bash /root/m/maya-ops/lt/ditto_up.sh ) > $O/ditto_up.log 2>&1
echo "ditto_up rc=$? $(tail -1 $O/ditto_up.log | cut -c1-160)"
rm -f /root/in/kid_*.txt /root/in/STOP
for i in $(seq 1 120); do [ -e /root/in/GO4 ] && break; sleep 2; done
echo "GO4 $(date -u +%T)"
cp /workspace/gallery/wd/ditto_stats.json $O/ditto_stats.before.json 2>/dev/null
env -u PYTHONPATH python3 /root/in/real_harness.py --out $O --inbox /root/in --rec-dir /root/rec4 --max-s 100 \
   --url "http://127.0.0.1:8765/beta/freeze?commercial=1" > $O/harness.log 2>&1
echo "harness rc=$? $(tail -1 $O/harness.log)"
cp /workspace/gallery/wd/ditto_stats.json $O/ditto_stats.take4.json 2>/dev/null
curl -s -m 5 127.0.0.1:8031/health > $O/health_end.json
