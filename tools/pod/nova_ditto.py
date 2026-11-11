#!/usr/bin/env python3
"""nova_ditto.py -- Nova's Ditto face path, behind NOVA_FACE=ditto. Lives on the pod at
/workspace/nova_ditto.py (installed by tools/pod/ditto_bridge_patch.py, tracked here).

WHAT IT IS
  A sidecar that turns Nova's reply audio into FRAMES, by driving the Ditto server
  (maya-lt lane/motion-transfer: maya-ops/lt/ditto_server.py, started by ditto_up.sh on
  127.0.0.1:8031). Ditto repaints only her lips on top of a pre-made body video; the body,
  hands, hair and eyes stay her own footage.

WHO CALLS IT
  rt_lk.py      feed(pcm16_24k)  -- every chunk of assistant audio, as it is produced
  lk_bridge.py  next_frame()     -- the publish loop takes its frames from here instead of
                                   the MuseTalk video queue (see ditto_bridge_patch.py)

THE CONTRACT (release/NOVA-TO-DITTO.md in dsbeauty01-web/maya-lt @ lane/motion-transfer,
verified against maya-ops/lt/ditto_server.py in this session)
  * POST /render, body = float32 mono 16 kHz, EXACTLY chunk_samples long (16000 = 1 s).
    Reply {"path": "/dev/shm/*.npy", "n": 25, "h", "w"} -- 25 BGR uint8 frames, whole picture.
  * Send SILENCE while she is quiet or the body freezes: the stream never stops.
  * Every frame returned is DITTO_PRIME frames (40 ms each) behind the audio just fed, and
    the delay is CONSTANT -- so the audio must be delayed by PRIME x 40 ms to keep lips locked.
    PRIME=35 -> 1400 ms (profiles/live_trio_nova.json ships SHIM_AV_OFFSET_MS=-1400).
  * GET /health until {"ready": true}.
  * POST /gesture {"clip"|"action"|"cue", "hold_s"} -- ONLY works when the server was started
    with DITTO_BANK=<bank.json> (motion_bank.py). Without a bank it answers
    {"ok": false, "why": "no motion bank (DITTO_BANK unset)"} -- see gesture() below.

NOVA LAWS honoured here
  * no silent fallbacks: a held frame is counted and logged; a frozen stretch over
    NOVA_DITTO_FREEZE_ALARM_S raises a loud [DITTO][ALARM] line and sets .alarm, which the
    page/grader can read through /workspace/gallery/wd/ditto_stats.json.
  * clock law: frames are paced off a monotonic clock at a fixed 25 fps, never off wall time.

Env
  NOVA_FACE               musetalk (default) | ditto      -- nothing here runs unless 'ditto'
  DITTO_PORT              8031
  DITTO_PRIME             35      frames of audio delay (x40 ms)
  DITTO_CHUNK             25      frames per /render call (chunk_samples = CHUNK*640)
  DITTO_TIMEOUT_SEC       2.5     per /render call
  NOVA_DITTO_FREEZE_ALARM_S  2.0  a held picture longer than this is an alarm
  NOVA_DITTO_WD           /workspace/gallery/wd   where ditto_stats.json / ditto.log go
  NOVA_DITTO_TIMELINE     1       (2026-11-10) wall-clock audio timeline + slot clock, see TIMELINE below.
                                  0 = the legacy pump (kept for an A/B; measured 44 fps pop rate and
                                  lips ~2.8 s behind her voice in the 2026-11-02 live takes).
  NOVA_DITTO_JITTER_MS    100     how late a 20 ms audio frame may arrive and still be "on time"
  NOVA_DITTO_RENDER_ALLOW_MS 600  time budget for one /render before its frames are due on screen

TIMELINE (2026-11-10, session nova-take8) -- why, with the measurement
  The legacy pump took "whatever audio is in the buffer" each time the frame queue ran low,
  put it at the START of a 1 s chunk and padded the rest with zeros. So a word was drawn up to
  1 s away from where it was spoken, differently for every sentence, and the publish clock had
  no lock: two callers each advanced it (5000 frames popped in ~112 s = 44 fps,
  docs/nova-ditto/ditto-live/logs/ditto_stats.take1.json). Measured on the live recordings with
  tools/qa/lip_proof.py: lip/audio correlation 0.19 and -0.14 inside the Maya gate's lag window,
  best lag +69 frames (2.76 s) on take 0 -- docs/nova-ditto/take8/.
  Now: audio is written on a WALL-CLOCK timeline (a gap in her speech becomes exactly that much
  silence), chunk k is second [k, k+1) of that timeline and is rendered once it has fully
  arrived, and frame j of the stream is shown in slot j of a fixed 25 fps clock that starts
  LEAD after the timeline does. Any number of callers get the frame of the current slot; a slow
  caller skips frames instead of drifting. The A/V offset is therefore ONE number:
      av_delay_ms = chunk (1000) + jitter (100) + render allowance (600) + PRIME x 40 (1400) = 3100
  It is longer than the old 1800 because 1800 was never achievable from a real-time feed: a 1 s
  chunk cannot be rendered before its last sample exists.
  QUESTION for the founder: 3.1 s of delay on a live reply, against lips that are not locked.
  [CLI-FILL] jitter 100 ms and render allowance 600 ms are this session's choices (the live
  render p50 was 514 ms WITH MuseTalk on the same GPU; DITTO-TRY measured ~250 ms alone). The
  two knobs that shorten the total are DITTO_PRIME and feeding Ditto from rt_lk.py, where
  OpenAI's audio arrives faster than real time. NOT PROVEN ON A POD -- self-test only.

Self-test (no GPU, no Ditto, no network beyond localhost):
  python3 nova_ditto.py --selftest
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import deque

import numpy as np
try:
    import cv2 as _cv2
except Exception:          # the selftest box may not have it; the pod's bridge env does (job4 stage 5: cv2 OK)
    _cv2 = None

E = os.environ.get

SR_IN = 24000          # OpenAI Realtime pcm16 output rate (pod/rt_lk.py: "format": {"type": "audio/pcm", "rate": 24000})
SR_OUT = 16000         # what Ditto wants
FPS = 25
MS_PER_FRAME = 1000.0 / FPS      # 40.0


def _wd() -> str:
    d = E("NOVA_DITTO_WD", "/workspace/gallery/wd")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        d = "/tmp"
    return d


def _log(msg: str) -> None:
    line = f"[DITTO {time.strftime('%H:%M:%S', time.gmtime())}] {msg}"
    print(line, flush=True)
    try:
        with open(os.path.join(_wd(), "ditto.log"), "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def enabled() -> bool:
    """The flag. NOVA_FACE=musetalk (or unset) must leave every caller byte-identical."""
    return (E("NOVA_FACE", "musetalk") or "musetalk").strip().lower() == "ditto"


# ---------------------------------------------------------------- resampling

def pcm16_24k_to_f32_16k(buf: bytes, carry: np.ndarray | None = None):
    """pcm16 mono @24 kHz -> float32 mono @16 kHz, ratio exactly 2/3.

    Anti-alias first (24k -> 16k decimates, so everything above 8 kHz must go), then
    linear interpolation on the sample grid. The anti-alias is a 3-tap moving average,
    which is -3 dB at ~5.5 kHz and >-12 dB by 8 kHz: crude but correct in direction, and
    Ditto drives HuBERT, which is trained on telephone-grade speech.
    `carry` is the tail of the previous call (2 samples), so chunk joins do not click.

    Returns (float32 samples @16 kHz, new carry).
    """
    x = np.frombuffer(buf, dtype="<i2").astype(np.float32) / 32768.0
    if carry is not None and len(carry):
        x = np.concatenate([carry, x])
        lead = len(carry)
    else:
        lead = 0
    if len(x) < 4:
        return np.zeros(0, np.float32), x.copy()
    k = np.ones(3, np.float32) / 3.0
    xs = np.convolve(x, k, mode="same")
    # output grid: n_out samples spaced 1.5 input samples apart, starting past the lead-in
    n_out = int((len(xs) - lead - 1) * SR_OUT / SR_IN)
    if n_out <= 0:
        return np.zeros(0, np.float32), x[-2:].copy()
    pos = lead + np.arange(n_out, dtype=np.float64) * (SR_IN / SR_OUT)
    i0 = np.floor(pos).astype(np.intp)
    frac = (pos - i0).astype(np.float32)
    i1 = np.minimum(i0 + 1, len(xs) - 1)
    y = (xs[i0] * (1.0 - frac) + xs[i1] * frac).astype(np.float32)
    return y, x[-2:].copy()


# ---------------------------------------------------------------- the face

class DittoFace:
    """Audio in, frames out. One instance per process; use get() to reach it."""

    def __init__(self, port: int | None = None):
        self.url = f"http://127.0.0.1:{port or E('DITTO_PORT', '8031')}"
        self.prime = int(E("DITTO_PRIME", "35"))
        self.chunk_frames = int(E("DITTO_CHUNK", "25"))
        self.chunk_samples = self.chunk_frames * 640          # 25 * 640 = 16000
        self.timeout = float(E("DITTO_TIMEOUT_SEC", "2.5"))
        self.freeze_alarm_s = float(E("NOVA_DITTO_FREEZE_ALARM_S", "2.0"))

        self._abuf = np.zeros(0, np.float32)                  # 16 kHz float32 waiting to be sent
        self._carry: np.ndarray | None = None
        self._alock = threading.Lock()

        self._frames: deque = deque()                         # BGR uint8 frames waiting to be published
        self._flock = threading.Condition()
        self._last = None                                     # last frame published (held on starvation)

        self.ready = False
        self.started = False
        self.alarm: str | None = None
        self.stats = {"chunks": 0, "frames": 0, "held": 0, "longest_hold_s": 0.0, "errors": 0,
                      "silence_chunks": 0, "speech_chunks": 0, "render_ms_p50": 0.0, "render_ms_p95": 0.0,
                      "gestures": 0, "gesture_refused": 0}
        self._ms: deque = deque(maxlen=500)
        self._t_next = None                                   # monotonic due-time of the next frame
        self._hold_since = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        # SLACK -- the frames the publisher waits for before it starts its 25 fps clock.
        # Ditto hands back frames in BURSTS of 25 (one per /render); the publisher drains
        # them one per 40 ms. Slack is the cushion that keeps it from starving between
        # bursts. It is paid ONCE, at the first frame, as a CONSTANT extra picture delay --
        # so the audio must be delayed by (PRIME + SLACK) frames, not PRIME alone, or the
        # lips sit SLACK x 40 ms early. 10 frames = 400 ms.
        self.slack = int(E("NOVA_DITTO_SLACK", "10"))
        self._warm = False
        self.av_delay_ms = (self.prime + self.slack) * MS_PER_FRAME   # (35+10)*40 = 1800.0

        # TIMELINE mode (default) -- see the module docstring.
        self.timeline = E("NOVA_DITTO_TIMELINE", "1") != "0"
        self.jitter_ms = float(E("NOVA_DITTO_JITTER_MS", "100"))
        self.render_allow_ms = float(E("NOVA_DITTO_RENDER_ALLOW_MS", "600"))
        self._epoch: float | None = None                      # monotonic time of timeline sample 0
        self._w = 0                                           # samples written to the timeline
        self._c = 0                                           # samples consumed (sent to Ditto)
        self._cur = None                                      # frame of the current slot
        self._last_slot = -1
        self.stats.update({"skipped": 0, "late_frames": 0, "gap_pads": 0, "tail_pads": 0})
        if self.timeline:
            self.av_delay_ms = self._tl_delay_ms()

    def _tl_lead_ms(self) -> float:
        """Timeline start -> first frame on screen: the chunk must fully arrive, then render."""
        return self.chunk_frames * MS_PER_FRAME + self.jitter_ms + self.render_allow_ms

    def _tl_delay_ms(self) -> float:
        return self._tl_lead_ms() + self.prime * MS_PER_FRAME

    # -- lifecycle ------------------------------------------------------

    def health(self) -> dict | None:
        try:
            with urllib.request.urlopen(self.url + "/health", timeout=2.0) as r:
                return json.loads(r.read())
        except Exception:
            return None

    def wait_ready(self, timeout_s: float | None = None) -> bool:
        """Poll /health until ready. ditto_up.sh is NOT started from here: it is a 5-15 min
        install and belongs in the pod's boot, not in a live request path."""
        t_end = time.time() + float(timeout_s if timeout_s is not None else E("DITTO_WAIT_SEC", "1500"))
        last = None
        while time.time() < t_end:
            h = self.health()
            if h and h.get("ready"):
                self.ready = True
                # the server is the authority on chunk size and prime -- adopt what it reports
                self.chunk_frames = int(h.get("chunk_frames", self.chunk_frames))
                self.chunk_samples = int(h.get("chunk_samples", self.chunk_samples))
                srv_prime = int(h.get("prime", self.prime))
                if srv_prime != self.prime:
                    _log(f"prime: server says {srv_prime}, env said {self.prime} -- using the server's")
                    self.prime = srv_prime
                self.av_delay_ms = (self._tl_delay_ms() if self.timeline
                                    else (self.prime + self.slack) * MS_PER_FRAME)
                _log(f"ready: chunk {self.chunk_frames}f/{self.chunk_samples}smp prime {self.prime} "
                     f"({self.av_delay_ms:.0f} ms audio delay) info={json.dumps(h.get('info'))}")
                return True
            if h and h.get("error"):
                if h["error"] != last:
                    _log(f"server error: {h['error']}")
                    last = h["error"]
            time.sleep(2.0)
        _log("NOT READY -- ditto server never answered ready")
        return False

    def start(self) -> None:
        if self.started:
            return
        self.started = True
        self._thread = threading.Thread(target=self._pump, name="ditto-pump", daemon=True)
        self._thread.start()
        _log("pump started")

    def stop(self) -> None:
        self._stop.set()

    # -- audio in -------------------------------------------------------

    def feed(self, pcm16_24k: bytes) -> None:
        """Every chunk of her reply audio, as rt_lk produces it. Safe to call from any thread."""
        if not pcm16_24k:
            return
        y, self._carry = pcm16_24k_to_f32_16k(pcm16_24k, self._carry)
        if len(y):
            self._append(y)

    def _append(self, y: np.ndarray) -> None:
        """Legacy: just queue it. Timeline: these samples END now, so if the timeline's write
        head is more than the jitter allowance behind, the difference was SILENCE -- write it,
        so the words land where they were spoken. Audio that arrives faster than real time
        (rt_lk's feed) is simply queued ahead; nothing is ever dropped."""
        with self._alock:
            if self.timeline and self._epoch is not None:
                start = int((time.monotonic() - self._epoch) * SR_OUT) - len(y)
                if self._w < start - int(self.jitter_ms * SR_OUT / 1000.0):
                    pad = start - self._w
                    self._abuf = np.concatenate([self._abuf, np.zeros(pad, np.float32)])
                    self._w += pad
                    self.stats["gap_pads"] += 1
            self._abuf = np.concatenate([self._abuf, y])
            self._w += len(y)

    def feed_pcm16_16k(self, pcm) -> None:
        """Her voice as the ENGINE already produced it: pcm16 mono 16 kHz.

        WHY THIS EXISTS (2026-11-02, session novaditto-final). The old wiring fed Ditto from
        rt_lk.py and published frames from lk_bridge.py -- TWO PROCESSES, therefore two
        DittoFace instances. The one that was fed never published and the one that published
        was never fed, so it posted nothing but silence to the server while both pumps fought
        over the same stateful body video.

        lk_bridge.py already receives her voice on the engine socket's 'A' channel at exactly
        AUDIO_SR = 16000, which is exactly what Ditto wants. So the face is now fed THERE, in
        the same process that publishes, and the publish path is untouched: this method only
        READS the samples. That is the contract ditto_renderer.py states -- the renderer never
        consumes the audio, it is only offset.
        """
        a = np.asarray(pcm, dtype=np.int16)
        if not a.size:
            return
        y = a.astype(np.float32) / 32768.0
        self._append(y)

    def _take_chunk(self) -> tuple[np.ndarray, bool]:
        """Exactly chunk_samples. Returns (audio, is_speech). When she is quiet this returns
        SILENCE, which is the point: the contract says send silence or the body freezes."""
        with self._alock:
            if len(self._abuf) >= self.chunk_samples:
                a = self._abuf[:self.chunk_samples]
                self._abuf = self._abuf[self.chunk_samples:]
                return a, True
            if len(self._abuf) > 0:
                # a partial tail: send it padded, so the last syllable is not swallowed
                a = np.zeros(self.chunk_samples, np.float32)
                a[:len(self._abuf)] = self._abuf
                self._abuf = np.zeros(0, np.float32)
                return a, True
        return np.zeros(self.chunk_samples, np.float32), False

    def _take_chunk_tl(self):
        """Timeline mode. Chunk k is timeline samples [k*N, (k+1)*N). It is handed out when it
        has fully arrived, or when the wall clock says its time is over (+ jitter) -- then the
        missing tail really was silence. Returns None while the chunk is still being spoken:
        a word is never cut in half and padded."""
        N = self.chunk_samples
        with self._alock:
            if self._epoch is None:
                self._epoch = time.monotonic()
                self._w = len(self._abuf)                     # anything fed before the start
                self._c = 0
                _log(f"timeline started -- frames go on screen {self._tl_lead_ms():.0f} ms later; "
                     f"audio must be delayed {self.av_delay_ms:.0f} ms")
            if len(self._abuf) >= N:
                a = self._abuf[:N]
                self._abuf = self._abuf[N:]
                self._c += N
                return a, bool(np.abs(a).max() > 1e-4)
            now_pos = int((time.monotonic() - self._epoch) * SR_OUT)
            if now_pos >= self._c + N + int(self.jitter_ms * SR_OUT / 1000.0):
                a = np.zeros(N, np.float32)
                k = len(self._abuf)
                a[:k] = self._abuf
                self._abuf = np.zeros(0, np.float32)
                self._c += N
                self._w = self._c
                speech = bool(k and np.abs(a).max() > 1e-4)
                if speech:
                    self.stats["tail_pads"] += 1
                return a, speech
        return None

    # -- the pump -------------------------------------------------------

    def _pump(self) -> None:
        """One /render per second of wall time, forever. Never stops: silence keeps the body alive."""
        while not self._stop.is_set():
            if not self.ready:
                time.sleep(0.5)
                continue
            # Stay only just ahead of the publisher. Every frame queued here is a frame of
            # ALREADY-RENDERED SILENCE that her next word has to wait behind, so a deep queue
            # is latency, not safety: chunk_frames + 5 = 1.2 s, under the 1.4 s the audio is
            # delayed by anyway. (Measured in the self-test: a 3-chunk lead swallowed the
            # first speech chunk entirely.)
            if self.timeline:
                got = self._take_chunk_tl()
                if got is None:
                    time.sleep(0.005)
                    continue
                audio, speech = got
                base = (self._c // self.chunk_samples - 1) * self.chunk_frames   # stream index of this chunk's frame 0
                self._tl_trim()
            else:
                with self._flock:
                    queued = len(self._frames)
                if queued >= self.chunk_frames + self.slack:
                    time.sleep(0.02)
                    continue
                audio, speech = self._take_chunk()
            t0 = time.time()
            try:
                req = urllib.request.Request(self.url + "/render", data=audio.tobytes(),
                                             headers={"Content-Type": "application/octet-stream"})
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    meta = json.loads(r.read())
                v = np.load(meta["path"])
                frames = [v[i] for i in range(v.shape[0])]
            except Exception as e:
                self.stats["errors"] += 1
                if self.stats["errors"] <= 10:
                    _log(f"render failed ({type(e).__name__}: {e}) -- the publisher will hold the last frame")
                time.sleep(0.1)
                continue
            self._ms.append((time.time() - t0) * 1000.0)
            self.stats["chunks"] += 1
            self.stats["speech_chunks" if speech else "silence_chunks"] += 1
            with self._flock:
                if self.timeline:
                    self._frames.extend((base + i, f) for i, f in enumerate(frames))
                else:
                    self._frames.extend(frames)
                self._flock.notify_all()
            self._write_stats()

    # -- timeline: the slot clock ---------------------------------------

    def _tl_slot(self, now: float) -> int:
        t0 = self._epoch + self._tl_lead_ms() / 1000.0
        return int((now - t0) // (MS_PER_FRAME / 1000.0))

    def _tl_trim(self) -> None:
        """Nobody publishing? Frames whose slot passed 2 s ago are dropped so memory stays bounded."""
        s = self._tl_slot(time.monotonic()) - 2 * FPS
        with self._flock:
            while self._frames and self._frames[0][0] < s:
                self._frames.popleft()

    def _next_tl(self, block_s: float):
        """The frame of the NEXT 40 ms slot, for any number of callers. Sleeps to the slot's
        start (never longer than one slot), then returns the newest frame whose slot has come.
        A caller that is slow skips frames; nobody can make the clock run fast."""
        if self._epoch is None:
            time.sleep(min(block_s, MS_PER_FRAME / 1000.0))
            return None
        dt = MS_PER_FRAME / 1000.0
        t0 = self._epoch + self._tl_lead_ms() / 1000.0
        now = time.monotonic()
        s = int((now - t0) // dt) + 1
        wait = t0 + s * dt - now
        if wait > 0:
            time.sleep(wait)
        if s < 0:
            return None
        with self._flock:
            popped = 0
            late = 0
            while self._frames and self._frames[0][0] <= s:
                idx, f = self._frames.popleft()
                popped += 1
                if idx < s:
                    late += 1
                self._cur = f
            first_call_of_slot = s > self._last_slot
            if first_call_of_slot:
                self._last_slot = s
            if popped:
                self.stats["frames"] += 1
                self.stats["skipped"] += popped - 1
                self.stats["late_frames"] += late
                if self._hold_since is not None:
                    held = time.monotonic() - self._hold_since
                    self.stats["longest_hold_s"] = round(max(self.stats["longest_hold_s"], held), 2)
                    self._hold_since = None
                return self._cur
            if self._cur is None or not first_call_of_slot:
                return self._cur
            self.stats["held"] += 1
            if self._hold_since is None:
                self._hold_since = time.monotonic()
            held = time.monotonic() - self._hold_since
            if held > self.freeze_alarm_s and self.alarm is None:
                self.alarm = f"picture held {held:.1f}s (> {self.freeze_alarm_s}s)"
                _log(f"[ALARM] {self.alarm} -- Ditto is not keeping up; this is a visible freeze")
            return self._cur

    # -- frames out -----------------------------------------------------

    def next_frame_bgr(self, block_s: float = 0.2):
        """One BGR frame, paced at 25 fps off a monotonic clock (clock law).
        Returns the last frame again if Ditto is starving -- counted and alarmed, never silent."""
        if self.timeline:
            return self._next_tl(block_s)
        # warm-up: hold the clock until SLACK frames are banked. The publish clock is pinned
        # here, once, and every later frame is exactly 40 ms after the one before it -- that
        # is what makes the A/V offset constant and therefore correctable.
        if not self._warm:
            with self._flock:
                if len(self._frames) < self.slack:
                    self._flock.wait(block_s)
                    if len(self._frames) < self.slack:
                        return None
                self._warm = True
            _log(f"publish clock started with {self.slack} frames of slack -- "
                 f"audio must be delayed {self.av_delay_ms:.0f} ms "
                 f"(prime {self.prime} + slack {self.slack}) x 40 ms")
        now = time.monotonic()
        if self._t_next is None:
            self._t_next = now
        wait = self._t_next - now
        if wait > 0:
            time.sleep(min(wait, block_s))
        self._t_next += MS_PER_FRAME / 1000.0
        if self._t_next < time.monotonic() - 0.5:      # we fell far behind: re-anchor, do not spin
            self._t_next = time.monotonic()
        with self._flock:
            if self._frames:
                f = self._frames.popleft()
                self._last = f
                self.stats["frames"] += 1
                if self._hold_since is not None:
                    held = time.monotonic() - self._hold_since
                    self.stats["longest_hold_s"] = round(max(self.stats["longest_hold_s"], held), 2)
                    self._hold_since = None
                return f
        # starved
        if self._last is None:
            return None
        self.stats["held"] += 1
        if self._hold_since is None:
            self._hold_since = time.monotonic()
        held = time.monotonic() - self._hold_since
        if held > self.freeze_alarm_s and self.alarm is None:
            self.alarm = f"picture held {held:.1f}s (> {self.freeze_alarm_s}s)"
            _log(f"[ALARM] {self.alarm} -- Ditto is not keeping up; this is a visible freeze")
        return self._last

    @staticmethod
    def bgr_to_rgba(f) -> tuple[int, int, bytes]:
        """lk_bridge publishes RGBA. Ditto hands back BGR uint8 (h, w, 3)."""
        h, w = f.shape[:2]
        if _cv2 is not None:      # 2026-11-11 nova-take8c: one native call, releases the GIL (the bridge is one asyncio thread)
            return w, h, _cv2.cvtColor(f, _cv2.COLOR_BGR2RGBA).tobytes()
        out = np.empty((h, w, 4), np.uint8)
        out[:, :, 0] = f[:, :, 2]
        out[:, :, 1] = f[:, :, 1]
        out[:, :, 2] = f[:, :, 0]
        out[:, :, 3] = 255
        return w, h, out.tobytes()

    def next_frame_rgba(self):
        """(w, h, rgba_bytes) -- exactly what lk_bridge's publish loop expects. None while warming."""
        f = self.next_frame_bgr()
        if f is None:
            return None
        return self.bgr_to_rgba(f)

    # -- gestures -------------------------------------------------------

    def gesture(self, name: str, hold_s: float = 3.0) -> dict:
        """POST /gesture. Only answers ok when the server runs with DITTO_BANK=<bank.json>
        (maya-ops/lt/motion_bank.py). Nova's bank (maya-lt assets/live_motion/nova/nova_bank.json)
        has: wave, nod/laugh, point, hold_up/show_closer, open/show_inside, demo, zoom.
        [TODO] There is NO freeze-cue clip in that bank -- see docs/NOVA-DITTO.md."""
        body = json.dumps({"clip": name, "action": name, "cue": name, "hold_s": hold_s}).encode()
        try:
            req = urllib.request.Request(self.url + "/gesture", data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=2.0) as r:
                out = json.loads(r.read())
        except Exception as e:
            self.stats["gesture_refused"] += 1
            out = {"ok": False, "why": f"{type(e).__name__}: {e}"}
        if out.get("ok"):
            self.stats["gestures"] += 1
        else:
            self.stats["gesture_refused"] += 1
            _log(f"gesture {name!r} refused: {out.get('why')}")
        return out

    # -- evidence -------------------------------------------------------

    def _write_stats(self) -> None:
        ms = sorted(self._ms) or [0.0]
        self.stats["render_ms_p50"] = round(ms[len(ms) // 2], 1)
        self.stats["render_ms_p95"] = round(ms[int(0.95 * (len(ms) - 1))], 1)
        with self._flock:
            self.stats["queued_frames"] = len(self._frames)
        self.stats["alarm"] = self.alarm
        self.stats["prime"] = self.prime
        self.stats["slack"] = self.slack
        self.stats["av_delay_ms"] = self.av_delay_ms
        self.stats["timeline"] = self.timeline
        try:
            with open(os.path.join(_wd(), "ditto_stats.json"), "w") as f:
                json.dump(self.stats, f, indent=1)
        except Exception:
            pass


_FACE: DittoFace | None = None
_GET_LOCK = threading.Lock()


def get() -> DittoFace:
    """The one instance. Callers do: nova_ditto.get().feed(pcm) / .next_frame_rgba()."""
    global _FACE
    with _GET_LOCK:
        if _FACE is None:
            _FACE = DittoFace()
        return _FACE


def boot(wait: bool = True) -> DittoFace:
    """Wait for the server, then start the pump. Call once, from whichever process starts first."""
    f = get()
    if wait and not f.ready:
        f.wait_ready()
    f.start()
    return f


# ---------------------------------------------------------------- self-test

def _selftest() -> int:
    """No GPU, no Ditto: a fake server on a free port answers /render with 25 grey frames."""
    import http.server
    import socket
    import tempfile

    tmp = tempfile.mkdtemp(prefix="novaditto_selftest_")
    os.environ["NOVA_DITTO_WD"] = tmp
    W, H, N = 64, 96, 25
    seen = {"chunks": 0, "sizes": set(), "gesture": 0}

    class Fake(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _j(self, code, obj):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            self._j(200, {"ready": True, "chunk_frames": N, "chunk_samples": N * 640,
                          "fps": 25, "prime": 35, "info": {"src": "fake.mp4"}})

        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(n)
            if self.path.startswith("/gesture"):
                seen["gesture"] += 1
                return self._j(200, {"ok": False, "why": "no motion bank (DITTO_BANK unset)"})
            a = np.frombuffer(raw, np.float32)
            seen["chunks"] += 1
            seen["sizes"].add(len(a))
            p = os.path.join(tmp, f"f{seen['chunks'] % 4}.npy")
            np.save(p, np.full((N, H, W, 3), seen["chunks"] % 256, np.uint8))
            self._j(200, {"path": p, "n": N, "h": H, "w": W})

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        print(f"  {'PASS' if cond else 'FAIL'}  {name} {extra}")
        ok = ok and bool(cond)

    os.environ["NOVA_DITTO_TIMELINE"] = "0"      # sections 1-6 test the LEGACY pump, as written
    print("nova_ditto self-test")
    # 1. the flag
    os.environ["NOVA_FACE"] = "musetalk"
    check("flag off by default", enabled() is False)
    os.environ["NOVA_FACE"] = "ditto"
    check("flag on with NOVA_FACE=ditto", enabled() is True)

    # 2. resampling: a 1 s 440 Hz tone at 24 kHz -> 16000 samples at 16 kHz
    t = np.arange(SR_IN, dtype=np.float32) / SR_IN
    tone = (np.sin(2 * np.pi * 440 * t) * 0.5 * 32767).astype("<i2").tobytes()
    y, carry = pcm16_24k_to_f32_16k(tone)
    check("resample 24k->16k length", abs(len(y) - SR_OUT) <= 4, f"got {len(y)}")
    check("resample keeps the tone", 0.2 < float(np.abs(y).max()) <= 1.0, f"peak {float(np.abs(y).max()):.3f}")
    # chunk joins must not click: feed the same tone in 0.2 s pieces
    f2 = DittoFace(port=port)
    step = SR_IN * 2 // 5
    for i in range(0, len(tone), step):
        f2.feed(tone[i:i + step])
    check("buffered ~1 s of 16k audio", abs(len(f2._abuf) - SR_OUT) <= 8, f"got {len(f2._abuf)}")
    # the bridge-side feed: pcm16 ALREADY at 16 kHz (lk_bridge's 'A' channel), no resampling
    f3 = DittoFace(port=port)
    t16 = np.arange(SR_OUT, dtype=np.float32) / SR_OUT
    pcm16 = (np.sin(2 * np.pi * 440 * t16) * 0.5 * 32767).astype("<i2")
    for i in range(0, len(pcm16), 320):               # 20 ms engine frames, as the bridge gets them
        f3.feed_pcm16_16k(pcm16[i:i + 320])
    check("feed_pcm16_16k buffers 16k pcm16 1:1", len(f3._abuf) == SR_OUT, f"got {len(f3._abuf)}")
    check("feed_pcm16_16k keeps the tone", 0.2 < float(np.abs(f3._abuf).max()) <= 1.0,
          f"peak {float(np.abs(f3._abuf).max()):.3f}")
    f3.feed_pcm16_16k(np.zeros(0, np.int16))
    check("feed_pcm16_16k ignores an empty frame", len(f3._abuf) == SR_OUT)

    # 3. the real loop against the fake server
    face = DittoFace(port=port)
    check("ready", face.wait_ready(timeout_s=10))
    check("prime adopted from server", face.prime == 35, f"prime {face.prime}")
    check("audio delay = (prime + slack) x 40 ms",
          abs(face.av_delay_ms - (35 + face.slack) * 40.0) < 1e-6, f"{face.av_delay_ms} ms")
    face.start()
    # a consumer, like lk_bridge's publish loop -- without one the queue fills and the pump
    # correctly stops, which is what made the first run of this test fail.
    drained = {"n": 0, "last": None}
    stop_consumer = threading.Event()

    def consume():
        while not stop_consumer.is_set():
            g = face.next_frame_rgba()
            if g is not None:
                drained["n"] += 1
                drained["last"] = g

    threading.Thread(target=consume, daemon=True).start()
    time.sleep(2.5)
    check("silence chunks sent while quiet", face.stats["silence_chunks"] > 0,
          f"{face.stats['silence_chunks']}")
    check("every chunk was exactly chunk_samples", seen["sizes"] == {N * 640}, f"{seen['sizes']}")
    n0 = face.stats["speech_chunks"]
    face.feed(tone)
    time.sleep(2.0)
    check("speech chunk sent after feed", face.stats["speech_chunks"] > n0,
          f"{face.stats['speech_chunks']}")
    with face._flock:
        qnow = len(face._frames)
    check("buffered picture stays bounded (<= chunk + slack + one burst)",
          qnow <= 2 * face.chunk_frames + face.slack, f"{qnow} frames")

    # 4. frames out, paced at 25 fps
    n1 = drained["n"]
    t0 = time.monotonic()
    while drained["n"] - n1 < 25 and time.monotonic() - t0 < 3.0:
        time.sleep(0.01)
    dt = time.monotonic() - t0
    stop_consumer.set()
    check("frames keep coming", drained["n"] - n1 >= 25, f"{drained['n'] - n1}")
    check("25 frames take ~1 s (25 fps)", 0.85 <= dt <= 1.25, f"{dt:.2f}s")
    check("no held frames while Ditto keeps up", face.stats["held"] == 0, f"held {face.stats['held']}")
    check("no freeze alarm", face.alarm is None, str(face.alarm))
    w, h, rgba = drained["last"]
    check("frame is RGBA at the source size", (w, h) == (W, H) and len(rgba) == W * H * 4,
          f"{w}x{h} {len(rgba)}B")
    bgr = np.full((2, 2, 3), 0, np.uint8)
    bgr[0, 0] = [1, 2, 3]                       # B=1 G=2 R=3
    _w, _h, px = DittoFace.bgr_to_rgba(bgr)
    check("BGR->RGBA channel order", tuple(np.frombuffer(px, np.uint8)[:4]) == (3, 2, 1, 255))

    # 5. gesture refusal is loud, not silent
    g = face.gesture("wave")
    check("gesture without a bank is refused and reported", g.get("ok") is False and seen["gesture"] == 1,
          str(g.get("why")))

    # 6. evidence file
    face._write_stats()
    sp = os.path.join(tmp, "ditto_stats.json")
    check("stats file written", os.path.exists(sp))
    if os.path.exists(sp):
        d = json.load(open(sp))
        check("stats carry prime, slack and av delay",
              d.get("prime") == 35 and d.get("slack") == face.slack
              and d.get("av_delay_ms") == (35 + face.slack) * 40.0, json.dumps(
                  {k: d.get(k) for k in ("prime", "slack", "av_delay_ms")}))

    face.stop()
    srv.shutdown()
    # 7. the A/V offset, measured -- legacy pump vs timeline (2026-11-10)
    for mode in ("0", "1"):
        r = _sync_sim(mode)
        name = "timeline" if mode == "1" else "legacy  "
        print(f"  ....  {name} A/V sim: offsets {r['offsets_ms']} ms, promised {r['promised_ms']:.0f}, "
              f"worst error {r['worst_err_ms']} ms, fps per caller {r['fps_per_caller']}, "
              f"popped/s {r['popped_per_s']}, held {r['held']}")
        if mode == "1":
            check("timeline: every word lands within 80 ms of the promised A/V offset",
                  r["n"] == 3 and r["edges"] == 3 and r["worst_err_ms"] is not None and r["worst_err_ms"] <= 80, f"{r['worst_err_ms']} ms")
            check("timeline: two callers each get ~25 fps, the clock does not run fast",
                  all(23.5 <= f <= 25.5 for f in r["fps_per_caller"]) and r["popped_per_s"] <= 25.5,
                  f"{r['fps_per_caller']} / {r['popped_per_s']}")
            check("timeline: no freeze alarm", r["alarm"] is None, str(r["alarm"]))
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def _sync_sim(timeline: str, render_s: float = 0.3) -> dict:
    """Measure the real A/V offset with a fake Ditto that behaves like the real one where it
    matters: it takes `render_s` per call and every frame it returns shows the loudness of the
    audio PRIME frames earlier (white = she is speaking). Three 0.5 s tones are fed in real time
    as 20 ms frames (the bridge's 'A' channel), at irregular moments; TWO consumers publish.
    offset = (first white frame on screen) - (first loud sample fed). It must equal av_delay_ms."""
    import http.server
    import socket
    import tempfile

    tmp = tempfile.mkdtemp(prefix="novaditto_sync_")
    os.environ["NOVA_DITTO_WD"] = tmp
    os.environ["NOVA_DITTO_TIMELINE"] = timeline
    N, PRIME = 25, 35
    loud: list = []
    lk = threading.Lock()

    class Fake(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _j(self, obj):
            b = json.dumps(obj).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            self._j({"ready": True, "chunk_frames": N, "chunk_samples": N * 640, "fps": 25, "prime": PRIME})

        def do_POST(self):
            a = np.frombuffer(self.rfile.read(int(self.headers.get("Content-Length", "0"))), np.float32)
            with lk:
                g0 = len(loud)
                loud.extend(float(np.abs(a[i * 640:(i + 1) * 640]).max()) for i in range(N))
                v = np.zeros((N, 4, 4, 3), np.uint8)
                for j in range(N):
                    k = g0 + j - PRIME
                    if k >= 0 and loud[k] > 0.1:
                        v[j] = 255
                p = os.path.join(tmp, f"s{(g0 // N) % 6}.npy")
            time.sleep(render_s)
            np.save(p, v)
            self._j({"path": p, "n": N, "h": 4, "w": 4})

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    face = DittoFace(port=port)
    face.wait_ready(timeout_s=10)
    face.start()
    stop = threading.Event()
    seen = [[], []]                                   # per consumer: (time, white?)
    uniq = [0, 0]
    counting = threading.Event()

    def consume(ci):
        last = None
        while not stop.is_set():
            f = face.next_frame_bgr()
            if f is None:
                continue
            seen[ci].append((time.monotonic(), bool(f[0, 0, 0] > 127)))
            if f is not last:
                if counting.is_set():
                    uniq[ci] += 1
                last = f

    for ci in (0, 1):
        threading.Thread(target=consume, args=(ci,), daemon=True).start()
    time.sleep(2.0)                                   # she is quiet first, as in a real session
    t_start = time.monotonic()
    f0 = face.stats["frames"]
    counting.set()
    tone =(np.sin(2 * np.pi * 220 * np.arange(8000) / 16000.0) * 0.5 * 32767).astype("<i2")
    onsets = []
    for at in (0.70, 2.35, 4.93):                     # irregular on purpose: not on a chunk edge
        while time.monotonic() - t_start < at:
            time.sleep(0.002)
        onsets.append(time.monotonic())
        t_u = time.monotonic()
        for i in range(0, 8000, 320):                 # 20 ms frames in real time
            face.feed_pcm16_16k(tone[i:i + 320])
            t_u += 0.02
            time.sleep(max(0.0, t_u - time.monotonic()))
    time.sleep(6.0)
    span = time.monotonic() - t_start
    stop.set()
    face.stop()
    srv.shutdown()
    offs = []
    ev = seen[0]
    edges = [t for (t, wh), (_, pw) in zip(ev[1:], ev[:-1]) if wh and not pw]   # each tone turning the frame white
    for t_on, t_ed in zip(onsets, edges):             # k-th tone fed <-> k-th tone seen
        offs.append(round((t_ed - t_on) * 1000))
    errs = [abs(o - face.av_delay_ms) for o in offs]
    return {"offsets_ms": offs, "n": len(offs), "promised_ms": face.av_delay_ms,
            "worst_err_ms": round(max(errs)) if errs else None,
            "fps_per_caller": [round(u / span, 1) for u in uniq],
            "popped_per_s": round((face.stats["frames"] - f0) / span, 1),
            "edges": len(edges), "held": face.stats["held"], "alarm": face.alarm}


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
