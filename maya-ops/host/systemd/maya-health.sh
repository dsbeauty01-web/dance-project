#!/usr/bin/env bash
# every 60s: if any service is dead or a heartbeat is stale, restart it and log.
set -u
LOG=/workspace/maya-ops/health.log
for s in maya-render maya-stream maya-router maya-host maya-push; do
  systemctl is-active --quiet $s || { echo "$(date -Is) RESTART $s (inactive)" >> $LOG; systemctl restart $s; }
done
H=$(curl -s --max-time 5 http://127.0.0.1:8787/health || echo '{}')
python3 - "$H" << 'PY' >> $LOG
import json,sys,time
j=json.loads(sys.argv[1] or '{}'); ages=j.get('beats_age_sec',{})
bad=[k for k,v in ages.items() if v>90]
print(time.strftime('%FT%T'), 'OK' if not bad and j.get('ok') else f'STALE {bad}', 'cost', j.get('cost',{}).get('llm_usd'))
PY
