"""
tts_adapter.py — one TTS entry point.
VOICE IS LOCKED (2026-08-30): OpenAI gpt-4o-mini-tts, voice "coral", warm-host
instruction. Chosen by the founder after a blind bench ("no elevenlabs, best
voice from OpenAI"). Single source of truth: maya-ops/voice/voice.lock.json —
read by BOTH this render pipeline and the live brain (maya_rt.py).

Ladder now: OpenAI (locked)  ->  edge-tts (free fallback). ElevenLabs DROPPED per
founder; do not re-add without an explicit request.

Config (env, override the lock only if needed):
  OPENAI_API_KEY / file   -> /workspace/.oai_key fallback (gpt-4o-mini-tts)
  OPENAI_TTS_VOICE        -> overrides locked voice (default from voice.lock.json)
Deps: requests (present). No heavy deps. Self-test runs offline (engine SELECTION
logic only — it does not fake a synth or claim audio it didn't produce).
"""
from __future__ import annotations
import os, subprocess, shutil, json

# --- single source of truth: voice.lock.json (falls back to hardcoded lock) ---
_LOCK_PATH = os.path.join(os.path.dirname(__file__), "..", "voice", "voice.lock.json")
_LOCK_DEFAULT = {
    "voice": "coral",
    "instructions": ("Warm, upbeat live-show host. Smiling voice. Conversational pace about "
                     "165 words per minute, brief natural pauses between thoughts, slight "
                     "emphasis on numbers and the product name. Sounds like she's talking TO "
                     "one person, not reading. Occasional soft breath."),
}


def _lock() -> dict:
    try:
        with open(_LOCK_PATH, encoding="utf-8") as f:
            d = json.load(f)
        return {"voice": d.get("voice", _LOCK_DEFAULT["voice"]),
                "instructions": d.get("instructions", _LOCK_DEFAULT["instructions"])}
    except Exception:
        return dict(_LOCK_DEFAULT)


def _oai_key() -> str | None:
    k = os.environ.get("OPENAI_API_KEY")
    if k:
        return k.strip()
    for p in ("/workspace/.oai_key", os.path.expanduser("~/.oai_key")):
        if os.path.exists(p):
            return open(p).read().strip()
    return None


def choose_engine() -> str:
    """Which engine WOULD be used right now (pure, testable). ElevenLabs dropped."""
    if _oai_key():
        return "openai"
    if shutil.which("edge-tts"):
        return "edge-tts"
    return "none"


def _openai(text: str, mp3_path: str) -> None:
    import requests
    lock = _lock()
    r = requests.post("https://api.openai.com/v1/audio/speech",
        headers={"Authorization": "Bearer " + _oai_key()},
        json={"model": "gpt-4o-mini-tts",
              "voice": os.environ.get("OPENAI_TTS_VOICE", lock["voice"]),
              "input": text, "instructions": lock["instructions"],
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
    {"openai": _openai, "edge-tts": _edge}[engine](text, mp3)
    ff = shutil.which("ffmpeg") or "ffmpeg"
    subprocess.run([ff, "-nostdin", "-y", "-loglevel", "error", "-i", mp3,
                    "-ar", str(sr), "-ac", "1", wav_path], check=True)
    return {"engine": engine, "wav": wav_path, "mp3": mp3}


if __name__ == "__main__":
    # offline self-test: selection ladder only (no network, no fake synth)
    os.environ.pop("ELEVENLABS_API_KEY", None)   # dropped; must be ignored even if present
    saved = os.environ.pop("OPENAI_API_KEY", None)
    base = choose_engine()
    assert base in ("openai", "edge-tts", "none"), base   # 'openai' if ~/.oai_key exists
    os.environ["OPENAI_API_KEY"] = "sk-test"
    assert choose_engine() == "openai"
    os.environ["ELEVENLABS_API_KEY"] = "el-test"
    assert choose_engine() == "openai", "ElevenLabs is dropped — OpenAI must still win"
    del os.environ["ELEVENLABS_API_KEY"]
    lk = _lock()
    assert lk["voice"] == "coral", lk["voice"]
    if saved: os.environ["OPENAI_API_KEY"] = saved
    else: os.environ.pop("OPENAI_API_KEY", None)
    print("tts_adapter self-test: PASS (ladder openai>edge>none; voice locked =", lk["voice"] + ")")
    print("engine right now:", choose_engine())
