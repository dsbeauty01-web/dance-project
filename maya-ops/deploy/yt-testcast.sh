#!/bin/bash
# YT TESTCAST — prove the YouTube ingest pipe from the pod, no OBS needed.
# Streams Maya's baked clips (idle + gestures, shuffled playlist feel) with silent audio
# to the channel's persistent stream key. YouTube Studio then shows the preview;
# the founder clicks GO LIVE there. Runs in tmux(ytcast); kill the session to stop.
#
# Usage (on the pod):  RTMP_URL=rtmp://a.rtmp.youtube.com/live2/<key> bash yt-testcast.sh
set -euo pipefail
: "${RTMP_URL:?set RTMP_URL}"
G=/workspace/maya-ops/gestures
LIST=/tmp/ytcast-list.txt
# idle-heavy rotation so she mostly stands naturally, with a gesture every ~30s
cat > "$LIST" << EOF
file '$G/idle_maya.mp4'
file '$G/idle_maya.mp4'
file '$G/leftwave_maya.mp4'
file '$G/idle_maya.mp4'
file '$G/maya_left_talk_point.mp4'
file '$G/idle_maya.mp4'
file '$G/maya_bothhand.mp4'
file '$G/idle_maya.mp4'
file '$G/mayahead_nudge.mp4'
EOF
exec ffmpeg -hide_banner -loglevel warning \
  -stream_loop -1 -f concat -safe 0 -re -i "$LIST" \
  -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 \
  -map 0:v:0 -map 1:a:0 \
  -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='AI · Maya — test broadcast':fontcolor=white@0.85:fontsize=34:box=1:boxcolor=black@0.35:boxborderw=12:x=(w-text_w)/2:y=44" \
  -r 25 -c:v libx264 -preset veryfast -b:v 4500k -maxrate 4500k -bufsize 9000k \
  -pix_fmt yuv420p -g 50 -c:a aac -b:a 128k -ar 44100 \
  -f flv "$RTMP_URL"
