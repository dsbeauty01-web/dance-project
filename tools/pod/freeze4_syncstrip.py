#!/usr/bin/env python3
"""tools/pod/freeze4_syncstrip.py <recording.mp4> <t0> <t1> <x,y,w,h> <out.jpg> — the face tile, frame by frame, with the
recording's own sound level under each frame (green bar). For judging by eye whether her mouth starts with her voice.
The recording is the screen + the sound Chrome actually played (x11grab + PulseAudio), so this is what a viewer got."""
import subprocess, sys, wave, os, tempfile
import numpy as np, cv2

src, t0, t1, box, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), [int(v) for v in sys.argv[4].split(",")], sys.argv[5]
x, y, w, h = box
tmp = tempfile.mkdtemp()
wav = os.path.join(tmp, "a.wav")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(t0), "-t", str(t1 - t0), "-i", src, "-ac", "1", "-ar", "16000", wav], check=True)
with wave.open(wav) as f: a = np.frombuffer(f.readframes(f.getnframes()), np.int16).astype(np.float32) / 32768
cap = cv2.VideoCapture(src); fps = cap.get(cv2.CAP_PROP_FPS) or 25
cap.set(cv2.CAP_PROP_POS_MSEC, t0 * 1000)
tiles = []
n = int((t1 - t0) * fps)
for i in range(n):
    ok, fr = cap.read()
    if not ok: break
    t = t0 + i / fps
    c = cv2.resize(fr[y:y + h, x:x + w], (150, int(150 * h / w)))
    seg = a[int(i / fps * 16000):int((i + 1) / fps * 16000)]
    lvl = float(np.sqrt(np.mean(seg * seg))) if len(seg) else 0
    bar = np.full((26, 150, 3), 30, np.uint8)
    cv2.rectangle(bar, (0, 14), (int(min(150, lvl * 1500)), 26), (90, 220, 120), -1)
    cv2.putText(bar, f"{t:.2f}s", (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1)
    tiles.append(np.vstack([c, bar]))
cols = 10
rows = [np.hstack(tiles[r:r + cols] + [np.zeros_like(tiles[0])] * (cols - len(tiles[r:r + cols]))) for r in range(0, len(tiles), cols)]
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88]); print(out, len(tiles), "frames")
