#!/usr/bin/env bash
# recon.sh -- READ-ONLY look at the mounted Nova volume. Nothing is written to, moved or deleted
# outside /workspace/novaditto_fb_out. Credential VALUES are never printed: only whether a name
# is present, and how long the value is.
set -uo pipefail
O=/workspace/novaditto_fb_out; mkdir -p "$O"
say(){ echo "[recon $(date -u +%H:%M:%S)] $*"; }

say "volume top level"
ls -la /workspace 2>&1 | head -60
say "df"
df -h /workspace /root 2>&1

say "the files the live stack needs"
for f in lk_bridge.py boot.sh rt_lk.py app.py boot-nova.sh deploy_from_git.sh; do
  if [ -e "/workspace/$f" ]; then echo "  PRESENT /workspace/$f $(stat -c %s "/workspace/$f") bytes  md5=$(md5sum "/workspace/$f" | cut -d' ' -f1)"
  else echo "  ABSENT  /workspace/$f"; fi
done
say "anything named lk_bridge or boot anywhere on the volume (2 levels)"
find /workspace -maxdepth 2 \( -name 'lk_bridge*.py' -o -name 'boot*.sh' -o -name '*.env' -o -name '.env' \) 2>/dev/null | head -30

# --- credentials: PRESENCE ONLY, never the value ---
say "live credentials referenced on the volume (names + value length only, never the value)"
python3 - <<'PY' 2>&1
import os, re
names = ["OPENAI_API_KEY", "LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"]
cands = [p for p in ("/workspace/boot.sh", "/workspace/.env", "/workspace/boot-nova.sh", "/workspace/env.sh") if os.path.exists(p)]
print("  scanned:", cands or "(none of the usual files exist)")
for p in cands:
    try: txt = open(p, "r", errors="replace").read()
    except Exception as e: print(f"  {p}: unreadable {e}"); continue
    for n in names:
        m = re.search(rf'{n}\s*=\s*["\']?([^"\'\s]*)', txt)
        print(f"  {os.path.basename(p)}: {n} = {'PRESENT, len ' + str(len(m.group(1))) if m and m.group(1) else ('PRESENT BUT EMPTY' if m else 'absent')}")
print("  (values are never printed)")
PY

say "is a Nova python env already on the volume?"
ls -d /workspace/venv /workspace/env /workspace/*/venv 2>/dev/null | head
python3 -c "import sys; print('  container python', sys.version.split()[0])"

say "pages / bakes present?"
ls /workspace/gallery 2>/dev/null | head -10
ls /workspace/_repo 2>/dev/null | head -10

# --- instruction #2: the probe, read-only ---
say "=== ditto_bridge_patch.py --probe on the REAL volume file ==="
if [ -e /workspace/lk_bridge.py ]; then
  python3 /workspace/in/ditto_bridge_patch.py --probe 2>&1 | tee "$O/probe.txt"
  echo "probe exit=$?" | tee -a "$O/probe.txt"
  # keep a copy of the real bridge so the anchors can be compared off-pod if they do not match
  cp /workspace/lk_bridge.py "$O/lk_bridge.real.py" 2>/dev/null && say "copied lk_bridge.py to the out dir for off-pod inspection"
else
  echo "NO /workspace/lk_bridge.py -- the live bridge is not on this volume" | tee "$O/probe.txt"
fi
say "recon done"
