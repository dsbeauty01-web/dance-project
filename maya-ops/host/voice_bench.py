#!/usr/bin/env python3
"""
voice_bench.py — the blind voice test from the voice skill: same 25s script on 3 voices → wav files → you listen.
  python voice_bench.py                # renders what keys allow: OpenAI coral (directed), OpenAI marin/cedar via TTS if available, ElevenLabs (if ELEVENLABS_API_KEY)
Outputs bench/voice_A.wav … + bench/KEY.json (which is which). Normalizes to -16 LUFS. Pick with your ears; lock via OT TTS profile.
"""
import json, os, random, subprocess
import requests

E = os.environ.get
SCRIPT = ("Hey — I'm Maya, and yes, I'm an AI host, live right now. Dana — great question. It's light, almost like water, and it absorbs in seconds. "
          "One drop every morning on clean skin, before your moisturizer. And today it's one-forty-nine — 149 shekels — down from two-forty-nine. Link below, or type ME.")
INSTR = "Warm, upbeat live-show host. Smiling voice. Conversational pace, brief natural pauses between thoughts, slight emphasis on numbers and the product name. Talking to one person, not reading."
os.makedirs("bench", exist_ok=True)
cands = []
if E("OPENAI_API_KEY"):
    for voice in ("coral", "marin", "cedar", "nova"):
        r = requests.post("https://api.openai.com/v1/audio/speech", headers={"Authorization": f"Bearer {E('OPENAI_API_KEY')}"},
                          json={"model": "gpt-4o-mini-tts", "voice": voice, "input": SCRIPT, "instructions": INSTR, "response_format": "wav"}, timeout=60)
        if r.status_code == 200:
            p = f"bench/raw_openai_{voice}.wav"; open(p, "wb").write(r.content); cands.append((f"openai:{voice}", p))
        else:
            print("openai", voice, "→", r.status_code, r.text[:80])
if E("ELEVENLABS_API_KEY") and E("ELEVENLABS_VOICE_ID"):
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{E('ELEVENLABS_VOICE_ID')}", headers={"xi-api-key": E("ELEVENLABS_API_KEY")},
                      params={"output_format": "pcm_24000"}, json={"text": SCRIPT, "model_id": E("ELEVENLABS_MODEL", "eleven_flash_v2_5")}, timeout=60)
    if r.status_code == 200:
        p = "bench/raw_elevenlabs.pcm"; open(p, "wb").write(r.content)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", p, "bench/raw_elevenlabs.wav"], check=True); cands.append(("elevenlabs", "bench/raw_elevenlabs.wav"))
if not cands:
    raise SystemExit("no keys: set OPENAI_API_KEY and/or ELEVENLABS_API_KEY(+VOICE_ID)")
random.shuffle(cands); key = {}
for i, (name, p) in enumerate(cands):
    out = f"bench/voice_{chr(65 + i)}.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", p, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", out], check=True); key[os.path.basename(out)] = name
json.dump(key, open("bench/KEY.json", "w"), indent=2)
print("listen blind:", ", ".join(sorted(key))); print("answer key in bench/KEY.json (don't peek until you've picked)")
