#!/usr/bin/env python3
"""
onboard_product.py — from a one-page client brief to a ready product pack in minutes. Engine-agnostic:
the same pack feeds maya_host (our stack) or a rented engine (Genpio/BocaLive catalog import).

  python onboard_product.py brief.json --out /workspace/maya-ops/clients/<slug>/

brief.json:
{
  "brand": "Sela Beauty", "product": "Vitamin C Serum", "slug": "sela-serum",
  "price": 149, "regular_price": 249, "currency": "ILS", "shipping": "free over 200 ILS",
  "buy_url": "https://...", "facts": ["20% vitamin C", "30 ml", "one drop every morning on clean skin", "light texture, absorbs fast"],
  "faq": [{"q": "how do I use it", "a": "One drop every morning on clean skin, before moisturizer."}],
  "forbidden": ["cure", "treat", "clinically proven"],
  "photos": ["/abs/hero.png", "/abs/macro.png"], "tone": "warm, quick, a little witty"
}
OUTPUT: catalog.json (maya_host-compatible) · script_EN.md (opener / product / interaction / price / close, evergreen)
        faq.csv (instant-answer layer) · kling_prompts.md (hero + macro + host-with-product) · banner.png (1920x180)
        persona_addendum.md (brand tone lines) · README.md (what to do with each file)
"""
import argparse, csv, json, os, re, sys

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def cur_word(c): return {"ILS": "shekels", "USD": "dollars", "EUR": "euros"}.get(c.upper(), c)


def catalog(b):
    return {"products": [{
        "name": b["product"], "brand": b.get("brand", ""), "key": b.get("slug") or slug(b["product"]),
        "facts": b["facts"], "price": b["price"], "regular_price": b.get("regular_price"), "currency": b.get("currency", "ILS"),
        "shipping": b.get("shipping", ""), "buy_url": b.get("buy_url", "PLACEHOLDER"), "stock": b.get("stock", "in stock"),
        "faq": b.get("faq", []), "forbidden": b.get("forbidden", ["cure", "treat", "heal", "clinically proven", "guaranteed"]),
    }]}


def script(b):
    p, c = b["product"], cur_word(b.get("currency", "ILS"))
    f = b["facts"]; price = b["price"]; reg = b.get("regular_price")
    f1 = f[0] if f else ""; f2 = f[1] if len(f) > 1 else ""; f3 = f[2] if len(f) > 2 else ""
    reg_line = f", down from {reg}" if reg else ""
    return f"""# {b.get('brand','')} — {p} · live script (EN, evergreen, catalog-true)

## Opener (0:00, retention)
Hey — I'm Maya. Yes, an AI host, live right now. Ask me anything in the chat, I actually answer.
Today: {p}. {f1}.

## Product (0:20)
{f1}. {f2}. {f3}.
It's {price} {c} live right now{reg_line}. The link is right below this video.

## Interaction (2:00)
Type ME in the chat if you want the link personally. Joined mid-way? Perfect timing — ask me anything.

## Price + close (5:00)
One more time: {p}, {f1}. {price} {c} today{reg_line}. Link below, or type ME.

## Re-entry (loop)
Staying live — new round starting now. New here? Ask me anything about {p}.

## Never say
{", ".join(b.get('forbidden', ['cure','treat','clinically proven']))} — medical questions get: "I can't make medical claims, it's a cosmetic product; for skin conditions a dermatologist is the right address."
"""


def faq_rows(b):
    p, c = b["product"], cur_word(b.get("currency", "ILS")); price = b["price"]
    rows = [("how much|price|cost", f"{price} {c} live right now{', down from ' + str(b['regular_price']) if b.get('regular_price') else ''}. Link below, or type ME."),
            ("shipping|deliver", b.get("shipping") or "Shipping details are in the link below."),
            ("is this ai|are you ai|robot", "One hundred percent — I'm Maya, an AI host. Everything I say comes from the catalog."),
            ("hi|hello|hey|shalom", "Welcome in! Ask me anything about " + p + ".")]
    rows += [(q["q"], q["a"]) for q in b.get("faq", [])]
    return rows


def kling(b):
    p = b["product"]
    return f"""# Kling prompts — {p}  (Image-to-Video, Pro 1080p, 16:9, audio OFF, negative: talking, moving lips, open mouth, deformed hands, extra fingers)
1. HERO (product photo as start+end frame, 8s): "The {p} stands on a cream surface; warm light glides across it; camera completely still; premium retail commercial style."
2. MACRO/USE (10s): "Close-up of the {p} in use, natural speed, real skin/hands, subtle handheld camera, warm daylight, authentic beauty-vlog style."
3. HOST WITH PRODUCT (Maya holding image via Nano Banana, then 15s, first=last frame): "She holds the product chest-high with gentle natural micro-movements, blinks softly, calm warm presence. Mouth stays closed."
"""


def banner(b, path):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("PIL missing — skip banner"); return
    W, H = 1920, 180
    im = Image.new("RGBA", (W, H), (10, 12, 16, 200)); d = ImageDraw.Draw(im)
    fb, fr = ImageFont.truetype(FONT, 46), ImageFont.truetype(FONT_R, 28)
    d.text((60, 36), b["product"], font=fb, fill="white")
    d.text((60, 100), " · ".join(b["facts"][:3]), font=fr, fill=(235, 225, 205))
    price = f"{b.get('currency','ILS').upper() if b.get('currency','ILS').upper()!='ILS' else '₪'}{b['price']}"
    d.text((1400, 22), "LIVE PRICE", font=fr, fill=(255, 209, 102)); d.text((1400, 58), price, font=ImageFont.truetype(FONT, 84), fill=(255, 209, 102))
    if b.get("regular_price"):
        d.text((1700, 110), f"reg {b['regular_price']}", font=fr, fill=(220, 220, 220))
    d.text((60, 140), "Tap the link below to order", font=fr, fill=(255, 209, 102))
    im.save(path)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("brief"); ap.add_argument("--out", default=None)
    a = ap.parse_args()
    b = json.load(open(a.brief, encoding="utf-8"))
    out = a.out or os.path.join("clients", b.get("slug") or slug(b["product"]))
    os.makedirs(out, exist_ok=True)
    json.dump(catalog(b), open(os.path.join(out, "catalog.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(os.path.join(out, "script_EN.md"), "w", encoding="utf-8").write(script(b))
    with open(os.path.join(out, "faq.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["pattern", "answer"]); w.writerows(faq_rows(b))
    open(os.path.join(out, "kling_prompts.md"), "w", encoding="utf-8").write(kling(b))
    open(os.path.join(out, "persona_addendum.md"), "w", encoding="utf-8").write(f"Brand: {b.get('brand','')}\nTone: {b.get('tone','warm, quick')}\nProduct focus: {b['product']}\n")
    banner(b, os.path.join(out, "banner.png"))
    open(os.path.join(out, "README.md"), "w", encoding="utf-8").write(
        "catalog.json → MAYA_CATALOG (our stack) or engine catalog import\nscript_EN.md → scheduler beats / engine script\n"
        "faq.csv → instant-answer layer / engine Q&A pairs\nkling_prompts.md → human generates 3 clips\nbanner.png → OBS/overlay\n")
    print("PACK READY:", out, "→", ", ".join(sorted(os.listdir(out))))


if __name__ == "__main__":
    main()
