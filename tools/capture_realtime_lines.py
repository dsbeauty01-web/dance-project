#!/usr/bin/env python3
"""capture_realtime_lines.py — records every Nova Says FAST line through the OpenAI REALTIME model,
the same engine and voice she uses live — so the game lines and her live voice are ONE voice.

  pip install websockets --break-system-packages
  python3 tools/capture_realtime_lines.py --lines beta/nsfast/lines-en.json   --out audio/nsfast/en
  python3 tools/capture_realtime_lines.py --lines beta/nsfast/lines-he-m.json --out audio/nsfast/he-m --lang he
  python3 tools/capture_realtime_lines.py --lines beta/nsfast/lines-he-f.json --out audio/nsfast/he-f --lang he

[ADAPT] Copy MODEL / URL / headers / the session.update shape from pod/rt_lk.py — it is the proven live config.
Writes <id>.<take>.mp3 + manifest.json {id: [files]} + durations.json. Warns when a line is too slow for the game.
"""
import argparse, asyncio, base64, json, os, shutil, subprocess, sys, wave
import websockets

# [ADAPT 2026-09-27] Copied from the live brain, not guessed:
#   MODEL  pod/rt_lk.py:25  MODEL = os.environ.get("RT_MODEL", "gpt-realtime-2")
#          old default here was "gpt-4o-realtime-preview" — a DIFFERENT voice engine, which is
#          exactly the "two voices" complaint this pack exists to end.
#   VOICE  rt_lk /health returns {"voice": "marin"} — same default, kept.
MODEL = os.environ.get("REALTIME_MODEL", os.environ.get("RT_MODEL", "gpt-realtime-2"))
VOICE = os.environ.get("REALTIME_VOICE", "marin")
URL = f"wss://api.openai.com/v1/realtime?model={MODEL}"
# [ADAPT 2026-09-27] First EN capture came back at 1.9-2.4s per "real" line against a 1.4s
# budget — every command over. Two causes, both fixed without losing a word of the script:
# the em-dash in "Nova says — arms UP!" buys a real pause (removed from all command lines in
# the three lines-*.json), and "quickly" is too soft an instruction. This wording is explicit
# about tempo and about not breathing mid-line, which is what a game-show call actually is.
STYLE = {
 "en": "You are Nova, a bright, playful dance friend. Speak like a RAPID-FIRE game-show host calling out a move to a 6-year-old: maximum speed, urgent and excited, NO pause anywhere in the line, no breath between words, clipped and punchy. Say ONLY the exact line, once. Never add words.",
 "he": "את נובה, חברת ריקוד שמחה. דברי כמו מנחת שעשועון שצועקת פקודה לילד בן 6: מהר מאוד, נמרץ ונלהב, בלי שום הפסקה באמצע המשפט, בלי נשימה בין המילים, קצר וחד. אמרי רק את המשפט המדויק, פעם אחת. בלי מילים נוספות.",
}
LIMIT = {"real": 1.4, "bare": 0.8}

async def speak(line, lang):
    # [ADAPT 2026-09-27] The pack shipped the BETA realtime shape (OpenAI-Beta header,
    # session.modalities, output_audio_format, response.modalities). Against rt_lk's real model
    # every single line failed with `invalid_request_error.beta_api_shape_disabled` — 0 of 46
    # clips recorded. Below is the GA shape lifted from pod/rt_lk.py:
    #   headers          rt_lk.py:649  {"Authorization": ...} and NOTHING else
    #   session.update   rt_lk.py:226  {"type":"realtime","output_modalities":["audio"],
    #                                   "audio":{"output":{"format":{"type":"audio/pcm","rate":24000},"voice":...}}}
    #   exact line       rt_lk.py say_resp() — conversation:"none" + a "repeat after me" user
    #                    message, which is how the live brain stops her paraphrasing a staged line.
    hdrs = {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}
    ask = ("חזרי אחריי מילה במילה, פעם אחת, מהר ובהתלהבות: " if lang == "he"
           else "Repeat after me word for word, once, fast and excited: ")
    async with websockets.connect(URL, additional_headers=hdrs, max_size=None) as ws:
        await ws.send(json.dumps({"type":"session.update","session":{
            "type":"realtime","output_modalities":["audio"],"instructions":STYLE[lang],
            "audio":{"output":{"format":{"type":"audio/pcm","rate":24000},"voice":VOICE}}}}))
        await ws.send(json.dumps({"type":"response.create","response":{"conversation":"none",
            "instructions":STYLE[lang],
            "input":[{"type":"message","role":"user","content":[{"type":"input_text","text":ask + line}]}]}}))
        pcm = bytearray()
        async for msg in ws:
            ev = json.loads(msg)
            if ev.get("type") in ("response.audio.delta", "response.output_audio.delta"): pcm += base64.b64decode(ev["delta"])
            elif ev.get("type") == "response.done": break
            elif ev.get("type") == "error": raise RuntimeError(ev)
        return bytes(pcm)

def to_mp3(pcm, path):
    wav = path[:-4] + ".wav"
    with wave.open(wav, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
    if shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",wav,"-af",
            "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse",
            "-b:a","96k",path], check=True)
        os.remove(wav)
    else: os.replace(wav, path[:-4] + ".wav")

def dur(path):
    if not shutil.which("ffprobe"): return None
    out = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",path], capture_output=True, text=True).stdout.strip()
    return float(out) if out else None

async def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--lines", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--lang", default="en"); ap.add_argument("--takes", type=int, default=2); a = ap.parse_args()
    lines = {k:v for k,v in json.load(open(a.lines, encoding="utf-8")).items() if not k.startswith("_")}
    os.makedirs(a.out, exist_ok=True); manifest, durs, slow = {}, {}, []
    for lid, text in lines.items():
        manifest[lid] = []
        for t in range(1, a.takes+1):
            fn = f"{lid}.{t}.mp3"; path = os.path.join(a.out, fn)
            try:
                to_mp3(await speak(text, a.lang), path); d = dur(path); durs[fn] = d; manifest[lid].append(fn)
                kind = "real" if lid.endswith(".real") else "bare" if lid.endswith(".bare") else None
                if kind and d and d > LIMIT[kind]: slow.append(f"{fn} {d:.2f}s > {LIMIT[kind]}s")
                print("ok", fn, f"{d:.2f}s" if d else "")
            except Exception as e: print("FAIL", fn, e)
    json.dump(manifest, open(os.path.join(a.out,"manifest.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(durs, open(os.path.join(a.out,"durations.json"),"w"), indent=1)
    missing = [k for k,v in manifest.items() if not v]
    print(f"\n{sum(len(v) for v in manifest.values())} clips · missing ids: {missing or 'none'}")
    if slow: print("TOO SLOW for a fast game (re-record or shorten):\n  " + "\n  ".join(slow))
    sys.exit(1 if missing else 0)

if __name__ == "__main__": asyncio.run(main())
