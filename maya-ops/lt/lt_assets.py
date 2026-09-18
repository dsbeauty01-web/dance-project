#!/usr/bin/env python3
"""
lt_assets.py — turn the prepped gesture clips into LiveTalking "action choreography" assets.

  python lt_assets.py --clips /workspace/maya-ops/bake/gesture_mode --out /workspace/LiveTalking/data/custom
      → data/custom/<name>/img/%08d.png + audio.wav per clip, and data/custom_config.json
      → prints the audiotype map to put in ~/.maya/host.env (LT_AT_WAVE=2 …)

Per the official docs (§3.4): frames at 25 fps (`-vf fps=25 -qmin 1 -q:v 1 -start_number 0 img/%08d.png`),
audio 16 kHz mono PCM (`-vn -acodec pcm_s16le -ac 1 -ar 16000 audio.wav`). Silent clips get a silent wav of the
same length (LiveTalking needs an audio track per custom video).
audiotype 1 = idle (auto when silent) · 2 = wave · 3 = point · 4 = show (both hands) · 5 = nod · 6 = goodbye
Every clip is validated as ONE continuous take (scene-change scan) before it is converted — stitched clips flicker.
"""
import argparse, glob, json, os, re, subprocess, sys

ROLES = [("idle", 1, ["gm_idle*", "*idle*"]), ("wave", 2, ["gm_wave*", "*wave*"]), ("point", 3, ["gm_point*", "*point*"]),
         ("show", 4, ["gm_bothhand*", "*bothhand*", "*show*"]), ("nod", 5, ["gm_nod*", "*nod*", "*nudge*"]), ("goodbye", 6, ["gm_goodbye*", "*goodbye*"])]


def find(clips, pats):
    for p in pats:
        h = sorted(glob.glob(os.path.join(clips, p + ".mp4")))
        if h: return h[0]
    return None


def duration(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip() or 0)


def cuts(p, thr=0.06):
    out = subprocess.run(["ffmpeg", "-v", "info", "-i", p, "-vf", f"select='gt(scene,{thr})',showinfo", "-f", "null", "-"], capture_output=True, text=True).stderr
    return out.count("pts_time:")


def has_audio(p):
    return "audio" in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", p], capture_output=True, text=True).stdout


def convert(src, dst_dir):
    img = os.path.join(dst_dir, "img"); os.makedirs(img, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vf", "fps=25", "-qmin", "1", "-q:v", "1", "-start_number", "0", os.path.join(img, "%08d.png")], check=True)
    wav = os.path.join(dst_dir, "audio.wav")
    if has_audio(src):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000", wav], check=True)
    else:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", f"{duration(src):.3f}", "-acodec", "pcm_s16le", wav], check=True)
    n = len(glob.glob(os.path.join(img, "*.png")))
    return n, wav


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--clips", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--config", default=None, help="path for custom_config.json (default: <out>/../custom_config.json)")
    a = ap.parse_args()
    cfg, env_lines, skipped = [], [], []
    for role, at, pats in ROLES:
        src = find(a.clips, pats)
        if not src:
            skipped.append(role); continue
        c = cuts(src)
        if c:
            print(f"REJECT {role}: {os.path.basename(src)} has {c} scene jump(s) — stitched clips flicker. Use one continuous take."); skipped.append(role); continue
        d = os.path.join(a.out, role); n, wav = convert(src, d)
        cfg.append({"audiotype": at, "imgpath": os.path.relpath(os.path.join(d, "img"), os.path.dirname(a.config or os.path.join(a.out, ".."))), 
                    "audiopath": os.path.relpath(wav, os.path.dirname(a.config or os.path.join(a.out, "..")))})
        env_lines.append(f"LT_AT_{role.upper() if role != 'show' else 'SHOW'}={at}")
        print(f"OK {role:<8} audiotype={at} frames={n} {duration(src):.1f}s ← {os.path.basename(src)}")
    cfg_path = a.config or os.path.normpath(os.path.join(a.out, "..", "custom_config.json"))
    json.dump(cfg, open(cfg_path, "w"), indent=1)
    print(f"\ncustom_config.json → {cfg_path} ({len(cfg)} clips)")
    print("put in ~/.maya/host.env:\n  " + "\n  ".join(env_lines))
    if skipped: print("missing/skipped roles (no gesture will fire for them):", ", ".join(skipped))
    if "idle" in skipped: sys.exit("idle clip is REQUIRED (audiotype 1) — without it she freezes when silent")


if __name__ == "__main__":
    main()
