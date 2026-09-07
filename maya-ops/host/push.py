#!/usr/bin/env python3
"""
push.py — push ONE video source to one or many RTMP targets (Facebook / Amazon Live / YouTube)
with auto-restart. Uses ffmpeg tee muxer so all platforms get the same frames.

  python push.py --source /path/slot_stream_output.flv|.mp4|rtmp://127.0.0.1/live/maya --targets fb,amazon,yt
  python push.py --source LOOP.mp4 --loop --targets amazon          # loop a file (test)

ENV (~/.maya/host.env + ~/.maya/amazon.env):
  FB_RTMP_URL     (secure_stream_url from fb_tool live create)
  AMAZON_RTMP_URL + AMAZON_STREAM_KEY     (from the Amazon Live Creator app → external encoder)
  YT_RTMP_URL     (rtmp://a.rtmp.youtube.com/live2) + YT_STREAM_KEY
Encode (all targets): 1920x1080 25fps · keyframe 2s · 4500k CBR-ish · aac 44.1k 160k
"""
import argparse, os, signal, subprocess, sys, time

for p in ("~/.maya/host.env", "~/.maya/amazon.env"):
    p = os.path.expanduser(p)
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1); os.environ.setdefault(k, v.strip().strip('"'))
E = os.environ.get


def target_url(name: str) -> str:
    if name == "fb":
        u = E("FB_RTMP_URL", "");  assert u, "FB_RTMP_URL missing (fb_tool live create)"; return u
    if name == "amazon":
        u, k = E("AMAZON_RTMP_URL", ""), E("AMAZON_STREAM_KEY", "")
        assert u and k, "AMAZON_RTMP_URL / AMAZON_STREAM_KEY missing (Amazon Live Creator app → external encoder)"
        return u.rstrip("/") + "/" + k
    if name == "yt":
        u, k = E("YT_RTMP_URL", "rtmp://a.rtmp.youtube.com/live2"), E("YT_STREAM_KEY", "")
        assert k, "YT_STREAM_KEY missing"; return u.rstrip("/") + "/" + k
    raise SystemExit(f"unknown target {name}")


def build(source: str, loop: bool, targets: list) -> list:
    inp = []
    if source.startswith("rtmp://") or source.startswith("srt://"):
        inp = ["-i", source]
    else:
        inp = (["-re", "-stream_loop", "-1"] if loop else ["-re"]) + ["-i", source]
    tee = "|".join(f"[f=flv:onfail=ignore]{target_url(t)}" for t in targets)
    return ["ffmpeg", "-hide_banner", "-loglevel", "warning"] + inp + [
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=25,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency", "-b:v", "4500k", "-maxrate", "4500k",
        "-bufsize", "9000k", "-g", "50", "-keyint_min", "50", "-sc_threshold", "0", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
        "-flags", "+global_header", "-f", "tee", "-map", "0:v", "-map", "0:a?", tee]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True); ap.add_argument("--loop", action="store_true")
    ap.add_argument("--targets", default="fb"); ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    targets = [t.strip() for t in a.targets.split(",") if t.strip()]
    cmd = build(a.source, a.loop, targets)
    print("PUSH →", targets, flush=True)
    backoff = 3
    stop = {"v": False}
    signal.signal(signal.SIGINT, lambda *_: stop.__setitem__("v", True))
    signal.signal(signal.SIGTERM, lambda *_: stop.__setitem__("v", True))
    while not stop["v"]:
        t0 = time.time()
        p = subprocess.Popen(cmd)
        while p.poll() is None and not stop["v"]:
            time.sleep(1)
        if stop["v"]:
            p.terminate(); break
        ran = time.time() - t0
        print(f"ffmpeg exited rc={p.returncode} after {ran:.0f}s — restart in {backoff}s", flush=True)
        if a.once:
            sys.exit(p.returncode)
        time.sleep(backoff); backoff = 3 if ran > 60 else min(60, backoff * 2)


if __name__ == "__main__":
    main()
