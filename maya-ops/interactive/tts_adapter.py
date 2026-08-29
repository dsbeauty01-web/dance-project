"""
tts_adapter.py — one TTS entry point with a quality ladder.
Picks the best available engine at call time so the voice upgrades the moment a
key is added — no other code changes:
    ElevenLabs (best, human)  ->  OpenAI gpt-4o-mini-tts  ->  edge-tts (free)
Used by the loop/render pipeline (scripted segments, pre-rendered answers). The
LIVE interactive path uses OpenAI Realtime's own voice; ElevenLabs applies to the
cascade/loop content, which is what the founder saw and wants more human.

Config (env):
  ELEVENLABS_API_KEY      -> enables ElevenLabs
  ELEVENLABS_VOICE_ID     -> default 21m00Tcm4TlvDq8ikWAM (a warm female preset)
  OPENAI_API_KEY / file   -> /workspace/.oai_key fallback (gpt-4o-mini-tts, coral)
Deps: requests (present). No heavy deps. Self-test runs offline (engine SELECTION
logic only — it does not fake a synth or claim audio it didn't produce).
"""
from __future__ import annotations
import os, subprocess, shutil

ELEVEN_DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"  # ElevenLabs "Rachel" — warm female
ELEVEN_MODEL = "eleven_multilingual_v2"


def _has_eleven() -> bool:
    return bool(os.environ.get("ELEVENLABS_API_KEY"))


def _oai_key() -> str | None:
    k = os.environ.get("OPENAI_API_KEY")
    if k:
        return k.strip()
    for p in ("/workspace/.oai_key", os.path.expanduser("~/.oai_key")):
        if os.path.exists(p):
            return open(p).read().strip()
    return None


def choose_engine() -> str:
    """Which engine WOULD be used right now (pure, testable)."""
    if _has_eleven():
        return "elevenlabs"
    if _oai_key():
        return "openai"
    if shutil.which("edge-tts"):
        return "edge-tts"
    return "none"


def _eleven(text: str, mp3_path: str) -> None:
    import requests
    vid = os.environ.get("ELEVENLABS_VOICE_ID", ELEVEN_DEFAULT_VOICE)
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "accept": "audio/mpeg",
                 "content-type": "application/json"},
        json={"text": text, "model_id": ELEVEN_MODEL,
              "voice_settings": {"stability": 0.4, "similarity_boost": 0.8}},
        timeout=60)
    r.raise_for_status()
    open(mp3_path, "wb").write(r.content)


def _openai(text: str, mp3_path: str) -> None:
    import requests
    r = requests.post("https://api.openai.com/v1/audio/speech",
        headers={"Authorization": "Bearer " + _oai_key()},
        json={"model": "gpt-4o-mini-tts", "voice": os.environ.get("OPENAI_TTS_VOICE", "coral"),
              "input": text, "instructions": "Warm, natural, friendly female live-shopping host.",
              "response_format": "mp3"}, timeout=60)
    r.raise_for_status()
    open(mp3_path, "wb").write(r.content)


def _edge(text: str, mp3_path: str) -> None:
    subprocess.run(["edge-tts", "--voice", "en-US-AriaNeural", "--text", text,
                    "--write-media", mp3_path], check=True)


def synthesize(text: str, wav_path: str, sr: int = 16000) -> dict:
    """Synthesize `text` to a mono wav at `sr`. Returns {engine, wav, mp3}.
    Raises if the chosen engine's call fails (never silently returns fake audio)."""
    engine = choose_engine()
    if engine == "none":
        raise RuntimeError("no TTS engine available: set ELEVENLABS_API_KEY or OPENAI key, or install edge-tts")
    mp3 = wav_path.rsplit(".", 1)[0] + ".mp3"
    {"elevenlabs": _eleven, "openai": _openai, "edge-tts": _edge}[engine](text, mp3)
    ff = shutil.which("ffmpeg") or "ffmpeg"
    subprocess.run([ff, "-nostdin", "-y", "-loglevel", "error", "-i", mp3,
                    "-ar", str(sr), "-ac", "1", wav_path], check=True)
    return {"engine": engine, "wav": wav_path, "mp3": mp3}


if __name__ == "__main__":
    # offline self-test: selection ladder only (no network, no fake synth)
    os.environ.pop("ELEVENLABS_API_KEY", None)
    saved = os.environ.pop("OPENAI_API_KEY", None)
    # with nothing + no key file + no edge-tts -> 'none' or 'edge-tts' if installed
    base = choose_engine()
    assert base in ("openai", "edge-tts", "none"), base   # 'openai' if ~/.oai_key exists
    os.environ["OPENAI_API_KEY"] = "sk-test"
    assert choose_engine() == "openai"
    os.environ["ELEVENLABS_API_KEY"] = "el-test"
    assert choose_engine() == "elevenlabs", "ElevenLabs must win when its key is set"
    del os.environ["ELEVENLABS_API_KEY"]
    if saved: os.environ["OPENAI_API_KEY"] = saved
    else: os.environ.pop("OPENAI_API_KEY", None)
    print("tts_adapter self-test: PASS (ladder elevenlabs>openai>edge>none)")
    print("engine right now:", choose_engine())
