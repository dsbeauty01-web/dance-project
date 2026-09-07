#!/usr/bin/env python3
"""
to_landscape.py — make ANY clip stream-safe landscape 1080p.
  1920x1080 · 25fps · keyframe every 2s · yuv420p · aac 44.1k stereo · loudness -16 LUFS

  python to_landscape.py IN.mp4 OUT.mp4 [--mode auto|crop|blurpad|pad]
  python to_landscape.py --batch DIR_IN DIR_OUT [--mode auto]

Modes: auto = crop when source is landscape-ish (w/h >= 1.3), blurpad when portrait
       crop    = scale-to-cover + center crop (no bars)
       blurpad = portrait subject centered over a blurred, zoomed copy (broadcast look)
       pad     = black bars (avoid on desktop)
"""
import argparse, json, os, subprocess, sys, glob

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate", "-show_entries", "format=duration",
                          "-of", "json", path], capture_output=True, text=True).stdout
    j = json.loads(out or "{}")
    s = (j.get("streams") or [{}])[0]
    return int(s.get("width", 0)), int(s.get("height", 0)), float(j.get("format", {}).get("duration", 0))


def has_audio(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    return "audio" in out


def vf_for(mode, w, h):
    if mode == "auto":
        mode = "crop" if (w and h and w / h >= 1.3) else "blurpad"
    if mode == "crop":
        return "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=25,format=yuv420p[v]"
    if mode == "blurpad":
        return ("[0:v]split=2[a][b];"
                "[a]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=24:6,eq=brightness=-0.08[bg];"
                "[b]scale=-2:1080[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2,fps=25,format=yuv420p[v]")
    return "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=25,format=yuv420p[v]"


def convert(src, dst, mode="auto"):
    w, h, dur = probe(src)
    vf = vf_for(mode, w, h)
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", src]
    if has_audio(src):
        cmd += ["-filter_complex", vf + ";[0:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100[a]",
                "-map", "[v]", "-map", "[a]", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2"]
    else:  # silent clip → add silent stereo track so concat/stream muxers stay happy
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-filter_complex", vf,
                "-map", "[v]", "-map", "1:a", "-shortest", "-c:a", "aac", "-b:a", "96k"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", "25", "-g", "50", "-keyint_min", "50",
            "-sc_threshold", "0", "-pix_fmt", "yuv420p", "-movflags", "+faststart", dst]
    subprocess.run(cmd, check=True)
    w2, h2, d2 = probe(dst)
    assert (w2, h2) == (1920, 1080), f"output not 1080p: {w2}x{h2}"
    print(f"OK {os.path.basename(src)} {w}x{h} → {w2}x{h2} {d2:.1f}s mode={mode}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?"); ap.add_argument("dst", nargs="?")
    ap.add_argument("--batch", nargs=2, metavar=("DIR_IN", "DIR_OUT"))
    ap.add_argument("--mode", default="auto", choices=["auto", "crop", "blurpad", "pad"])
    a = ap.parse_args()
    if a.batch:
        os.makedirs(a.batch[1], exist_ok=True)
        for f in sorted(glob.glob(os.path.join(a.batch[0], "*.mp4"))):
            convert(f, os.path.join(a.batch[1], os.path.basename(f)), a.mode)
    elif a.src and a.dst:
        convert(a.src, a.dst, a.mode)
    else:
        ap.print_help(); sys.exit(1)


if __name__ == "__main__":
    main()
