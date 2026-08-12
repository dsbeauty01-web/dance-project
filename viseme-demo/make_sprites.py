# VISEME-DEMO: draw 12 mouth sprites color-matched to Nova's face.
# Anchor (measured from frame.png, video 1076x1924): mouth center ~(522, 507).
# Sprite canvas: 120x80 px centered on the mouth (drawn at 4x and downscaled
# for smooth edges). Colors sampled from the frame around her real mouth.
import json
import os

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FRAME = os.path.join(HERE, "frame.png")
OUT = os.path.join(HERE, "visemes")
os.makedirs(OUT, exist_ok=True)

img = Image.open(FRAME).convert("RGB")

# sample her real colors
skin = img.getpixel((500, 470))          # cheek near mouth
lip = img.getpixel((522, 512))           # lip line
lip_dark = tuple(max(0, c - 45) for c in lip)
mouth_in = (94, 38, 48)                  # inner mouth (warm dark)
teeth = (250, 246, 240)
tongue = (196, 92, 100)

W, H = 120, 80                            # sprite size in video px
S = 4                                     # supersample
CX, CY = W * S // 2, H * S // 2


def canvas():
    return Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))


def save(im, name):
    im = im.filter(ImageFilter.GaussianBlur(S * 0.6))
    im = im.resize((W, H), Image.LANCZOS)
    im.save(os.path.join(OUT, name + ".png"))


def lips_around(d, w, h, open_h=0):
    """upper+lower lip outline around an opening of w x open_h."""
    # lower lip fullness
    d.ellipse([CX - w // 2 - 8, CY - h // 2 - 6, CX + w // 2 + 8, CY + h // 2 + 10],
              fill=lip)


def draw_closed(smile=0.0):
    im = canvas(); d = ImageDraw.Draw(im)
    w = int(150 + 30 * smile)
    # subtle lip base
    d.ellipse([CX - w, CY - 26, CX + w, CY + 34], fill=lip)
    # smile line
    d.arc([CX - w + 10, CY - 40 - int(26 * smile), CX + w - 10, CY + 30 + int(10 * smile)],
          start=20, end=160, fill=lip_dark, width=S * 3)
    return im


def draw_open(w, h, teeth_top=True, tongue_v=False, round_lips=False):
    im = canvas(); d = ImageDraw.Draw(im)
    lw = w + 60
    d.ellipse([CX - lw, CY - h - 26, CX + lw, CY + h + 30], fill=lip)      # lips
    d.ellipse([CX - w, CY - h, CX + w, CY + h], fill=mouth_in)             # opening
    if teeth_top:
        d.rectangle([CX - w + 8, CY - h + 2, CX + w - 8, CY - h + 4 + max(8, h // 3)],
                    fill=teeth)
    if tongue_v:
        d.ellipse([CX - w // 2, CY + h // 4, CX + w // 2, CY + h + 4], fill=tongue)
    if round_lips:
        d.ellipse([CX - w - 26, CY - h - 26, CX + w + 26, CY + h + 26],
                  outline=lip_dark, width=S * 4)
    return im


sprites = {}

# rest / closed (smile like her frame)
save(draw_closed(smile=0.6), "rest"); sprites["rest"] = 1
# M/B/P — pressed lips
im = canvas(); d = ImageDraw.Draw(im)
d.ellipse([CX - 150, CY - 20, CX + 150, CY + 22], fill=lip)
d.line([CX - 130, CY, CX + 130, CY], fill=lip_dark, width=S * 3)
save(im, "mbp"); sprites["mbp"] = 1
# A — big open
save(draw_open(120, 90, teeth_top=True), "A"); sprites["A"] = 1
# E — wide mid
save(draw_open(150, 55, teeth_top=True), "E"); sprites["E"] = 1
# I — wide small
save(draw_open(140, 34, teeth_top=True), "I"); sprites["I"] = 1
# O — round mid
save(draw_open(80, 78, teeth_top=False, round_lips=True), "O"); sprites["O"] = 1
# U/W/OO — small round
save(draw_open(52, 52, teeth_top=False, round_lips=True), "U"); sprites["U"] = 1
# F/V — lower lip under teeth
im = canvas(); d = ImageDraw.Draw(im)
d.ellipse([CX - 140, CY - 24, CX + 140, CY + 30], fill=lip)
d.rectangle([CX - 100, CY - 12, CX + 100, CY + 6], fill=teeth)
d.ellipse([CX - 120, CY + 2, CX + 120, CY + 34], fill=lip_dark)
save(im, "fv"); sprites["fv"] = 1
# L — open with tongue up
save(draw_open(90, 60, teeth_top=True, tongue_v=True), "L"); sprites["L"] = 1
# small open (transitional)
save(draw_open(90, 40, teeth_top=True), "small"); sprites["small"] = 1
# smile-open (talking smile)
save(draw_open(130, 45, teeth_top=True), "smile"); sprites["smile"] = 1
# wide-open (excited)
save(draw_open(130, 100, teeth_top=True, tongue_v=True), "wide"); sprites["wide"] = 1

meta = {"anchor": {"cx": 522, "cy": 507, "w": W, "h": H},
        "video": {"w": 1076, "h": 1924},
        "sprites": sorted(sprites)}
json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=1)
print("sprites:", sorted(sprites), "| colors lip=", lip, "skin=", skin)
