# track-harness — self-test the pose-tracking cues without a real camera

Runs a game page in headless Chrome with a recorded video as a FAKE webcam,
forces each cue, and screenshots the overlay so the tracking can be checked
(glow position / visibility / arrows) without anyone in front of a camera.

## Setup (once)
    cd tools
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm i playwright-core   # uses installed Chrome

## Make a fake-camera clip (Y4M) — a person/figure for MoveNet to track
FFMPEG at: .../WinGet/Packages/Gyan.FFmpeg_*/ffmpeg-*/bin/ffmpeg
    ffmpeg -y -ss 5 -t 8 -i ../nova-joined-small.mp4 \
      -vf "crop=320:430:200:120,scale=640:480,fps=15,format=yuv420p" \
      -pix_fmt yuv420p fakecam.y4m

## Run (writes shot_<game>_<cue>.png next to the script)
    node track-harness.js nova-wave.html shoulder-roll,wrist-wave,elbow-pump,free
    node track-harness.js nova-join.html head-left,shoulder-left,hips-left,free

Each cue prints the computed aura {x,y,size,arrow}. A real-person clip tracks
far better than the cartoon (cartoon limbs drop out on some frames).
