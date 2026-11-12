#!/usr/bin/env bash
# take8_body.sh -- the take-8 BODY treatment, CPU only: native resolution (no rescale), light luma
# unsharp 5:5:0.7, crf 12, 25 fps, no audio. Source: maya-lt assets/lead_seyzar/seyzar_bank8s.json
# ("native 1284x1608 (no 860 downscale) + unsharp 5:5:0.7 luma; face sharpness 146 vs 74").
#   bash take8_body.sh IN.mp4 OUT.mp4
# It never writes over IN and never deletes anything (bakes are treasure). The result is a CANDIDATE:
# it still has to go through prebake_gate.py and the Bake Factory before any page uses it.
set -euo pipefail
IN=${1:?in.mp4}; OUT=${2:?out.mp4}
[ "$IN" != "$OUT" ] || { echo "REFUSING: output would overwrite the source"; exit 2; }
[ ! -e "$OUT" ] || { echo "REFUSING: $OUT exists (never overwrite a body)"; exit 2; }
ffmpeg -v error -i "$IN" -vf "unsharp=5:5:0.7:5:5:0.0,format=yuv420p" -c:v libx264 -preset slow -crf 12 -g 50 -r 25 -an "$OUT"
a=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height,nb_frames -of csv=p=0 "$IN")
b=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height,nb_frames -of csv=p=0 "$OUT")
echo "in  $a"; echo "out $b"
[ "$a" = "$b" ] || { echo "FAIL: size or frame count changed"; exit 3; }
echo "OK -- now gate it: python3 prebake_gate.py $OUT --face face_landmarker.task   (must be PASS or SOFTEN)"
