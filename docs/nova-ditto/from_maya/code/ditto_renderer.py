"""ditto_renderer.py -- SHIM_RENDERER=ditto_renderer:Renderer (lane/live-trio 2026-10-25, default OFF: the live keeps
flashhead_renderer). The FIGURE renderer: Ditto bends the lips of the character's own idle video (half / full figure,
face ~200-320 px of a 1080x1920 frame), served by ditto_server.py in its own venv (brought up by ditto_up.sh, before READY).

Contract (soulx_shim.make_renderer / adopt_chunk):
  .chunk_frames = 25, .chunk_samples = 16000   -> the shim adopts this chunk (5 Ditto hubert steps of 0.2 s)
  .render(audio_f32_16k[16000]) -> 25 BGR uint8 frames at the source size (1080x1920), already the whole picture
  .av_delay_frames = DITTO_PRIME: every frame returned is that many frames behind the audio just given, constant ->
     run the shim with SHIM_AV_OFFSET_MS = -40 * DITTO_PRIME (audio delayed by the same amount).
Use with SHIM_IDLE_MOTION=0 (the renderer streams continuously; silence is the idle video with her closed mouth) and
SHIM_LAYOUT=proof + PROOF_FULLFRAME=1 (the frame is the picture; card, chips and bubbles are drawn over it).
Env: DITTO_PORT 8031 · DITTO_WAIT_SEC 1500 (setup + load) · DITTO_TIMEOUT_SEC 2.5 per chunk
GESTURES (lane/live-motion, default OFF; needs the server's DITTO_BANK): DITTO_GESTURES=1 -> gesture_client.GestureClient: brain
events (Gesture API v1: $MAYA_GESTURE_EVENTS file and/or UDP $MAYA_GESTURE_UDP) are held until the line they announce reaches the
renderer, then sent to the server, so the clip starts with her words. DITTO_GESTURE_KEYWORDS=1 adds the fallback: a line nobody
tagged fires a gesture from its own words (product name / price -> hold up, "open" -> open, "closer" -> closer, ...).
"""
import json, os, subprocess, time, urllib.request

import numpy as np

E = os.environ.get
HERE = os.path.dirname(os.path.abspath(__file__))


def _health(url, t=2.0):
    try:
        with urllib.request.urlopen(url + "/health", timeout=t) as r: return json.loads(r.read())
    except Exception:
        return None


class Renderer:
    def __init__(self, cfg=None):
        self.url = f"http://127.0.0.1:{E('DITTO_PORT', '8031')}"
        h = _health(self.url)
        if not (h and h.get("ready")):
            t = time.time()
            rc = subprocess.call(["bash", os.path.join(HERE, "ditto_up.sh")], timeout=float(E("DITTO_WAIT_SEC", "1500")))
            print(f"[ditto] ditto_up.sh rc={rc} in {time.time() - t:.0f}s", flush=True)
            h = _health(self.url)
            if not (h and h.get("ready")): raise RuntimeError(f"ditto: server not ready (rc {rc}, health {h})")
        self.chunk_frames, self.chunk_samples, self.fps = int(h["chunk_frames"]), int(h["chunk_samples"]), int(h["fps"])
        self.av_delay_frames = int(h.get("prime", 0)); self.info = h.get("info")
        self.timeout = float(E("DITTO_TIMEOUT_SEC", "2.5")); self.errors = 0; self._last = None
        want = -40 * self.av_delay_frames
        if float(E("SHIM_AV_OFFSET_MS", "0") or 0) != want:
            print(f"[ditto] !! SHIM_AV_OFFSET_MS should be {want} for DITTO_PRIME={self.av_delay_frames} (lips would be off by the difference)", flush=True)
        self.gc = None
        if E("DITTO_GESTURES") == "1":
            try:
                import gesture_client
                self.gc = gesture_client.GestureClient(self.url)
            except Exception as e:
                print(f"[ditto] gestures unavailable: {type(e).__name__}: {e}", flush=True)
        print(f"[ditto] renderer ready: {self.chunk_frames} frames / {self.chunk_samples} samples per chunk, {json.dumps(self.info)}", flush=True)

    def render(self, audio):
        a = np.asarray(audio, np.float32)
        if len(a) != self.chunk_samples: a = np.pad(a, (0, max(0, self.chunk_samples - len(a))))[:self.chunk_samples]
        if self.gc is not None:
            try: self.gc.on_chunk()
            except Exception as e: print(f"[ditto] gesture hook failed: {e}", flush=True)
        try:
            req = urllib.request.Request(self.url + "/render", data=a.tobytes(), headers={"Content-Type": "application/octet-stream"})
            with urllib.request.urlopen(req, timeout=self.timeout) as r: meta = json.loads(r.read())
            v = np.load(meta["path"])
            out = [v[i] for i in range(v.shape[0])]; self._last = out[-1]; return out
        except Exception as e:
            # a late/failed chunk must not stop the clock: hold the last frame (counted by the shim as padding)
            self.errors += 1
            if self.errors <= 5: print(f"[ditto] render failed ({type(e).__name__}: {e}) -- holding the last frame", flush=True)
            if self._last is None: raise
            return [self._last] * self.chunk_frames
