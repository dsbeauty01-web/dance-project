"""
ttsreal_elevenlabs.py — ElevenLabs voice for LiveTalking, as a TTS class in the style of ttsreal.py (EdgeTTS/FishTTS…).

HOW TO WIRE (the only engine edit, ~6 lines):
  1. copy this file next to ttsreal.py in the LiveTalking repo
  2. in ttsreal.py (or wherever the TTS factory lives — app.py `--tts` switch / registry.py on newer builds):
        from ttsreal_elevenlabs import ElevenLabsTTS
        elif opt.tts == "elevenlabs": self.tts = ElevenLabsTTS(opt, self)
  3. start with  --tts elevenlabs   and env  ELEVENLABS_API_KEY  ELEVENLABS_VOICE_ID  (ELEVENLABS_MODEL default eleven_flash_v2_5)

CONTRACT (matches BaseTTS in ttsreal.py): txt_to_audio(msg) is called per text message with msg = (text, textevent);
we must push 16 kHz mono int16 PCM to self.parent.put_audio_frame(frame_bytes, eventpoint) in frames of
self.chunk samples (sample_rate // fps = 320 samples = 640 bytes at 16 kHz / 50 fps), sending the "start" event on the
first frame and "end" on the last — exactly what the built-in providers do. Whole sentences come from the engine's
sentence splitter; ElevenLabs Flash returns first audio in ~75 ms, so speech starts fast and stays continuous.
Output format pcm_16000 = no ffmpeg decode, no resample, no mp3 round-trip (the chunk-gap mistake of the last engine).
"""
import os, time, logging
import numpy as np
import requests

try:
    from ttsreal import BaseTTS, State
except Exception:  # allows import-time QA outside the repo
    class State:
        RUNNING, PAUSE = 0, 1
    class BaseTTS:
        def __init__(self, opt, parent):
            self.opt, self.parent = opt, parent
            self.fps, self.sample_rate = 50, 16000
            self.chunk = self.sample_rate // self.fps
            self.state = State.RUNNING

log = logging.getLogger("elevenlabs_tts")
E = os.environ.get


class ElevenLabsTTS(BaseTTS):
    def __init__(self, opt, parent):
        super().__init__(opt, parent)
        self.api_key = E("ELEVENLABS_API_KEY", "")
        self.voice = E("ELEVENLABS_VOICE_ID", "")
        self.model = E("ELEVENLABS_MODEL", "eleven_flash_v2_5")
        self.stability = float(E("TTS_STABILITY", "0.45")); self.similarity = float(E("TTS_SIMILARITY", "0.75")); self.style = float(E("TTS_STYLE", "0.35"))
        self.base = E("ELEVENLABS_BASE", "https://api.elevenlabs.io").rstrip("/")
        if not (self.api_key and self.voice):
            log.error("ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID missing — the engine will speak nothing")

    def txt_to_audio(self, msg):
        text, textevent = msg
        t0 = time.time()
        try:
            with requests.post(f"{self.base}/v1/text-to-speech/{self.voice}/stream",
                               headers={"xi-api-key": self.api_key, "Content-Type": "application/json"},
                               params={"output_format": "pcm_16000", "optimize_streaming_latency": "3"},
                               json={"text": text, "model_id": self.model,
                                     "voice_settings": {"stability": self.stability, "similarity_boost": self.similarity, "style": self.style, "use_speaker_boost": True}},
                               stream=True, timeout=30) as r:
                if r.status_code != 200:
                    log.error("elevenlabs %s: %s", r.status_code, r.text[:200]); return
                self._stream_pcm(r.iter_content(chunk_size=4096), textevent, t0)
        except Exception as e:
            log.error("elevenlabs request failed: %s", e)

    def _stream_pcm(self, chunks, textevent, t0):
        """Re-frame the raw pcm_16000 stream into engine frames; first frame carries 'start', last carries 'end'."""
        frame_bytes = self.chunk * 2
        buf = b""; first = True
        for data in chunks:
            if self.state != State.RUNNING:
                return
            buf += data
            while len(buf) >= frame_bytes:
                frame, buf = buf[:frame_bytes], buf[frame_bytes:]
                ev = None
                if first:
                    ev = {"status": "start", "text": textevent[0] if isinstance(textevent, (list, tuple)) else textevent, "msgenvent": textevent}
                    first = False
                    log.info("elevenlabs first audio in %.2fs", time.time() - t0)
                self.parent.put_audio_frame(self._to_float(frame), ev)
        # flush the tail, padded to a full frame, with the end event
        if buf:
            buf += b"\x00" * (frame_bytes - len(buf))
        else:
            buf = b"\x00" * frame_bytes
        self.parent.put_audio_frame(self._to_float(buf), {"status": "end", "text": textevent[0] if isinstance(textevent, (list, tuple)) else textevent, "msgenvent": textevent})

    @staticmethod
    def _to_float(frame: bytes) -> np.ndarray:
        # LiveTalking's providers hand float32 arrays in [-1, 1] to put_audio_frame
        return np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32767.0


if __name__ == "__main__":
    # smoke: fake parent collects frames; fake ElevenLabs = ELEVENLABS_BASE pointing at mock_elevenlabs.py (pcm_24000 there; fine for a frame-count test)
    class Opt: pass
    class Parent:
        def __init__(self): self.frames = []; self.events = []
        def put_audio_frame(self, f, ev=None):
            self.frames.append(len(f)); self.events.append(ev["status"] if ev else None)
    p = Parent(); t = ElevenLabsTTS(Opt(), p)
    t.txt_to_audio(("Rafael — one-forty-nine, 149 shekels live right now.", ("Rafael line",)))
    print("frames:", len(p.frames), "| all 320 samples:", all(n == 320 for n in p.frames), "| events:", [e for e in p.events if e])
