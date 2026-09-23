#!/usr/bin/env python3
"""capture_novasays_lines.py — renders every Nova Says line in HER voice.
Usage (on the pod or laptop with OPENAI_API_KEY set):
  python3 tools/capture_novasays_lines.py --lines beta/novasays/lines-en.json   --out audio/novasays/en    --voice marin
  python3 tools/capture_novasays_lines.py --lines beta/novasays/lines-he-m.json --out audio/novasays/he-m  --voice marin
  python3 tools/capture_novasays_lines.py --lines beta/novasays/lines-he-f.json --out audio/novasays/he-f  --voice marin
--voice MUST equal the Realtime session voice (rt_lk /health reports it) so the game lines and her live voice are one voice.
Writes <id>.1.mp3, <id>.2.mp3 (2 takes) + manifest.json {id: [files]}. Trims leading/trailing silence with ffmpeg when available.
"""
import argparse, json, os, shutil, subprocess, sys
from openai import OpenAI

STYLE = ("You are Nova, a bright, playful dance friend for a 6-year-old. Warm, excited, clear, a little silly. "
         "Say exactly the line, once. Short and punchy. No extra words.")

def trim(path):
    if not shutil.which("ffmpeg"): return
    tmp = path + ".tmp.mp3"
    cmd = ["ffmpeg","-y","-loglevel","error","-i",path,"-af",
           "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
           "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.10,areverse", tmp]
    if subprocess.run(cmd).returncode == 0 and os.path.getsize(tmp) > 1000: os.replace(tmp, path)
    elif os.path.exists(tmp): os.remove(tmp)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--voice", default="marin"); ap.add_argument("--takes", type=int, default=2)
    ap.add_argument("--model", default="gpt-4o-mini-tts")
    a = ap.parse_args()
    lines = {k:v for k,v in json.load(open(a.lines, encoding="utf-8")).items() if not k.startswith("_")}
    os.makedirs(a.out, exist_ok=True); client = OpenAI(); manifest = {}; failed = []
    for lid, text in lines.items():
        manifest[lid] = []
        for t in range(1, a.takes+1):
            fn = f"{lid}.{t}.mp3"; path = os.path.join(a.out, fn)
            try:
                r = client.audio.speech.create(model=a.model, voice=a.voice, input=text, instructions=STYLE, response_format="mp3")
                r.write_to_file(path); trim(path); manifest[lid].append(fn); print("ok", fn)
            except Exception as e:
                print("FAIL", fn, e); failed.append(fn)
    json.dump(manifest, open(os.path.join(a.out, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    missing = [k for k,v in manifest.items() if not v]
    print(f"\n{sum(len(v) for v in manifest.values())} clips · {len(missing)} ids with no take" + (f": {missing}" if missing else ""))
    sys.exit(1 if missing else 0)

if __name__ == "__main__": main()
