#!/usr/bin/env bash
# lt_boot.sh — Maya on LiveTalking + MuseTalk. One command, hard gates, persisted to the volume.
#   bash lt_boot.sh install     # once per volume: clone LiveTalking, env, MuseTalk weights, SRS build, wiring  (~25 min)
#   bash lt_boot.sh check       # HOUR-ONE GATE: engine up, avatar loaded, local RTMP has video ≥24 fps + real audio (dBFS)
#   bash lt_boot.sh live 15     # Facebook live: push local RTMP → FB rtmps, run maya_lt.py, 60 s recording, report
#   bash lt_boot.sh planted 3   # unattended 3-min test with planted comments (still pushes to FB)
#   bash lt_boot.sh down        # stop everything + THIS pod only (by RUNPOD_POD_ID)
# Rules from the skills baked in: MuseTalk (cuda by default) · rtcpush→SRS→RTMP, never --transport rtmp ·
# ElevenLabs via the TTS module (no /humanaudio hacks) · gestures via custom_config · UDP 8000 + CANDIDATE public IP ·
# measure audio by dBFS, never by frame counters · stop pods by explicit id only.
set -uo pipefail
WS=${WS:-/workspace}; LT=$WS/LiveTalking; SRS=$WS/srs; MO=$WS/maya-ops/lt; LOG=$WS/logs; mkdir -p "$LOG"
ln -sfn $WS/.maya ~/.maya 2>/dev/null || true; [ -f ~/.maya/host.env ] && { set -a; . ~/.maya/host.env; set +a; }
export PYTHONUTF8=1 MAYA_CATALOG=${MAYA_CATALOG:-$MO/serum-c.en.json} MAYA_PERSONA_FILE=${MAYA_PERSONA_FILE:-$MO/persona_maya.md}
AVATAR=${LT_AVATAR:-maya_serum}; PY=${LT_PY:-$WS/ltenv/bin/python}
R=$LOG/lt-report.md
say(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$R"; }
die(){ say "!! $*"; exit 1; }
up(){ if [ -f "$LOG/$1.pid" ] && kill -0 "$(cat "$LOG/$1.pid")" 2>/dev/null; then say "· $1 running"; return; fi
      say "→ start $1"; nohup bash -c "$2" > "$LOG/$1.log" 2>&1 < /dev/null & echo $! > "$LOG/$1.pid"; sleep 1; }
down(){ [ -f "$LOG/$1.pid" ] || return 0; P=$(cat "$LOG/$1.pid"); pkill -TERM -P "$P" 2>/dev/null; kill -TERM "$P" 2>/dev/null; sleep 2; kill -KILL "$P" 2>/dev/null; rm -f "$LOG/$1.pid"; }
wait_http(){ for i in $(seq 1 "${3:-60}"); do curl -s -m3 "$1" >/dev/null 2>&1 && { say "· $2 up"; return 0; }; sleep 3; done; return 1; }
public_ip(){ curl -s -m5 https://api.ipify.org || curl -s -m5 ifconfig.me; }
dbfs(){ ffmpeg -hide_banner -nostats -v info -i "$1" -af volumedetect -f null - 2>&1 | grep -oE 'mean_volume: -?[0-9.]+' | grep -oE '\-?[0-9.]+' ; }

case "${1:-}" in
install)
  say "INSTALL (once per volume)"
  nvidia-smi >/dev/null 2>&1 || die "no GPU"
  [ -d "$LT/.git" ] || git clone https://github.com/lipku/LiveTalking "$LT"
  [ -x "$PY" ] || { python3 -m venv "$WS/ltenv" && "$WS/ltenv/bin/pip" install -U pip; }
  cd "$LT" && "$WS/ltenv/bin/pip" install -r requirements.txt 2>&1 | tail -3
  # torch per README (CUDA 12.x wheel); skip if already importable with cuda
  "$PY" -c "import torch;assert torch.cuda.is_available()" 2>/dev/null || "$WS/ltenv/bin/pip" install torch torchvision --index-url https://download.pytorch.org/whl/cu128 2>&1 | tail -2
  # MuseTalk weights (README: models/ dir); the repo ships a downloader
  [ -f "$LT/models/musetalk/pytorch_model.bin" ] || [ -d "$LT/models/musetalk" ] || { [ -f download_models.sh ] && bash download_models.sh || say "!! download MuseTalk weights per README into $LT/models"; }
  # our avatar bake (LiveTalking layout) — from the volume bake or the backup tgz
  [ -d "$LT/data/avatars/$AVATAR" ] || { for src in $WS/maya-ops/bake/avatars/$AVATAR $WS/LiveTalking-old/data/avatars/$AVATAR ~/maya-bakes-backup/data/avatars/$AVATAR; do [ -d "$src" ] && { mkdir -p "$LT/data/avatars"; cp -r "$src" "$LT/data/avatars/"; break; }; done; }
  [ -d "$LT/data/avatars/$AVATAR" ] || die "avatar $AVATAR not found — restore it from maya-bakes-backup (full_imgs/, latents.pt, coords.pkl, mask/) or re-bake with: $PY -m musetalk.simple_musetalk --avatar_id $AVATAR --file serum_present_src.mp4"
  # gesture assets
  "$PY" "$MO/lt_assets.py" --clips "${CLIPS_DIR:-$WS/maya-ops/bake/gesture_mode}" --out "$LT/data/custom" --config "$LT/data/custom_config.json" || die "assets failed"
  # ElevenLabs TTS module (one factory line)
  cp "$MO/ttsreal_elevenlabs.py" "$LT/"
  if ! grep -q "ElevenLabsTTS" "$LT/ttsreal.py" 2>/dev/null && ! grep -rq "ElevenLabsTTS" "$LT"/*.py 2>/dev/null; then
    FACTORY=$(grep -lE "opt.tts *== *['\"]edgetts['\"]" "$LT"/*.py | head -1)
    if [ -n "$FACTORY" ]; then
      sed -i "0,/opt.tts *== *['\"]edgetts['\"]/s//opt.tts == 'elevenlabs':\n        from ttsreal_elevenlabs import ElevenLabsTTS\n        self.tts = ElevenLabsTTS(opt, self)\n    elif opt.tts == 'edgetts'/" "$FACTORY"
      say "· ElevenLabs TTS wired into $FACTORY"
    else say "!! could not find the TTS factory (opt.tts == 'edgetts') — wire ElevenLabsTTS by hand per ttsreal_elevenlabs.py header"; fi
  fi
  # SRS (rtcpush → RTMP bridge), built once and cached on the volume
  if [ ! -x "$SRS/trunk/objs/srs" ]; then
    git clone -b 5.0release https://github.com/ossrs/srs "$SRS" && cd "$SRS/trunk" && ./configure --ffmpeg-fit=off >/dev/null && make -j"$(nproc)" 2>&1 | tail -2
  fi
  [ -x "$SRS/trunk/objs/srs" ] || die "SRS build failed"
  say "INSTALL DONE — persisted on $WS";;

check|live|planted)
  MODE=$1; MIN=${2:-15}
  nvidia-smi >/dev/null 2>&1 || die "no GPU"
  IP=$(public_ip); [ -n "$IP" ] || die "no public IP"; export CANDIDATE=$IP
  cat > "$SRS/trunk/conf/maya_rtc2rtmp.conf" << EOF
listen 1935; max_connections 100; daemon off; srs_log_tank console;
http_server { enabled on; listen 8080; dir ./objs/nginx/html; }
http_api { enabled on; listen 1985; }
rtc_server { enabled on; listen 8000; candidate $IP; }
vhost __defaultVhost__ { rtc { enabled on; rtmp_to_rtc off; rtc_to_rtmp on; } http_remux { enabled on; mount [vhost]/[app]/[stream].flv; } }
EOF
  down srs; up srs "cd $SRS/trunk && ./objs/srs -c conf/maya_rtc2rtmp.conf"; wait_http http://127.0.0.1:1985/api/v1/versions SRS 20 || die "SRS not up"
  down engine
  up engine "cd $LT && $PY app.py --transport rtcpush --push_url 'http://127.0.0.1:1985/rtc/v1/whip/?app=live&stream=livestream' --model musetalk --avatar_id $AVATAR --customvideo_config data/custom_config.json --tts ${LT_TTS:-openaitts} --REF_FILE ${LT_REF_FILE:-coral} --listenport 8010 ${LT_EXTRA_ARGS:-}"
  wait_http http://127.0.0.1:8010/ engine 120 || { tail -30 "$LOG/engine.log"; die "engine not up"; }
  sleep 8
  # ---- HOUR-ONE GATE ----
  say "GATE: local RTMP must carry video >=24 fps and real audio"
  curl -s -X POST http://127.0.0.1:8010/set_audiotype -H 'Content-Type: application/json' -d '{"sessionid":0,"audiotype":1,"reinit":true}' >/dev/null
  curl -s -X POST http://127.0.0.1:8010/human -H 'Content-Type: application/json' -d '{"sessionid":0,"text":"Voice and video check. One, two, three. This is Maya, live on LiveTalking.","type":"echo","interrupt":true}' >/dev/null
  sleep 2; timeout 20 ffmpeg -y -v error -i rtmp://127.0.0.1/live/livestream -t 8 -c copy "$LOG/gate.flv" || die "cannot pull rtmp://127.0.0.1/live/livestream — rtcpush/SRS bridge not flowing (check CANDIDATE=$IP, UDP 8000 open, engine.log)"
  FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=avg_frame_rate -of csv=p=0 "$LOG/gate.flv" | awk -F/ '{printf "%.1f", $1/($2?$2:1)}')
  LVL=$(dbfs "$LOG/gate.flv"); LVL=${LVL:--99}
  say "· local RTMP: fps=$FPS  audio mean=${LVL} dBFS  (need fps>=24, dBFS>-40)"
  ENGFPS=$(grep -oiE "(infer|final)[ _]?fps[^0-9]*[0-9.]+" "$LOG/engine.log" | tail -2 | tr '\n' ' '); say "· engine log: ${ENGFPS:-no fps line yet}"
  awk -v f="$FPS" 'BEGIN{exit !(f>=24)}' || die "video below 24 fps — lower --batch_size / check GPU util (nvidia-smi)"
  awk -v l="$LVL" 'BEGIN{exit !(l>-40)}' || die "audio silent (${LVL} dBFS) — TTS module not producing: check OPENAI_API_KEY (voice is openaitts/coral) and engine.log"
  say "GATE PASSED — she renders and speaks on the local RTMP"
  [ "$MODE" = "check" ] && { say "check complete (no Facebook). Next: bash lt_boot.sh live 15"; exit 0; }
  # ---- FACEBOOK ----
  "$PY" "$MO/fb_tool.py" live create | tee -a "$R" | grep -E "permalink|VIDEO id|rtmp:" >/dev/null
  RT=$(grep -oE '^rtmp: .*' "$R" | tail -1 | cut -d' ' -f2); [ -n "$RT" ] || die "no FB rtmp url"
  "$PY" "$MO/fb_tool.py" live current >/dev/null; set -a; . ~/.maya/host.env; set +a
  down push; up push "ffmpeg -hide_banner -loglevel warning -re -i rtmp://127.0.0.1/live/livestream -c copy -f flv '$RT'"
  sleep 6; say "!! Facebook Live Producer → Settings → Stream latency → LOW !!"; say "PERMALINK: $(grep -oE 'https://www.facebook.com[^ ]*' "$R" | tail -1)"
  ( sleep 40; ffmpeg -y -v error -i rtmp://127.0.0.1/live/livestream -t 60 -c copy "$LOG/lt_60s.flv" ) &
  if [ "$MODE" = "planted" ]; then "$PY" "$MO/maya_lt.py" --minutes "$MIN" --planted "$MO/planted.json" 2>&1 | tee "$LOG/host.log" | grep -E "SPEAK|ANSWER|SUMMARY|BLOCKED|error"
  else "$PY" "$MO/maya_lt.py" --minutes "$MIN" 2>&1 | tee "$LOG/host.log" | grep -E "SPEAK|ANSWER|SUMMARY|BLOCKED|error"; fi
  { echo; echo "## lt_boot $(date -Is) mode=$MODE"; echo "- gate: fps=$FPS dBFS=$LVL"; echo "- summary: $(cat $MO/last_session_lt.json 2>/dev/null)";
    echo "- recording: $LOG/lt_60s.flv mean $(dbfs $LOG/lt_60s.flv 2>/dev/null || echo n/a) dBFS"; } >> "$R"
  cp "$R" $WS/lt-report.md; cat $WS/lt-report.md; bash "$0" down;;

down)
  down push; down engine; down srs
  LV=$(grep -oE '^FB_LIVE_VIDEO_ID=.*' ~/.maya/host.env 2>/dev/null | cut -d= -f2); [ -n "${LV:-}" ] && "$PY" "$MO/fb_tool.py" live end "$LV" >/dev/null 2>&1
  [ -n "${RUNPOD_API_KEY:-}" ] && [ -n "${RUNPOD_POD_ID:-}" ] && curl -s -X POST -H "Authorization: Bearer $RUNPOD_API_KEY" "https://rest.runpod.io/v1/pods/$RUNPOD_POD_ID/stop" >/dev/null && say "pod $RUNPOD_POD_ID stop requested (by id only)"
  say "DOWN";;
*) echo "usage: lt_boot.sh install | check | live N | planted N | down";;
esac
