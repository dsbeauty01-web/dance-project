#!/bin/bash
# take 3: the SAME live stack, Ditto server swapped to Nova's older one (from_maya: 514 ms/chunk live on
# 2026-11-02), body_t8 kept, live_trio_nova settings. The timeline sidecar in the bridge is untouched.
set -u
O=/root/out/live3; mkdir -p $O /root/rec3 /root/m2/maya-ops/lt /root/m2/bench/replace_musetalk_alt
cp /root/in/old_ditto_server.py /root/m2/maya-ops/lt/ditto_server.py
cp /root/in/old_motion_bank.py /root/m2/maya-ops/lt/motion_bank.py
cp /root/in/old_ditto_wide.py /root/m2/bench/replace_musetalk_alt/ditto_wide.py
cp /root/m/maya-ops/lt/ditto_up.sh /root/m2/maya-ops/lt/ditto_up.sh
pkill -f "[d]itto_server.py"; sleep 2
( env -i PATH=$PATH HOME=/root DITTO_ROOT=/root/ditto MAYA_LOGS=$O DITTO_PORT=8031 DITTO_SRC=/root/in/body_t8.mp4 \
    DITTO_AMP=0.6 DITTO_CHUNK=25 DITTO_PRIME=35 DITTO_VAD=1 DITTO_THREADS=6 DITTO_EYE_HOLD=1 DITTO_WAIT_SEC=600 \
    bash /root/m2/maya-ops/lt/ditto_up.sh ) > $O/ditto_up.log 2>&1
echo "ditto_up rc=$? $(tail -1 $O/ditto_up.log | cut -c1-200)"
rm -f /root/in/kid_*.txt /root/in/STOP
for i in $(seq 1 120); do [ -e /root/in/GO3 ] && break; sleep 2; done
echo "GO3 $(date -u +%T)"
env -u PYTHONPATH python3 /root/in/real_harness.py --out $O --inbox /root/in --rec-dir /root/rec3 --max-s 100 \
   --url "http://127.0.0.1:8765/beta/freeze?commercial=1" > $O/harness.log 2>&1
echo "harness rc=$? $(tail -1 $O/harness.log)"
cp /workspace/gallery/wd/ditto_stats.json $O/ditto_stats.take3.json 2>/dev/null
cp /workspace/gallery/wd/ditto.log $O/ditto_sidecar.take3.log 2>/dev/null
curl -s -m 5 127.0.0.1:8031/health > $O/health_end.json
echo READY > $O/TAKE3_READY
