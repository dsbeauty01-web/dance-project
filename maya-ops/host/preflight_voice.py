#!/usr/bin/env python3
"""
preflight_voice.py — refuses to let Maya go live silent or in the wrong voice.

Root cause it exists for (2026-09-16): the .env on the shared volume was reconfigured by ANOTHER
project between sessions (voice id + model + provider all changed). The engine then synthesised
through a shim nobody had started, every call failed, and RTMPS happily published SILENT FRAMES
while `sent_audio` kept climbing. Frame counters do not prove sound.

  python preflight_voice.py                 # check everything, exit 1 on any failure
  python preflight_voice.py --fix           # also rewrite the wrong .env rows and start the shim
  python preflight_voice.py --expect-voice yd3FYOmSLO39myWHIQXq --expect-model eleven_flash_v2_5

Checks, in order (each prints PASS/FAIL and why):
  1. CONFIG   — the engine .env rows match what Maya needs (provider, voice id, model, sample rate)
  2. SHIM     — if provider is openai_compatible, something is actually listening on the shim port
  3. SYNTH    — one real synthesis round-trip through the engine's TTS path
  4. LEVEL    — the produced audio measures louder than -50 dBFS (silence reads ~-91)
  5. SAMPLERATE — output is >= 24000 Hz (16000 is the known silent-killer default)
Exit 0 only if all five pass. Wire it as the last gate before ot_live.py / going live.
"""
from __future__ import annotations
import argparse, json, os, re, shutil, subprocess, sys, time, wave

E = os.environ.get
HOST_ENV = os.path.expanduser(E("MAYA_HOST_ENV", "~/.maya/host.env"))
OT_DIR = E("OT_DIR", "/workspace/opentalking")
OT_ENV = os.path.join(OT_DIR, ".env")
OT_BASE = E("OT_BASE", "http://127.0.0.1:8210").rstrip("/")
SHIM = E("TTS_SHIM_URL", "http://127.0.0.1:8797").rstrip("/")
HOST_DIR = os.path.dirname(os.path.abspath(__file__))

# What Maya's LIVE host requires. Override per run with --expect-*.
WANT = {
    "OPENTALKING_TTS_DEFAULT_PROVIDER": E("MAYA_TTS_PROVIDER", "elevenlabs"),
    "OPENTALKING_TTS_ELEVENLABS_VOICE_ID": E("MAYA_VOICE_ID", "yd3FYOmSLO39myWHIQXq"),
    "OPENTALKING_TTS_ELEVENLABS_MODEL_ID": E("MAYA_VOICE_MODEL", "eleven_flash_v2_5"),
    # pcm_24000 CANNOT work on this build: the ElevenLabs adapter hardcodes input_format="mp3"
    # (providers/tts/elevenlabs/adapter.py -> _stream_decode_mp3_to_pcm_chunks), so raw PCM is fed
    # to an mp3 decoder and ffmpeg dies with "exit code 69". 2026-09-17.
    "OPENTALKING_TTS_ELEVENLABS_OUTPUT_FORMAT": E("MAYA_VOICE_FORMAT", "mp3_44100_128"),
    "OPENTALKING_TTS_SAMPLE_RATE": "24000",
}
# The brain the engine must talk to. Wrong value here = she reads OpenTalking's built-in Chinese
# error string aloud; the voice checks below all still PASS, which is how it reached air twice.
WANT_BRAIN = {
    "OPENTALKING_LLM_BASE_URL": E("MAYA_LLM_BASE_URL", "http://127.0.0.1:8795/v1"),
    "OPENTALKING_LLM_MODEL": E("MAYA_LLM_MODEL", "maya-brain"),
}
OK, BAD = [], []


def say(ok: bool, name: str, detail: str):
    (OK if ok else BAD).append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name:<12} {detail}", flush=True)


def read_env(path: str) -> dict:
    out = {}
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")   # later lines win, like dotenv
    return out


