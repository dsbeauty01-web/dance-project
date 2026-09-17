#!/usr/bin/env python3
"""
clip_cutter.py — turn a recorded live into 3 disclosed short clips for TikTok/IG/Reels (the funnel).
Uses metrics.jsonl (answer timestamps) to find the best moments: fastest answers, the medical deflection, a purchase.

  python clip_cutter.py --video recording.mp4 --started "2026-09-12 20:00:00" --metrics metrics.jsonl --out clips/
  → clips/clip_01_price.mp4 … (9:16, 1080x1920, captions burned in, "AI host" label, 20-35s each) + clips/manifest.json
Caption text = her spoken answer (from metrics). Pre/post padding configurable. Needs ffmpeg + DejaVu fonts.
"""
import argparse, json, os, subprocess
from datetime import datetime

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%")


def pick(metrics):
    by = {"purchase": None, "medical": None, "question": None}
    for m in metrics:
        i = m.get("intent")
        if i in by and (by[i] is None or m["latency"] < by[i]["latency"]):
            by[i] = m
    picks = [m for m in by.values() if m]
    fastest = sorted(metrics, key=lambda m: m["latency"])[:1]
    for f in fastest:
        if f not in picks:
            picks.append(f)
    return picks[:3]


def cut(video, t_off, m, out, pre=6, post=16):
    start = max(0, m["t_in"] - t_off - pre)
    cap = esc((m.get("say") or "")[:110])
    q = esc(f"{m['name'].split()[0]}: {m['text'][:60]}")
    vf = (f"crop=608:1080:656:0,scale=1080:1920,"
          f"drawbox=x=0:y=60:w=1080:h=70:color=black@0.55:t=fill,drawtext=fontfile={FONT}:text='●  AI host — Maya':fontcolor=white:fontsize=40:x=40:y=72,"
          f"drawtext=fontfile={FONT}:text='{q}':fontcolor=#ffd166:fontsize=42:x=(w-text_w)/2:y=1420:box=1:boxcolor=black@0.55:boxborderw=18,"
          f"drawtext=fontfile={FONT}:text='{cap}':fontcolor=white:fontsize=40:x=(w-text_w)/2:y=1540:box=1:boxcolor=black@0.55:boxborderw=18:line_spacing=8")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.2f}", "-t", str(pre + post), "-i", video, "-vf", vf, "-c:v", "libx264", "-crf", "20",
                    "-preset", "medium", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out], check=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--video", required=True); ap.add_argument("--started", required=True, help="recording start, 'YYYY-MM-DD HH:MM:SS' local")
    ap.add_argument("--metrics", default="metrics.jsonl"); ap.add_argument("--out", default="clips"); a = ap.parse_args()
    t_off = datetime.fromisoformat(a.started).timestamp()
    metrics = [json.loads(l) for l in open(a.metrics, encoding="utf-8")]
    metrics = [m for m in metrics if m.get("t_in", 0) >= t_off]
    os.makedirs(a.out, exist_ok=True); manifest = []
    for i, m in enumerate(pick(metrics), 1):
        out = os.path.join(a.out, f"clip_{i:02d}_{m['intent']}.mp4"); cut(a.video, t_off, m, out)
        manifest.append({"file": out, "intent": m["intent"], "hook": f"{m['name'].split()[0]} asked: {m['text'][:60]}", "caption": "AI host Maya answers live. #AIhost #skincare (AI-generated)", "latency": m["latency"]})
        print("clip", out)
    json.dump(manifest, open(os.path.join(a.out, "manifest.json"), "w"), indent=2, ensure_ascii=False)
    print(f"{len(manifest)} clips → {a.out}  (post with the AI label ON in TikTok/IG)")


if __name__ == "__main__":
    main()
