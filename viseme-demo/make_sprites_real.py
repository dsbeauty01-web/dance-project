# VISEME-DEMO v2: cut the 12 mouth sprites from HER REAL RENDERED MOUTH.
# Source: nova-hello.mp4 (81s of her singing/talking, face large and frontal).
# The first sprite set was drawn with code and read as a sticker — this replaces
# it with real pixels: tracked mouth crops, color-matched to the idle_sway face,
# feathered alpha, scaled to the idle loop's mouth. Same filenames as v1 so
# viseme-demo.html needs no change (meta.json anchor w/h updated to 142x105).
#
# Frame picks (at 4fps over the clip) were chosen by eye from a contact sheet:
# each is a clean, near-frontal exemplar of that mouth shape.
import json
import os
import subprocess

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
HELLO = os.path.join(HERE, "..", "nova-hello.mp4")
IDLE_FRAME = os.path.join(HERE, "frame.png")
OUT = os.path.join(HERE, "visemes")

HW, HH = 832, 1104
FPS = 4
REF_CX, REF_CY = 435, 335    # mouth center on the ref frame (t=32.6s)
TW, TH = 150, 110            # track template: mouth+nose
R = 140

# viseme -> harvest frame index (at 4fps); 292 doubles as mbp (closed lips)
PICK = {"rest": 292, "mbp": 292, "small": 284, "E": 156, "I": 271,
        "smile": 170, "O": 126, "U": 194, "A": 127, "wide": 213,
        "L": 231, "fv": 161}

CW, CH = 150, 96             # source crop: MOUTH ONLY — a bigger patch drags the
                             # source clip's nose/chin angle along and warps her face
SCALE = 0.75                 # nova-hello mouth ~130px wide vs idle ~100px

need = sorted(set(PICK.values()))
grab = {}
proc = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-i", HELLO, "-vf", f"fps={FPS}",
     "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
frames = []
i = 0
while True:
    buf = proc.stdout.read(HW * HH * 3)
    if len(buf) < HW * HH * 3:
        break
    frames.append(np.frombuffer(buf, dtype=np.uint8).reshape(HH, HW, 3))
    i += 1
proc.wait()

# track the mouth in each picked frame (same FFT SSD as make_anchor_track.py)
ref = frames[int(32.6 * FPS)].astype(np.float32).mean(2)
tpl = ref[REF_CY - TH // 2:REF_CY + TH // 2, REF_CX - TW // 2:REF_CX + TW // 2]
tpl_e = float((tpl ** 2).sum())
x0, x1 = REF_CX - TW // 2 - R, REF_CX + TW // 2 + R
y0, y1 = REF_CY - TH // 2 - R, REF_CY + TH // 2 + R

def mouth_center(fid):
    g = frames[fid].astype(np.float32).mean(2)
    reg = g[y0:y1, x0:x1]
    rh, rw = reg.shape
    fr = np.fft.rfft2(reg)
    ft = np.fft.rfft2(tpl, s=(rh, rw))
    corr = np.fft.irfft2(fr * np.conj(ft), s=(rh, rw))
    ii = np.pad(np.cumsum(np.cumsum(reg ** 2, 0), 1), ((1, 0), (1, 0)))
    ny, nx = rh - TH + 1, rw - TW + 1
    win = (ii[TH:TH + ny, TW:TW + nx] - ii[0:ny, TW:TW + nx]
           - ii[TH:TH + ny, 0:nx] + ii[0:ny, 0:nx])
    ssd = win - 2 * corr[:ny, :nx] + tpl_e
    dy, dx = np.unravel_index(np.argmin(ssd), ssd.shape)
    return REF_CX + int(dx - R), REF_CY + int(dy - R)

idle = np.asarray(Image.open(IDLE_FRAME).convert("RGB"))
ICX, ICY = 522, 507

def skin_mean(img, cx, cy, r_in=55, r_out=85):
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    px = img[(d > r_in) & (d < r_out)].astype(np.float32)
    m = (px.mean(1) > 90) & (px.mean(1) < 235)
    return px[m].mean(0)

tgt_skin = skin_mean(idle, ICX, ICY)

for name, fid in PICK.items():
    mx, my = mouth_center(fid)
    my += 6                                     # lips sit slightly low in the box
    crop = frames[fid][my - CH // 2:my + CH // 2,
                       mx - CW // 2:mx + CW // 2].astype(np.float32)
    src_skin = skin_mean(frames[fid], mx, my)
    crop = np.clip(crop * (tgt_skin / src_skin)[None, None, :], 0, 255)
    im = Image.fromarray(crop.astype(np.uint8)).resize(
        (int(CW * SCALE), int(CH * SCALE)), Image.LANCZOS)
    w, h = im.size
    yy, xx = np.mgrid[0:h, 0:w]
    nx = (xx - w / 2) / (w / 2)
    ny = (yy - h / 2) / (h / 2)
    d = np.sqrt(nx ** 2 + ny ** 2)
    a = np.clip((1.0 - d) / 0.5, 0, 1)          # small solid center, wide feather
    a = (np.sin(a * np.pi / 2) ** 2 * 255).astype(np.uint8)
    Image.fromarray(np.dstack([np.asarray(im), a]), "RGBA").save(
        os.path.join(OUT, name + ".png"))
    print(name, fid, f"({w}x{h})")

meta = {"anchor": {"cx": ICX, "cy": ICY, "w": int(CW * SCALE), "h": int(CH * SCALE)},
        "video": {"w": 1076, "h": 1924},
        "sprites": sorted(PICK)}
json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=1)
print("meta updated: anchor", meta["anchor"])