def write_env_rows(path: str, rows: dict):
    shutil.copy2(path, path + f".bak-{int(time.time())}")
    lines = open(path, encoding="utf-8").read().splitlines()
    for k, v in rows.items():
        hit = False
        for i, l in enumerate(lines):
            if l.split("=", 1)[0].strip() == k:
                lines[i] = f"{k}={v}"; hit = True          # rewrite EVERY occurrence (dupes exist)
        if not hit:
            lines.append(f"{k}={v}")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


# ---------- 0. brain ----------
def check_brain(fix: bool):
    """Runs FIRST. A perfect voice reading the wrong brain's error message is still a dead stream.

    2026-09-17: the Hebrew page work left OPENTALKING_LLM_BASE_URL=http://127.0.0.1:8796/v1 and
    model 'maya-he' in the shared .env. Nothing listens on 8796, so every LLM call failed and the
    engine spoke '抱歉，我暂时无法连接语言服务' — in Maya's voice, on a live stream, twice.
    """
    import requests
    env = read_env(OT_ENV)
    wrong = {k: v for k, v in WANT_BRAIN.items() if env.get(k) != v}
    for k, v in WANT_BRAIN.items():
        if k in wrong:
            print(f"        {k}: found {env.get(k, '(missing)')!r}, need {v!r}")
    if wrong and fix and os.path.exists(OT_ENV):
        write_env_rows(OT_ENV, wrong)          # rewrites EVERY duplicate row
        print(f"        rewrote {len(wrong)} brain row(s) in {OT_ENV} (backup kept)")
        env = read_env(OT_ENV)
        wrong = {k: v for k, v in WANT_BRAIN.items() if env.get(k) != v}
    if wrong:
        say(False, "BRAIN", f"{len(wrong)} row(s) wrong in {OT_ENV} — rerun with --fix, then RESTART the engine. "
                            "DO NOT GO LIVE — the engine will speak its error string.")
        return
    # config is right; now prove something actually answers there with the right model
    url = env["OPENTALKING_LLM_BASE_URL"].rstrip("/") + "/models"
    want_model = env["OPENTALKING_LLM_MODEL"]
    try:
        r = requests.get(url, timeout=5)
        ids = [m.get("id") for m in (r.json().get("data") or [])]
    except Exception as exc:
        say(False, "BRAIN", f"nothing answers at {url} ({type(exc).__name__}) — brain_server.py is not running. "
                            "DO NOT GO LIVE — the engine will speak its error string.")
        return
    ok = want_model in ids
    say(ok, "BRAIN", f"{url} → {want_model}" if ok
        else f"{url} returned {ids or 'no models'}, expected {want_model!r}. "
             "DO NOT GO LIVE — the engine will speak its error string.")


# ---------- 1. config ----------
def check_config(fix: bool) -> dict:
    env = read_env(OT_ENV)
    wrong = {k: v for k, v in WANT.items() if env.get(k) != v}
    for k, v in WANT.items():
        cur = env.get(k, "(missing)")
        if k in wrong:
            print(f"        {k}: found {cur!r}, need {v!r}")
    if wrong and fix and os.path.exists(OT_ENV):
        write_env_rows(OT_ENV, wrong)
        print(f"        rewrote {len(wrong)} row(s) in {OT_ENV} (backup kept)")
        env = read_env(OT_ENV); wrong = {k: v for k, v in WANT.items() if env.get(k) != v}
    say(not wrong, "CONFIG", f"{OT_ENV} matches Maya's voice config" if not wrong
        else f"{len(wrong)} row(s) wrong — another project rewrote the shared .env. Rerun with --fix, then RESTART the engine")
    # duplicate-key warning: a later duplicate silently wins
    if os.path.exists(OT_ENV):
        keys = [l.split("=", 1)[0].strip() for l in open(OT_ENV, encoding="utf-8") if "=" in l and not l.strip().startswith("#")]
        dupes = {k for k in WANT if keys.count(k) > 1}
        if dupes:
            print(f"        WARNING duplicate keys in .env (last one wins): {', '.join(sorted(dupes))}")
    return env


