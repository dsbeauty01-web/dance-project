#!/bin/bash
# job4 stage 10, run by hand: leave the production volume as found
PG=/workspace/pages/beta/freeze.html; O=/root/out/live
for pat in "[r]t_lk.py" "[l]k_bridge.py" "[b]oot_novaditto.sh" "[a]pp.py" "[d]itto_server.py"; do pkill -f "$pat"; done; sleep 2
python3 -I /root/in/ditto_bridge_patch.py --revert --wd $O > $O/revert.txt 2>&1; echo "revert rc=$? $(grep -E 'REVERTED|no .bak' $O/revert.txt | head -1)"
rm -f /workspace/lk_bridge.py.bak-ditto-* /workspace/nova_ditto.py
if [ -s /root/freeze.html.orig ]; then cp /root/freeze.html.orig "$PG.t8-restore" && mv "$PG.t8-restore" "$PG"; fi
md5sum /workspace/lk_bridge.py /workspace/rt_lk.py "$PG"
ls /workspace/nova_ditto.py /workspace/lk_bridge.py.bak-ditto-* 2>&1 | head -3
