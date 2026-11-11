#!/bin/bash
# stand-in child for take 1: GO, then three typed lines, then STOP. Lines go to the page's own chat box.
cd /dev/shm/t8; mkdir -p kid
echo "I'm Sam!" > kid/kid_001.txt
echo "a dolphin! they jump so high" > kid/kid_002.txt
echo "can we dance now?" > kid/kid_003.txt
echo go > kid/GO; echo stop > kid/STOP
python3 pod.py put kid/GO GO; t0=$(date +%s)
w(){ while [ $(( $(date +%s) - t0 )) -lt $1 ]; do sleep 1; done; }
w 16; python3 pod.py put kid/kid_001.txt kid_001.txt
w 36; python3 pod.py put kid/kid_002.txt kid_002.txt
w 58; python3 pod.py put kid/kid_003.txt kid_003.txt
w 82; python3 pod.py put kid/STOP STOP
echo "driver done at +$(( $(date +%s) - t0 ))s"