# ---------- 2. shim ----------
def check_shim(env: dict, fix: bool):
    provider = env.get("OPENTALKING_TTS_DEFAULT_PROVIDER", "")
    if provider != "openai_compatible":
        say(True, "SHIM", f"not needed (provider={provider or 'unset'})"); return
    import requests
    def up():
        try:
            return requests.get(SHIM + "/health", timeout=3).status_code < 400
        except Exception:
            return False
    if not up() and fix:
        shim = os.path.join(HOST_DIR, "tts_shim.py")
        if os.path.exists(shim):
            subprocess.Popen([sys.executable, shim], stdout=open("/tmp/tts_shim.log", "a"),
                             stderr=subprocess.STDOUT, start_new_session=True)
            for _ in range(10):
                time.sleep(1)
                if up():
                    break
    say(up(), "SHIM", f"{SHIM} reachable" if up()
        else f"provider is openai_compatible but NOTHING listens on {SHIM} — every synthesis will fail and the stream will publish SILENT frames")


# ---------- 3+4+5. real synthesis, real level ----------
def dbfs(path: str):
    # volumedetect reports at INFO level — "-v error" would swallow the numbers we came here for
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-v", "info", "-i", path, "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", out)
    p = re.search(r"max_volume:\s*(-?[\d.]+) dB", out)
    return (float(m.group(1)) if m else None, float(p.group(1)) if p else None)


def check_synthesis():
    import requests
    text = "Voice check. One, two, three. This is Maya."
    wav = "/tmp/preflight_voice.wav"
    got = None
    for path, payload in (("/tts/preview", {"text": text}), ("/v1/audio/speech", {"input": text, "response_format": "wav"})):
        try:
            r = requests.post(OT_BASE + path, json=payload, timeout=45)
            if r.status_code < 300 and len(r.content) > 2000:
                open(wav, "wb").write(r.content); got = path; break
            j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            if isinstance(j, dict) and j.get("audio_path") and os.path.exists(j["audio_path"]):
                shutil.copy2(j["audio_path"], wav); got = path; break
        except Exception:
            continue
    if not got:
        say(False, "SYNTH", f"no audio came back from {OT_BASE} — check the engine log for httpx.ConnectError (that is the shim being down)")
        say(False, "LEVEL", "skipped"); say(False, "SAMPLERATE", "skipped"); return
    say(True, "SYNTH", f"{got} returned {os.path.getsize(wav)} bytes")
    mean, peak = dbfs(wav)
    audible = mean is not None and mean > -50
    say(audible, "LEVEL", f"mean {mean} dBFS / peak {peak} dBFS — real speech" if audible
        else f"mean {mean} dBFS — that is SILENCE. Frame counters lie; this is the check that catches it")
    try:
        with wave.open(wav, "rb") as w:
            rate = w.getframerate()
        say(rate >= 24000, "SAMPLERATE", f"{rate} Hz" + ("" if rate >= 24000 else " — 16000 is the launch-script default that outranks .env; export OPENTALKING_TTS_SAMPLE_RATE=24000 BEFORE starting the engine"))
    except Exception as e:
        say(False, "SAMPLERATE", f"could not read wav header ({e})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="rewrite wrong .env rows and start the shim")
    ap.add_argument("--expect-voice"); ap.add_argument("--expect-model"); ap.add_argument("--expect-provider")
    a = ap.parse_args()
    if a.expect_voice: WANT["OPENTALKING_TTS_ELEVENLABS_VOICE_ID"] = a.expect_voice
    if a.expect_model: WANT["OPENTALKING_TTS_ELEVENLABS_MODEL_ID"] = a.expect_model
    if a.expect_provider: WANT["OPENTALKING_TTS_DEFAULT_PROVIDER"] = a.expect_provider
    print(f"PRE-FLIGHT VOICE · engine {OT_BASE} · env {OT_ENV}")
    check_brain(a.fix)          # first: a perfect voice reading the wrong brain is still a dead stream
    env = check_config(a.fix)
    check_shim(env, a.fix)
    check_synthesis()
    total = len(OK) + len(BAD)
    print(f"\n{len(OK)}/{total} passed" + ("" if not BAD else f" — BLOCKED BY: {', '.join(BAD)}"))
    print(f"Do NOT go live until all {total} pass." if BAD else "Cleared for live.")
    sys.exit(1 if BAD else 0)
