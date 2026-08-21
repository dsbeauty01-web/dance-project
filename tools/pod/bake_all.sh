#!/usr/bin/env bash
# tools/pod/bake_all.sh — executes the BAKE-ALL master plan (2026-08-15), exact windows.
# One bake at a time, sequential. Each: trim -> verify dur -> bake -> quota-guard -> copy
# -> bake_verify (PASS register / FAIL .BROKEN). On face-seg crash: shrink 1s each side,
# retry ONCE, then log FAIL and continue. Silence = processing (LAW: no kills).
set -u
LOG=/workspace/logs/bake-all.log
mkdir -p /workspace/logs /root/av_local /root/cuts /root/tmp
exec >>"$LOG" 2>&1
export PYTHONPATH=/workspace/_sys/pylibs311_good/dist-packages:${PYTHONPATH:-}
export TMPDIR=/root/tmp
cd /workspace/LiveTalking
AV=/workspace/LiveTalking/data/avatars
TOOLS=/workspace/tools
echo "$(date -u) ========== BAKE-ALL START =========="

# id  src  start  end
JOBS=(
  "fullwave10sec|handywave-full.mp4|5.6|58.0"
  "nova_hello_a|nova-hello.mp4|27.3|67.4"
  "nova_hello_b|nova-hello.mp4|68.3|80.0"
  "nova_prewave_a|pre-wave.mp4|0.3|33.4"
  "shoulderright-left10sec|pre-wave.mp4|61.3|75.0"
  "nova_prewave_c|pre-wave.mp4|45.0|54.7"
)

trim(){ # src start end out
  local dur; dur=$(python3 -c "print(round($3-$2,3))")
  ffmpeg -y -ss "$2" -i "/workspace/sources/$1" -t "$dur" -c:v libx264 -crf 18 -an -pix_fmt yuv420p -r 30 "$4" >/dev/null 2>&1
  ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$4" 2>/dev/null
}

bake_one(){ # id cut
  rm -rf "/root/av_local/$1"
  python -m avatars.musetalk.genavatar --file "$2" --avatar_id "$1" --save_path /root/av_local >"/workspace/logs/bake_$1.log" 2>&1
  [ -f "/root/av_local/$1/latents.pt" ] && [ -s "/root/av_local/$1/latents.pt" ]
}

for job in "${JOBS[@]}"; do
  IFS='|' read -r id src start end <<< "$job"
  echo "$(date -u) ----- $id  ($src  $start..$end) -----"
  # RESUME: skip if this avatar already exists valid on the volume (survived a prior run)
  ex="$AV/$id"
  if [ -s "$ex/latents.pt" ]; then
    exsz=$(stat -c%s "$ex/latents.pt"); exfi=$(ls "$ex/full_imgs" 2>/dev/null|wc -l); exmk=$(ls "$ex/mask" 2>/dev/null|wc -l)
    if [ "$exsz" -gt 1048576 ] && [ "$exfi" = "$exmk" ] && [ "$exfi" -gt 10 ]; then
      echo "$(date -u) SKIP $id — already valid (frames=$exfi latents=$((exsz/1024))KB)"; continue
    fi
  fi
  cut="/root/cuts/$id.mp4"
  want=$(python3 -c "print(round($end-$start,3))")
  got=$(trim "$src" "$start" "$end" "$cut")
  diff=$(python3 -c "print(abs($got-$want)<=0.2)" 2>/dev/null)
  if [ "$diff" != "True" ]; then echo "$(date -u) TRIM-BAD $id want=${want}s got=${got}s — SKIP"; continue; fi
  echo "$(date -u) trim ok ${got}s"

  ok=0
  if bake_one "$id" "$cut"; then ok=1
  else
    # face-seg crash path: shrink 1s each side, retry ONCE
    s2=$(python3 -c "print(round($start+1,3))"); e2=$(python3 -c "print(round($end-1,3))")
    echo "$(date -u) bake failed — shrink retry $s2..$e2 (once)"
    trim "$src" "$s2" "$e2" "$cut" >/dev/null
    bake_one "$id" "$cut" && ok=1
  fi
  if [ "$ok" != "1" ]; then echo "$(date -u) FAIL $id — bake produced no valid latents (after 1 retry)"; continue; fi

  # quota guard before the volume copy
  payload=$(du -sb "/root/av_local/$id" | cut -f1)
  if ! bash "$TOOLS/quota_guard.sh" "$payload" /workspace >/tmp/qg.out 2>&1; then
    cat /tmp/qg.out; echo "$(date -u) QUOTA-STOP at $id — aborting BAKE-ALL"; break
  fi
  rm -rf "$AV/$id"; cp -r "/root/av_local/$id" "$AV/$id"; sync

  # validator gate
  vout=$(bash "$TOOLS/bake_verify.sh" "$id" "$AV" 2>&1 | tail -1)
  echo "$(date -u) $vout"
done
echo "$(date -u) ========== BAKE-ALL DONE =========="
echo "REGISTERED:"; python3 -c "import json;d=json.load(open('$AV/verified-avatars.json'));print(' '.join(sorted(k for k in d if any(x in k for x in ['wave','hello','prewave']))))" 2>/dev/null
