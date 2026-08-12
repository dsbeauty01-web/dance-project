# VISEME-DEMO: track the mouth across the idle loop -> anchor-track.json.
# The body loop sways; a static overlay floats off her lips. This measures the
# mouth's (dx,dy) per frame vs frame 1 (FFT SSD template match, pure numpy) so
# the page can glue the sprite to her face. Output: {"fps", "frames": [[dx,dy]..]}.
import json
import os
import subprocess

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.join(HERE, "..", "freezegame", "idle_sway.mp4")
VW, VH = 1076, 1924
CX, CY = 522, 507          # mouth anchor measured on frame 1 (see make_sprites.py)
TW, TH = 180, 120          # template: mouth + nose area (distinctive, rigid)
R = 120                    # search radius in px (her sway peaks past 80)

proc = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-i", VIDEO, "-f", "rawvideo", "-pix_fmt", "gray", "-"],
    stdout=subprocess.PIPE)

def read_frame():
    buf = proc.stdout.read(VW * VH)
    if len(buf) < VW * VH:
        return None
    return np.frombuffer(buf, dtype=np.uint8).reshape(VH, VW).astype(np.float32)

# search region around the anchor, big enough for template + radius
x0, x1 = CX - TW // 2 - R, CX + TW // 2 + R
y0, y1 = CY - TH // 2 - R, CY + TH // 2 + R

first = read_frame()
tpl = first[CY - TH // 2:CY + TH // 2, CX - TW // 2:CX + TW // 2]
tpl_energy = float((tpl ** 2).sum())

def track(frame):
    """min-SSD offset of tpl inside the search region, via FFT correlation."""
    reg = frame[y0:y1, x0:x1]
    rh, rw = reg.shape
    fr = np.fft.rfft2(reg)
    ft = np.fft.rfft2(tpl, s=(rh, rw))
    corr = np.fft.irfft2(fr * np.conj(ft), s=(rh, rw))   # corr[dy,dx] = sum reg[dy:,dx:]*tpl
    # local energy of each window via integral image
    ii = np.cumsum(np.cumsum(reg ** 2, 0), 1)
    ii = np.pad(ii, ((1, 0), (1, 0)))
    ny, nx = rh - TH + 1, rw - TW + 1
    win = ii[TH:TH + ny, TW:TW + nx] - ii[0:ny, TW:TW + nx] - ii[TH:TH + ny, 0:nx] + ii[0:ny, 0:nx]
    ssd = win - 2 * corr[:ny, :nx] + tpl_energy
    dy, dx = np.unravel_index(np.argmin(ssd), ssd.shape)
    return int(dx - R), int(dy - R)

offsets = [(0, 0)]
while True:
    f = read_frame()
    if f is None:
        break
    offsets.append(track(f))
proc.wait()

# light smoothing (3-frame moving average) so the mouth doesn't jitter
arr = np.array(offsets, dtype=np.float32)
sm = arr.copy()
sm[1:-1] = (arr[:-2] + arr[1:-1] + arr[2:]) / 3.0
frames = [[round(float(dx), 1), round(float(dy), 1)] for dx, dy in sm]

fps_out = subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
     "stream=r_frame_rate", "-of", "csv=p=0", VIDEO],
    capture_output=True, text=True).stdout.strip()
num, den = fps_out.split("/")
fps = float(num) / float(den)

json.dump({"fps": fps, "frames": frames},
          open(os.path.join(HERE, "anchor-track.json"), "w"))
mags = [abs(a) for f in frames for a in f]
print(f"{len(frames)} frames @ {fps} fps, max |offset| = {max(mags)} px")
