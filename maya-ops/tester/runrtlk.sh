#!/bin/bash
# clean rt_lk launcher for a fresh pod — sets the same env boot.sh uses, then runs the brain.
cd /workspace
eval "$(grep -E '^export [A-Z_]+=' /workspace/boot.sh)"
echo "LAUNCHER START $(date -u); python=$(command -v python); PYTHONPATH=${PYTHONPATH:0:50}"
exec python -u rt_lk.py
