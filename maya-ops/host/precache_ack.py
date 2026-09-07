#!/usr/bin/env python3
"""
precache_ack.py — pre-render the "she heard you" clips once, so a comment gets a visible spoken
reaction in ~2-5s while the full 10s answer renders.

  python precache_ack.py              # renders generic acks + named acks for NAMES
  python precache_ack.py --names Dana,Tom,Lior,Refael,Noa,Yossi   # add names

Uses RENDER_URL (warm render_server): POST /render {"text"} → {"clip"}; converts to 1080p
landscape; writes ACK_DIR/generic_N.mp4 and ACK_DIR/<name>_N.mp4 + manifest.json.
"""
import argparse, json, os, subprocess, sys
import requests

E = os.environ.get
RENDER = E("RENDER_URL", "http://127.0.0.1:8793").rstrip("/")
ACK_DIR = E("ACK_DIR", "/workspace/maya-ops/bake/ack")
HERE = os.path.dirname(os.path.abspath(__file__))

GENERIC = [
    "Great question — one sec.",
    "Ooh, good one. Let me check.",
    "One moment, checking that for you.",
    "Love that question. Hold on.",
    "Yes! Give me a second.",
    "Got it — one sec.",
]
NAMED = [
    "{name} — great question, one sec.",
    "{name} — good one, let me check.",
    "{name} — one moment.",
]
DEFAULT_NAMES = ["Refael", "Dana", "Tom", "Lior", "Noa", "Yossi", "Maya", "Sara", "David", "Michal"]


def render(text: str) -> str:
    r = requests.post(RENDER + "/render", json={"text": text}, timeout=180)
    clip = r.json().get("clip")
    if not clip:
        raise RuntimeError(f"render failed: {r.text[:200]}")
    return clip


def landscape(src: str, dst: str):
    subprocess.run([sys.executable, os.path.join(HERE, "to_landscape.py"), src, dst], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", default=",".join(DEFAULT_NAMES))
    a = ap.parse_args()
    os.makedirs(ACK_DIR, exist_ok=True)
    manifest = {"generic": [], "named": {}}
    for i, line in enumerate(GENERIC):
        dst = os.path.join(ACK_DIR, f"generic_{i}.mp4")
        if not os.path.exists(dst):
            landscape(render(line), dst)
        manifest["generic"].append({"file": dst, "text": line}); print("ack", dst)
    for name in [n.strip() for n in a.names.split(",") if n.strip()]:
        manifest["named"][name] = []
        for i, tpl in enumerate(NAMED):
            dst = os.path.join(ACK_DIR, f"{name}_{i}.mp4")
            if not os.path.exists(dst):
                landscape(render(tpl.format(name=name)), dst)
            manifest["named"][name].append({"file": dst, "text": tpl.format(name=name)}); print("ack", dst)
    with open(os.path.join(ACK_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"DONE: {len(manifest['generic'])} generic + {sum(len(v) for v in manifest['named'].values())} named acks in {ACK_DIR}")


if __name__ == "__main__":
    main()
