#!/usr/bin/env python3
"""
mock_elevenlabs.py — offline stand-in for api.elevenlabs.io so tts_shim.py and voice_bench.py can be QA'd without a key.
Routes: GET /v1/voices · POST /v1/text-to-speech/{id} (pcm_24000 or mp3) · POST /v1/text-to-voice/create-previews ·
        POST /v1/text-to-voice/create-voice-from-preview. Audio = 1.2s of a soft tone (real bytes, real lengths).
  python mock_elevenlabs.py   # :8799   → set ELEVENLABS_BASE=http://127.0.0.1:8799 in the code under test
"""
import base64, json, math, struct, subprocess, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CALLS = {"tts": 0, "design": 0, "save": 0}


def tone_pcm(seconds=1.2, rate=24000, freq=330):
    return b"".join(struct.pack("<h", int(6000 * math.sin(2 * math.pi * freq * i / rate))) for i in range(int(rate * seconds)))


def to_mp3(pcm):
    return subprocess.run(["ffmpeg", "-v", "error", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", "-", "-f", "mp3", "-b:a", "96k", "-"], input=pcm, capture_output=True).stdout


class H(BaseHTTPRequestHandler):
    def _s(self, code, body: bytes, ctype="application/json"):
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/v1/voices"):
            vs = [{"voice_id": "lib_sarah", "name": "Sarah", "labels": {"gender": "female", "description": "warm"}},
                  {"voice_id": "lib_matilda", "name": "Matilda", "labels": {"gender": "female", "description": "friendly"}},
                  {"voice_id": "lib_brian", "name": "Brian", "labels": {"gender": "male"}}]
            return self._s(200, json.dumps({"voices": vs}).encode())
        self._s(404, b"{}")

    def do_POST(self):
        if not self.headers.get("xi-api-key"):
            return self._s(401, b'{"detail":"missing key"}')
        n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n) or b"{}")
        p = self.path.split("?")[0]; q = self.path.split("?")[1] if "?" in self.path else ""
        if p.startswith("/v1/text-to-speech/"):
            CALLS["tts"] += 1; pcm = tone_pcm()
            return self._s(200, pcm if "pcm_24000" in q else to_mp3(pcm), "audio/pcm" if "pcm_24000" in q else "audio/mpeg")
        if p == "/v1/text-to-voice/create-previews":
            CALLS["design"] += 1
            return self._s(200, json.dumps({"previews": [{"generated_voice_id": "gen_" + uuid.uuid4().hex[:8], "audio_base_64": base64.b64encode(to_mp3(tone_pcm(2.0, freq=440))).decode()}]}).encode())
        if p == "/v1/text-to-voice/create-voice-from-preview":
            CALLS["save"] += 1
            return self._s(200, json.dumps({"voice_id": "saved_" + body.get("generated_voice_id", "x")[-6:]}).encode())
        self._s(404, b"{}")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("mock ElevenLabs on :8799", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8799), H).serve_forever()
