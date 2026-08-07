#!/usr/bin/env python3
"""LOOP MODE step 2 — script JSON -> her spoken video segments (pod-side).

Usage:  python3 bake_playlist.py scripts/<product>.he.json outdir/

Per segment:  Hebrew TTS (edge-tts) -> wav
           -> RENDER: lipsynced video of her saying it
           -> AI disclosure label burned INTO the pixels (platform law, EU AI Act)
           -> 1080x1920 mpegts (.ts) segment, aligned codec params

Output .ts (MPEG-TS), not .mp4: the playlist player streams by concatenating TS
segments into ONE ffmpeg stdin pipe — that is what makes reply-insertion gapless.

RENDER has two modes:
  MODE=musetalk  (the real thing) — offline MuseTalk render from the maya_idle bake.
                 WIRE-UP TODO: the exact inference entrypoint on the volume must be
                 confirmed on the pod at first bake (LiveTalking ships MuseTalk under
                 /workspace/LiveTalking; look for musetalk/scripts/realtime_inference.py
                 or use LiveTalking's offline path). Fails loudly if not wired.
  MODE=mux       (works TODAY, no GPU) — loops the idle bake video under the TTS audio.
                 No lipsync; mouth won't match. Good enough to test the ENTIRE pipeline
                 end-to-end (bake -> playlist -> RTMP -> insertion) before bake day.
"""
import json, os, pathlib, subprocess, sys

VOICE = os.environ.get("MAYA_TTS_VOICE", "he-IL-HilaNeural")   # founder picks; see plan
MODE = os.environ.get("MAYA_BAKE_MODE", "mux")
IDLE = os.environ.get("MAYA_IDLE_MP4", "/workspace/maya-ops/gestures/idle_maya.mp4")
LABEL = os.environ.get("MAYA_AI_LABEL", "AI · מיה — מנחה וירטואלית")  # founder approves text
FONT = os.environ.get("MAYA_LABEL_FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

def sh(cmd):
    print(">>", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True)

def tts(text, wav):
    sh(["edge-tts", "--voice", VOICE, "--text", text, "--write-media", wav])

def render(wav, out_ts, seg_id):
    # drawtext burns the AI label into the pixels — survives re-streams and screenshots.
    label = (f"drawtext=fontfile={FONT}:text='{LABEL}':fontcolor=white@0.85:fontsize=34:"
             f"box=1:boxcolor=black@0.35:boxborderw=12:x=(w-text_w)/2:y=44")
    common = ["-vf", f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{label}",
              "-r", "25", "-c:v", "libx264", "-preset", "veryfast", "-profile:v", "high",
              "-pix_fmt", "yuv420p", "-g", "50", "-c:a", "aac", "-ar", "44100", "-b:a", "128k",
              "-f", "mpegts", out_ts]
    if MODE == "mux":
        sh(["ffmpeg", "-y", "-stream_loop", "-1", "-i", IDLE, "-i", wav,
            "-map", "0:v:0", "-map", "1:a:0", "-shortest", *common])
    elif MODE == "musetalk":
        raise SystemExit(f"RENDER {seg_id}: musetalk offline path not wired yet — "
                         "confirm the inference entrypoint on the pod, then implement here. "
                         "Refusing to pretend (use MAYA_BAKE_MODE=mux to test the pipeline).")
    else:
        raise SystemExit(f"unknown MAYA_BAKE_MODE={MODE}")

def main(script_path, outdir):
    script = json.loads(pathlib.Path(script_path).read_text(encoding="utf-8"))
    if script.get("holes"):
        raise SystemExit(f"REFUSED: {script['product_id']} still has {script['holes']} "
                         "[NEEDS-FOUNDER] holes — a script with holes never reaches a bake.")
    out = pathlib.Path(outdir, script["product_id"]); out.mkdir(parents=True, exist_ok=True)
    manifest = {"product_id": script["product_id"], "voice": VOICE, "mode": MODE, "segments": []}
    for i, s in enumerate(script["segments"]):
        base = f"{i:02d}-{s['id']}"
        wav, ts = str(out / f"{base}.wav"), str(out / f"{base}.ts")
        tts(s["text_he"], wav)
        render(wav, ts, s["id"])
        manifest["segments"].append({"file": f"{base}.ts", "role": s["role"],
                                     "gesture": s.get("gesture"), "seq": i})
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    print(f"BAKED {script['product_id']}: {len(manifest['segments'])} segments -> {out}")

if __name__ == "__main__":
    if len(sys.argv) != 3: raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
