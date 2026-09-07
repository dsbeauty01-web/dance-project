#!/usr/bin/env python3
"""
showcase_build.py — the 90-second recorded showcase, assembled from real Maya clips.

  python showcase_build.py --config showcase.json --out maya-showcase-90s.mp4
  (also writes maya-showcase-vertical.mp4, 1080x1920 center-crop)

CONFIG (JSON) — a list of segments, in order:
  {"type":"answer",  "text":"Hey — I'm Maya. Yes, an AI host. Watch this.", "chat":[], "banner":false}
  {"type":"answer",  "text":"Dana — light, almost like water, absorbs in seconds.",
                     "chat":[{"name":"Dana","text":"what does it feel like?"}], "gesture":"SHOW"}
  {"type":"clip",    "file":"/abs/cutaway_apply_1080.mp4", "voice":"Watch this — one drop on the back of the hand.", "caption":"one drop · every morning"}
  {"type":"answer",  "text":"Honest answer, Lior — I can't make medical claims...", "chat":[{"name":"Lior","text":"will it cure my acne?"}]}
  {"type":"answer",  "text":"One-forty-nine — 149 shekels, link below.", "banner":true, "gesture":"POINT"}
  {"type":"answer",  "text":"I'm live 24/7. Type ME and I'll sort you out personally."}
"answer" → RENDER_URL /render (warm MuseTalk, coral) → 1080p → overlays.
"clip"   → existing file; if "voice" given, TTS is rendered as audio-only via render_server? NO — keep it simple:
           the clip keeps its own audio unless "voice_wav" (a pre-made wav) is given → mixed under.
Overlays: AI label (top-left), chat panel (right), price banner (bottom), caption (bottom-center).
Needs: ffmpeg with drawtext + DejaVu fonts; RENDER_URL; to_landscape.py next to this file.
"""
import argparse, json, os, subprocess, sys, tempfile
import requests

E = os.environ.get
RENDER = E("RENDER_URL", "http://127.0.0.1:8793").rstrip("/")
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
PRODUCT = E("SHOWCASE_PRODUCT", "Vitamin C Serum · 20% · 30 ml")
PRICE = E("SHOWCASE_PRICE", "149")
REG = E("SHOWCASE_REG", "249")


def esc(t: str) -> str:
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%")


def render(text: str) -> str:
    r = requests.post(RENDER + "/render", json={"text": text}, timeout=240)
    clip = r.json().get("clip")
    if not clip:
        sys.exit(f"render failed: {r.text[:200]}")
    out = clip.replace(".mp4", "_1080.mp4")
    subprocess.run([sys.executable, os.path.join(HERE, "to_landscape.py"), clip, out], check=True)
    return out


def overlays(seg: dict) -> str:
    """Build a drawtext/drawbox filter chain for one segment (input label [0:v] → [v])."""
    f = ["[0:v]drawbox=x=40:y=40:w=440:h=64:color=black@0.55:t=fill",
         f"drawtext=fontfile={FONT}:text='●  AI host  —  Maya  —  LIVE':fontcolor=white:fontsize=30:x=60:y=56"]
    y = 160
    for c in seg.get("chat", []):
        line = f"{c['name']}: {c['text']}"
        f.append(f"drawbox=x=1240:y={y - 12}:w=640:h=64:color=black@0.5:t=fill")
        f.append(f"drawtext=fontfile={FONT}:text='{esc(c['name'])}':fontcolor=#ffd166:fontsize=28:x=1260:y={y}")
        f.append(f"drawtext=fontfile={FONT_R}:text='{esc(c['text'])}':fontcolor=white:fontsize=28:x=1260+text_w*0+{20 + 16 * len(c['name'])}:y={y}")
        y += 84
    if seg.get("banner"):
        f.append("drawbox=x=0:y=900:w=1920:h=180:color=black@0.7:t=fill")
        f.append(f"drawtext=fontfile={FONT}:text='{esc(PRODUCT)}':fontcolor=white:fontsize=44:x=60:y=930")
        f.append(f"drawtext=fontfile={FONT_R}:text='Tap the link below to order':fontcolor=#ffd166:fontsize=30:x=60:y=1000")
        f.append(f"drawtext=fontfile={FONT}:text='LIVE PRICE  ₪{esc(PRICE)}':fontcolor=#ffd166:fontsize=64:x=1300:y=925")
        f.append(f"drawtext=fontfile={FONT_R}:text='reg ₪{esc(REG)}':fontcolor=white@0.8:fontsize=30:x=1310:y=1005")
    if seg.get("caption"):
        f.append(f"drawtext=fontfile={FONT}:text='{esc(seg['caption'])}':fontcolor=white:fontsize=40:x=(w-text_w)/2:y=840:box=1:boxcolor=black@0.5:boxborderw=14")
    return ",".join(f) + "[v]"


def make_segment(seg: dict, idx: int, workdir: str) -> str:
    src = render(seg["text"]) if seg["type"] == "answer" else seg["file"]
    out = os.path.join(workdir, f"seg_{idx:02d}.mp4")
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", src]
    fc = overlays(seg)
    maps = ["-map", "[v]"]
    if seg.get("voice_wav"):
        cmd += ["-i", seg["voice_wav"]]
        fc += ";[0:a][1:a]amix=inputs=2:weights=0.25 1:duration=first[a]"; maps += ["-map", "[a]"]
    else:
        maps += ["-map", "0:a?"]
    cmd += ["-filter_complex", fc] + maps + ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", "25", "-g", "50",
                                             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", out]
    subprocess.run(cmd, check=True)
    return out


def concat(parts: list, out: str):
    lst = out + ".txt"
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out], check=True)
    os.remove(lst)


def vertical(src: str, out: str):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vf", "crop=608:1080:656:0,scale=1080:1920", "-c:v", "libx264",
                    "-crf", "18", "-preset", "medium", "-c:a", "copy", out], check=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--config", required=True); ap.add_argument("--out", default="maya-showcase-90s.mp4")
    a = ap.parse_args()
    segs = json.load(open(a.config, encoding="utf-8"))
    work = tempfile.mkdtemp(prefix="showcase_")
    parts = [make_segment(s, i, work) for i, s in enumerate(segs)]
    concat(parts, a.out)
    vertical(a.out, a.out.replace(".mp4", "").replace("-90s", "") + "-vertical.mp4")
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.out], capture_output=True, text=True).stdout.strip()
    print(f"DONE {a.out} ({float(dur):.1f}s) + vertical cut")


if __name__ == "__main__":
    main()
