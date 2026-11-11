#!/usr/bin/env python3
"""tools/pod/freeze4_sheet.py <results dir> <out.jpg> — one contact sheet of a FREEZE v4 pod run:
panel big (talking) · panel small (dancing) · freeze hold · red banner (no face) · red panel (stream lost) · the face up close."""
import os, sys
from PIL import Image, ImageDraw, ImageFont

d, out = sys.argv[1], sys.argv[2]
cells = [("A-1-talking-panel-big.png", "Talking: SoulX face panel BIG"), ("A-2-dance-panel-small.png", "Dancing: panel small, Watching"),
         ("A-3-freeze-hold.png", "Freeze hold: badge FREEZE!"), ("A-4-talking-in-game.png", "Talking in the game"),
         ("B-red-banner-no-face.png", "No face stream: red banner, no game"), ("C-face-stream-lost.png", "Stream lost mid-game: panel red")]
W, H, L = 640, 360, 30
try: font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
except Exception: font = ImageFont.load_default()
sheet = Image.new("RGB", (W * 2, (H + L) * 3 + H // 1), (20, 11, 38))
dr = ImageDraw.Draw(sheet)
for i, (f, cap) in enumerate(cells):
    x, y = (i % 2) * W, (i // 2) * (H + L)
    p = os.path.join(d, f)
    if os.path.exists(p): sheet.paste(Image.open(p).convert("RGB").resize((W, H)), (x, y + L))
    else: dr.text((x + 20, y + L + 150), "MISSING: " + f, fill=(255, 180, 180), font=font)
    dr.text((x + 10, y + 4), cap, fill=(255, 214, 90), font=font)
y = 3 * (H + L)
faces = [os.path.join(d, f) for f in ("A-face-received-1.png", "A-face-received-2.png", "A-face-received-3.png") if os.path.exists(os.path.join(d, f))]
pubs = sorted(os.path.join(d, "face", f) for f in os.listdir(os.path.join(d, "face")) if f.startswith("published_speech")) if os.path.isdir(os.path.join(d, "face")) else []
row = [(p, "received in browser") for p in faces[:2]] + [(p, "published by pod") for p in pubs[:3]]
for j, (p, cap) in enumerate(row[:5]):
    im = Image.open(p).convert("RGB").resize((240, 240)); sheet.paste(im, (j * 256 + 8, y + 40))
    dr.text((j * 256 + 8, y + 12), cap, fill=(215, 205, 240), font=font)
sheet.save(out, quality=88); print(out, sheet.size)
