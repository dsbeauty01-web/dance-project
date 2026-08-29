#!/usr/bin/env python3
# voice_bench.py — BENCH protocol for locking Maya's voice (voice skill).
# Same 30s serum script rendered on:
#   (a) gpt-4o-mini-tts, re-instructed as a warm live-show host  (streaming)
#   (b) ElevenLabs stock voices on the LOW-LATENCY tier          (streaming)
# Measures TTFA (time-to-first-audio-byte) per render; target <300ms. Saves each
# wav for a BLIND pick and appends a results table to maya-ops/voice/BENCH.md.
# NO cloning — designed stock voice only (no consented source). Winner is LOCKED.
#
# Run on the pod (needs OPENAI key at /workspace/.oai_key + ELEVENLABS_API_KEY + ffmpeg):
#   ELEVENLABS_API_KEY=... python maya-ops/voice/voice_bench.py
import os, time, json, subprocess, shutil, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
RENDERS = os.path.join(HERE, "renders"); os.makedirs(RENDERS, exist_ok=True)
BENCH_MD = os.path.join(HERE, "BENCH.md")

SCRIPT = ("Hey everyone, welcome in — I'm Maya. Today it's all about our concentrated "
          "vitamin C serum: twenty percent pure vitamin C, thirty milliliters. One drop "
          "every morning before your moisturizer, and over time your skin looks brighter "
          "and more even. Regular price is two forty-nine, but live with me right now it's "
          "just one forty-nine, with free shipping over two hundred. Tap the link below — "
          "I'd love for you to try it.")

# warm live-show host instruction (for gpt-4o-mini-tts `instructions`)
HOST_INSTRUCTION = ("Warm, upbeat, genuine live-shopping host. Friendly and natural, like "
                    "talking to a friend on camera. Conversational pacing, light real energy, "
                    "never salesy, never robotic. Clear natural English, a smile in the voice.")

# ElevenLabs warm-female stock voices to bench (low-latency model)
ELEVEN_VOICES = [
    ("Rachel",   "21m00Tcm4TlvDq8ikWAM"),
    ("Sarah",    "EXAVITQu4vr4xnSDxMaL"),
    ("Charlotte","XB0fDUnXU5powFXDhCwa"),
]
ELEVEN_MODEL = "eleven_turbo_v2_5"   # low-latency tier


def _oai_key():
    k = os.environ.get("OPENAI_API_KEY")
    if k: return k.strip()
    p = "/workspace/.oai_key"
    return open(p).read().strip() if os.path.exists(p) else None


def _to_wav(mp3, wav):
    ff = shutil.which("ffmpeg") or "ffmpeg"
    subprocess.run([ff, "-nostdin", "-y", "-loglevel", "error", "-i", mp3, "-ar", "16000", "-ac", "1", wav], check=True)


def _dur_s(wav):
    ff = shutil.which("ffprobe") or "ffprobe"
    try:
        out = subprocess.check_output([ff, "-v", "error", "-show_entries", "format=duration",
                                       "-of", "csv=p=0", wav]).decode().strip()
        return round(float(out), 2)
    except Exception:
        return None


def bench_openai():
    import requests
    key = _oai_key()
    if not key: return {"engine": "gpt-4o-mini-tts", "voice": "coral", "error": "no OpenAI key"}
    mp3 = os.path.join(RENDERS, "openai_coral.mp3")
    t0 = time.time(); ttfa = None
    with requests.post("https://api.openai.com/v1/audio/speech",
        headers={"Authorization": "Bearer " + key},
        json={"model": "gpt-4o-mini-tts", "voice": "coral", "input": SCRIPT,
              "instructions": HOST_INSTRUCTION, "response_format": "mp3"},
        stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(mp3, "wb") as f:
            for chunk in r.iter_content(4096):
                if chunk:
                    if ttfa is None: ttfa = int((time.time() - t0) * 1000)
                    f.write(chunk)
    wav = mp3[:-4] + ".wav"; _to_wav(mp3, wav)
    return {"engine": "gpt-4o-mini-tts", "voice": "coral(+host instr)", "ttfa_ms": ttfa,
            "audio_s": _dur_s(wav), "wav": os.path.relpath(wav, HERE)}


def bench_eleven():
    import requests
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key: return [{"engine": "elevenlabs", "error": "no ELEVENLABS_API_KEY — set it and re-run"}]
    rows = []
    for name, vid in ELEVEN_VOICES:
        mp3 = os.path.join(RENDERS, f"eleven_{name.lower()}.mp3")
        t0 = time.time(); ttfa = None
        try:
            with requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/stream?optimize_streaming_latency=3",
                headers={"xi-api-key": key, "accept": "audio/mpeg", "content-type": "application/json"},
                json={"text": SCRIPT, "model_id": ELEVEN_MODEL,
                      "voice_settings": {"stability": 0.4, "similarity_boost": 0.8}},
                stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(mp3, "wb") as f:
                    for chunk in r.iter_content(4096):
                        if chunk:
                            if ttfa is None: ttfa = int((time.time() - t0) * 1000)
                            f.write(chunk)
            wav = mp3[:-4] + ".wav"; _to_wav(mp3, wav)
            rows.append({"engine": "elevenlabs", "voice": name, "ttfa_ms": ttfa,
                         "audio_s": _dur_s(wav), "wav": os.path.relpath(wav, HERE)})
        except Exception as e:
            rows.append({"engine": "elevenlabs", "voice": name, "error": repr(e)[:160]})
    return rows


def main():
    results = [bench_openai()] + bench_eleven()
    ts = os.environ.get("BENCH_TS", "RUN")   # pass a real timestamp in; Date is blocked in some envs
    lines = [f"\n## BENCH run {ts}", "", "| # | engine | voice | TTFA (ms, target <300) | audio | wav (blind-listen) |",
             "|---|--------|-------|------------------------|-------|--------------------|"]
    for i, r in enumerate(results, 1):
        if r.get("error"):
            lines.append(f"| {i} | {r.get('engine')} | {r.get('voice','')} | — | — | ERROR: {r['error']} |")
        else:
            lines.append(f"| {i} | {r['engine']} | {r['voice']} | {r.get('ttfa_ms','?')} | {r.get('audio_s','?')}s | `{r['wav']}` |")
    lines += ["", "Blind-listen the wavs in renders/, pick the winner, then record the LOCK below."]
    open(BENCH_MD, "a").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("\nwavs in:", RENDERS)

if __name__ == "__main__":
    main()
