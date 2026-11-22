#!/usr/bin/env python3
"""tools/pod/nova_face.py — Nova's live SoulX face as the LiveKit participant `nova-face` (b0.27 FREEZE4).

What it is: an ENGINE for pod/rt_lk.py (same two calls the brain makes on LiveTalking today:
  POST /humanaudio  multipart "file" = wav 16 kHz mono — her voice, one line at a time (rt_lk feed_engine)
  GET  /set_avatar  no-op 200 (the brain calls it for gestures; a face has none)
) that renders her face with SoulX-FlashHead Lite and publishes, from ONE participant `nova-face`:
  · a video track  = her talking face (512x512, 25 fps)      → shared/face-panel.js shows it in the side panel
  · an audio track = the same voice samples the face was rendered from → shared/nova-bridge.js plays it
Face and voice leave in the same 40 ms step (frame k of a chunk + samples k*640..(k+1)*640), so they start in sync.

The renderer is Maya's, imported UNCHANGED from the image (ghcr.io/dsbeauty01-web/maya-lt:soulx-wide-v2,
/opt/maya-ops/lt/flashhead_renderer.py: render(15360 samples f32 @16 kHz) -> 24 BGR frames). No Maya file is copied
or edited. FACE_RENDERER=fake swaps in a CPU stand-in (the reference image + a mouth that opens with the audio) so
this file can be tested without a GPU — a fake run proves the plumbing only, never the lips.

Silence is rendered too (the model's own idle), so the face never freezes while she is quiet.
Latency: one chunk is 0.96 s. When speech arrives, a queued silence chunk that has not started is thrown away,
so her first word starts on the next chunk boundary (the measured arrival→publish delay is in GET /).

Env:  FACE_PORT 8010 · LIVEKIT_URL/LIVEKIT_API_KEY/LIVEKIT_API_SECRET · LK_ROOM (nova-freeze4) · FACE_IDENTITY (nova-face)
      FACE_IMG (tools/pod/assets/nova_face_ref.png) · FACE_RENDERER flashhead|fake · FACE_RENDERER_DIR (/opt/maya-ops/lt)
      FACE_OUT dir for stats/frames/recording (/root/out/face) · FACE_RECORD 1 = keep an mp4 of exactly what was published
      FACE_TEST_HOOKS 1 = POST /pause?s=N stops the video for N s (proof of the page's red banner; never on a tester pod)

NOVA-FINAL (2026-11-12, Refael's approved spec "the new skill and full switch to Ditto"): FACE_RENDERER=dual runs BOTH
faces in this one process, ONE AT A TIME (the other one renders nothing, so it never steals CPU/GPU from the live one):
  · mode "wide" = Ditto (tools/pod/ditto_take8/ditto_server.py on DITTO_URL) on her talk body in her room
    (tools/pod/assets/nova_talk_wide.mp4, Ditto Gold body gate PASS) -> video track `nova-wide-video`
    -- INTRO / ENDING ("before the music/game starts she talks WIDE")
  · mode "pip"  = SoulX-FlashHead (as before) -> video track `nova-face-video` -- the small in-game face (PiP, top-left)
  The voice track `nova-face-voice` carries whichever face is talking. GET /face_mode?m=wide|pip switches (pod/rt_lk.py
  calls it when the page's speak-gate changes: gate off = wide, gate on = pip). Default for FACE_RENDERER=flashhead|fake:
  unchanged (one face, mode "pip" only).
  Ditto returns every frame DITTO_PRIME frames behind the audio fed (a constant delay line, ditto-for-nova skill), so the
  voice published with a Ditto chunk is delayed by the same amount here: picture and sound leave together.
  Real time (Nova live 2026-11-11: 1.1-1.2 s per 1 s, FAIL): the render thread stays one chunk ahead of the publisher
  (pipelined, it never waits for a publish), the idle face is not rendered at all, and the wide frames are published at
  WIDE_W x WIDE_H (720x1280 default; the 1080 frames are what FACE_RECORD keeps for the gate).
"""
import asyncio, io, json, os, subprocess, sys, threading, time, wave, collections

import numpy as np
from aiohttp import web

E = os.environ.get
PORT = int(E("FACE_PORT", "8010"))
ROOM = E("LK_ROOM", "nova-freeze4")
IDENT = E("FACE_IDENTITY", "nova-face")
HERE = os.path.dirname(os.path.abspath(__file__))
FACE_IMG = E("FACE_IMG", os.path.join(HERE, "assets", "nova_face_ref.png"))
OUT = E("FACE_OUT", "/root/out/face")
FPS, SR, CHUNK = 25, 16000, 24                      # flashhead_renderer.py: 24 frames @25 fps = 0.96 s
SAMPLES = CHUNK * SR // FPS                         # 15360
STEP = SR // FPS                                    # 640 samples per frame (40 ms)
os.makedirs(OUT, exist_ok=True)


def log(*a):
    print(time.strftime("%H:%M:%S"), "[FACE]", *a, flush=True)


# ───────────────────────── renderers ─────────────────────────
class FakeRenderer:
    """CPU stand-in: the reference picture with a dark mouth whose height follows the audio level."""
    def __init__(self):
        import cv2
        self.cv2 = cv2
        im = cv2.imread(FACE_IMG)
        if im is None: raise RuntimeError("fake renderer: FACE_IMG missing: " + FACE_IMG)
        self.base = cv2.resize(im, (512, 512))

    def render(self, audio):
        out = []
        for k in range(CHUNK):
            a = audio[k * STEP:(k + 1) * STEP]
            lvl = float(np.sqrt(np.mean(a * a))) if len(a) else 0.0
            f = self.base.copy()
            h = int(min(40, lvl * 400))
            if h > 1: self.cv2.ellipse(f, (256, 372), (34, h), 0, 0, 360, (40, 20, 60), -1)
            out.append(f)
        return out


class DittoRenderer:
    """client of ditto_server.py: render(audio of self.samples) -> (frames BGR at the body's size, the voice delayed by prime)"""
    def __init__(self):
        import urllib.request
        self.U = urllib.request; self.url = E("DITTO_URL", "http://127.0.0.1:8031")
        t_end = time.time() + float(E("DITTO_WAIT_SEC", "900")); h = {}
        while time.time() < t_end:
            try:
                h = json.loads(self.U.urlopen(self.url + "/health", timeout=5).read())
                if h.get("ready"): break
                if h.get("error"): raise RuntimeError("ditto_server: " + str(h["error"])[:300])
            except RuntimeError: raise
            except Exception: pass
            time.sleep(2)
        if not h.get("ready"): raise RuntimeError("ditto_server not ready on " + self.url)
        self.chunk, self.samples, self.prime = int(h["chunk_frames"]), int(h["chunk_samples"]), int(h["prime"])
        self.delay = np.zeros(self.prime * STEP, np.float32)
        self.info = h.get("info", {}); log("ditto ready:", json.dumps({k: h.get(k) for k in ("chunk_frames", "prime")}), self.info.get("src"))

    def reset(self):
        self.delay = np.zeros(self.prime * STEP, np.float32)

    def render(self, audio):
        r = self.U.Request(self.url + "/render", data=np.ascontiguousarray(audio, np.float32).tobytes(), method="POST")
        m = json.loads(self.U.urlopen(r, timeout=30).read())
        if "path" not in m: raise RuntimeError("ditto render: " + str(m)[:200])
        frames = list(np.load(m["path"]))
        line = np.concatenate([self.delay, audio]); self.delay = line[len(audio):]
        return frames, line[:len(audio)]


class Dual:
    """the two faces, one active. mode 'wide' = Ditto, 'pip' = SoulX."""
    def __init__(self, soulx, ditto):
        self.r = {"pip": soulx, "wide": ditto}; self.mode = E("FACE_START_MODE", "wide")


def make_renderer():
    kind = E("FACE_RENDERER", "flashhead")
    if kind == "fake":
        return FakeRenderer()
    if kind == "dual":
        d = DittoRenderer()                                       # first: Ditto must be up before SoulX takes the GPU memory
        os.environ.setdefault("SHIM_FACE", FACE_IMG)
        sys.path.insert(0, E("FACE_RENDERER_DIR", "/opt/maya-ops/lt"))
        if E("FACE_PIP_RENDERER", "flashhead") == "fake": s_ = FakeRenderer()
        else:
            from flashhead_renderer import Renderer
            s_ = Renderer()
        return Dual(s_, d)
    os.environ.setdefault("SHIM_FACE", FACE_IMG)                  # flashhead_renderer reads SHIM_FACE
    sys.path.insert(0, E("FACE_RENDERER_DIR", "/opt/maya-ops/lt"))
    from flashhead_renderer import Renderer                       # Maya's file, unchanged
    return Renderer()


# ───────────────────────── state ─────────────────────────
S = {"ready": False, "room": False, "chunks": 0, "speech_chunks": 0, "underruns": 0, "frames": 0,
     "render_ms": collections.deque(maxlen=400), "arrive_to_publish_ms": [], "sharp": [], "lines": 0,
     "error": "", "t_start": time.time(), "paused_until": 0.0,
     "mode": "pip", "mode_switches": [], "wide_ms": collections.deque(maxlen=2000), "wide_late": 0, "wide_frames": 0}
WIDE_W, WIDE_H = int(E("WIDE_W", "720")), int(E("WIDE_H", "1280"))
DUAL = None                          # the Dual object when FACE_RENDERER=dual
lock = threading.Lock()
pending = collections.deque()        # [samples f32, t_arrival] — her voice waiting to be rendered
ready = collections.deque()          # rendered chunks waiting to be published
have_speech = threading.Event()


# NOVA-AUDIT 2026-11-22 · VOICE HOLES. Her live voice reaches us in 0.2 s pieces as it is spoken (pod/rt_lk.py FLUSH), the
# renderer takes 0.4 s (Ditto) / 0.96 s (SoulX) at a time, and a take that found only part of a chunk was padded with zeros —
# 8-9 holes of 0.16-0.2 s in every 8 s sentence (docs/NOVA-FINAL.md "OPEN — her live voice has small holes").
# FACE_VOICE_PREBUF_MS (default 0 = off, unchanged): at the START of a line, wait until one chunk + this much voice is queued
# (or the line has stopped arriving for FACE_VOICE_PREBUF_IDLE_MS, i.e. it is shorter than that), then speak from that cushion.
# Pieces keep arriving at speaking speed, so the cushion stays and a take mid-line finds a full chunk; only the END of a line is
# padded. Cost: her first word starts that much later. S["voice_holes"] counts what is left: a padded take followed by more of
# the same line within FACE_VOICE_HOLE_MS (= a hole the child hears).
PREBUF_MS = float(E("FACE_VOICE_PREBUF_MS", "0"))
PREBUF_IDLE_MS = float(E("FACE_VOICE_PREBUF_IDLE_MS", "300"))
HOLE_MS = float(E("FACE_VOICE_HOLE_MS", "600"))
VS = {"mid": False, "last_in": 0.0, "pad_at": None}
S.update({"voice_pads": 0, "voice_holes": 0, "voice_prebuf_waits": 0, "voice_lines": []})


def voice_arrived(t, n=0):
    """called by /humanaudio under the lock: counts a hole when a padded take is followed by more of her line, and how fast
    her voice ARRIVES per line (S["voice_lines"]: [audio s, arrival span s, pieces] — audio s > span s = faster than real time)."""
    if VS["pad_at"] is not None and t - VS["pad_at"] < HOLE_MS / 1000: S["voice_holes"] += 1
    ln = VS.get("line")
    if ln is None or t - VS["last_in"] > 1.0:
        if ln and ln[2] > 1: S["voice_lines"].append([round(ln[1] / SR, 2), round(VS["last_in"] - ln[0], 2), ln[2]]); del S["voice_lines"][:-12]
        VS["line"] = ln = [t, 0, 0]
    ln[1] += n; ln[2] += 1
    VS["pad_at"] = None; VS["last_in"] = t


def pending_take(n, now=None):
    """Take up to n samples of queued voice. Returns (audio, t_first_arrival or None)."""
    got, t0, need = [], None, n
    now = time.time() if now is None else now
    with lock:
        if PREBUF_MS > 0 and pending and not VS["mid"]:
            have = sum(len(a) for a, _ in pending)
            if have < n + int(PREBUF_MS * SR / 1000) and (now - VS["last_in"]) * 1000 < PREBUF_IDLE_MS:
                S["voice_prebuf_waits"] += 1
                return None, None                     # the line has started arriving: build the cushion first (silence meanwhile)
        while need and pending:
            a, t = pending[0]
            if t0 is None: t0 = t
            if len(a) <= need:
                got.append(a); need -= len(a); pending.popleft()
            else:
                got.append(a[:need]); pending[0] = [a[need:], t]; need = 0
        if not pending: have_speech.clear()
        if got and not need: VS["mid"] = True         # a full take: we are inside her line (until a padded take ends it)
        if got and need:                              # a padded take: the end of her line — or a hole if more follows
            S["voice_pads"] += 1; VS["pad_at"] = now; VS["mid"] = False
    if not got: return None, None
    a = np.concatenate(got)
    if len(a) < n: a = np.concatenate([a, np.zeros(n - len(a), np.float32)])
    return a, t0


def render_loop(R):
    import cv2
    global DUAL
    if isinstance(R, Dual):
        DUAL = R; S["mode"] = R.mode
        try:   # one real SoulX frame before the game, so the first moment of the PiP is her face, never a black tile (pod run #2)
            fr = R.r["pip"].render(np.zeros(getattr(R.r["pip"], "samples", SAMPLES), np.float32))
            S["pip_first"] = (fr[0] if isinstance(fr, tuple) else fr)[-1]
        except Exception as e: log("pip warm frame failed:", e)
    while True:
        mode = S["mode"] if DUAL else "pip"
        r = DUAL.r[mode] if DUAL else R
        n_s = getattr(r, "samples", SAMPLES); n_f = getattr(r, "chunk", CHUNK)
        # keep exactly one chunk ahead of the publisher; speech pre-empts a silence chunk that has not started.
        # Ditto is a stream (its body video and its delay line run on): its silence chunks are never thrown away.
        while True:
            with lock:
                n = len(ready)
                if n and mode == "pip" and have_speech.is_set() and not ready[-1]["speech"] and ready[-1]["mode"] == "pip":
                    ready.pop(); n -= 1
            if n == 0 or (DUAL and S["mode"] != mode): break
            have_speech.wait(0.01)
        if DUAL and S["mode"] != mode: continue
        audio, t_arr = pending_take(n_s)
        speech = audio is not None
        if not speech: audio = np.zeros(n_s, np.float32)
        t = time.time()
        try:
            out = r.render(audio)
        except Exception as e:
            S["error"] = "render: " + repr(e)[:300]; log("RENDER ERROR", e); time.sleep(0.2); continue
        if isinstance(out, tuple): frames, pub_audio = out          # Ditto: the voice that belongs to these frames
        else: frames, pub_audio = out, audio
        ms = (time.time() - t) * 1000
        (S["wide_ms"] if mode == "wide" else S["render_ms"]).append(ms)
        if mode == "wide" and ms > n_f * 40: S["wide_late"] += 1
        if speech:
            S["speech_chunks"] += 1
            if mode == "pip":
                g = cv2.cvtColor(frames[n_f // 2], cv2.COLOR_BGR2GRAY)
                S["sharp"].append(float(cv2.Laplacian(g[96:416, 96:416], cv2.CV_64F).var()))   # centre of the face
            if S["speech_chunks"] <= 3 or S["speech_chunks"] % 15 == 0:
                cv2.imwrite(os.path.join(OUT, f"published_{mode}_speech_{S['speech_chunks']:03d}.jpg"), frames[n_f // 2])
        with lock:
            ready.append({"frames": frames, "audio": pub_audio, "speech": speech, "t_arr": t_arr, "mode": mode, "n": n_f})
        S["chunks"] += 1


# ───────────────────────── LiveKit publisher ─────────────────────────
_REC_N = [0]
def _recorder(name, w, h, crf):
    _REC_N[0] += 1; vp = os.path.join(OUT, f"{name}_{_REC_N[0]}_video.mp4"); ap = os.path.join(OUT, f"{name}_{_REC_N[0]}_voice.wav")
    v = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "ultrafast", "-crf", str(crf),
                          "-pix_fmt", "yuv420p", vp], stdin=subprocess.PIPE)
    a = wave.open(ap, "wb"); a.setnchannels(1); a.setsampwidth(2); a.setframerate(SR)
    if REC_THREAD: return _RecWriter(v, a), a, vp, ap
    return v, a, vp, ap


# NOVA-AUDIT 2026-11-22 · FACE_REC_THREAD (default 0 = off, unchanged). With FACE_RECORD=1 (every proof pod) the publisher
# wrote each 1080x1920 frame (6.2 MB) into the recording's ffmpeg pipe INSIDE the 25 fps publish loop; when that encoder is
# slower than the loop the pipe blocks and the live picture/voice to the child stalls and then bursts. On: a writer thread
# with a bounded queue takes the frames; a full queue drops the RECORDING's frame (S["rec_dropped"]), never the live one.
REC_THREAD = E("FACE_REC_THREAD", "0") == "1"
# FACE_PUB_STEADY (default 0 = off, unchanged): the publisher used to catch up after a late chunk by sending up to 0.5 s of
# frames with no wait — a burst the browser shows as a stall then a jump, and a burst that pulls the next voice chunk early
# (a padded take = a voice hole). On: more than FACE_PUB_STEADY_MS (80 = 2 frames) behind -> re-anchor the clock instead.
PUB_STEADY = E("FACE_PUB_STEADY", "0") == "1"; PUB_STEADY_S = float(E("FACE_PUB_STEADY_MS", "80")) / 1000
S.update({"pub_late_frames": 0, "pub_max_lag_ms": 0, "pub_reanchors": 0})
S["rec_dropped"] = 0
class _RecWriter:
    """looks like the Popen the old code used: .stdin.write / .stdin.close / .wait — the voice wav is written with the frame."""
    def __init__(self, proc, wav):
        import queue
        self.p, self.w, self.q = proc, wav, queue.Queue(maxsize=int(E("FACE_REC_QUEUE", "50")))
        self.stdin = self; self.th = threading.Thread(target=self._run, daemon=True); self.th.start()
    def _run(self):
        while True:
            item = self.q.get()
            if item is None: break
            try: self.p.stdin.write(item[0]); self.w.writeframes(item[1])
            except Exception: pass
    def put(self, fb, ab):
        try: self.q.put_nowait((fb, ab))
        except Exception: S["rec_dropped"] += 1
    def write(self, b): pass                           # (the old direct path; unused when threaded)
    def close(self):
        self.q.put(None); self.th.join(60)
        try: self.p.stdin.close()
        except Exception: pass
    def wait(self, t=None): return self.p.wait(t)


async def publisher():
    from livekit import rtc, api
    import cv2
    tok = (api.AccessToken(E("LIVEKIT_API_KEY"), E("LIVEKIT_API_SECRET")).with_identity(IDENT).with_name("Nova face")
           .with_grants(api.VideoGrants(room_join=True, room=ROOM, can_publish=True, can_subscribe=False)).to_jwt())
    room = rtc.Room()
    await room.connect(E("LIVEKIT_URL"), tok)
    vsrc = rtc.VideoSource(512, 512)
    asrc = rtc.AudioSource(SR, 1)
    vtr = rtc.LocalVideoTrack.create_video_track("nova-face-video", vsrc)
    atr = rtc.LocalAudioTrack.create_audio_track("nova-face-voice", asrc)
    vo = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_CAMERA)
    try:   # the face is small and soft already; give WebRTC room so it does not soften it further (received/published was 0.72x)
        vo.video_encoding = rtc.VideoEncoding(max_framerate=FPS, max_bitrate=int(E("FACE_MAX_BITRATE", "3000000")))
    except Exception as e:
        log("video_encoding not set:", e)
    ao = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
    for o in (vo, ao):                               # same stream id = the browser lip-syncs the two tracks (if supported)
        try: o.stream = "nova-face"
        except Exception: pass
    await room.local_participant.publish_track(vtr, vo)
    wsrc = None
    if DUAL is not None or E("FACE_RENDERER") == "dual":         # NOVA-FINAL: her wide Ditto body, a second video track
        wsrc = rtc.VideoSource(WIDE_W, WIDE_H)
        wtr = rtc.LocalVideoTrack.create_video_track("nova-wide-video", wsrc)
        wo = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_SCREENSHARE)
        try: wo.video_encoding = rtc.VideoEncoding(max_framerate=FPS, max_bitrate=int(E("WIDE_MAX_BITRATE", "4000000")))
        except Exception as e: log("wide video_encoding not set:", e)
        try: wo.stream = "nova-face"
        except Exception: pass
        await room.local_participant.publish_track(wtr, wo)
    await room.local_participant.publish_track(atr, ao)
    S["room"] = True; log("LiveKit: published as", IDENT, "in room", ROOM, "(+ wide)" if wsrc else "")

    rec = S.setdefault("_rec", {})                    # recorders open lazily per face; POST /finish closes them (same dict)

    # FACE_VIDEO_DELAY_FRAMES (default 0): hold the face back N frames behind the voice. Do NOT set it: judged BY EYE on the
    # pod recordings (2026-11-11) the mouth already starts ~120-160 ms AFTER her voice with 0, and 3 frames made it later.
    # (The in-page mouth-motion probe said "133 ms before" — it counts head motion in silence; the frames say otherwise.)
    vdelay = int(E("FACE_VIDEO_DELAY_FRAMES", "0")); vq = collections.deque()
    log("video delay frames:", vdelay)
    loop = asyncio.get_event_loop()
    t0, i, last = loop.time(), 0, {"pip": None, "wide": None}
    while True:
        with lock:
            ch = ready.popleft() if ready else None
        if ch is None:                                  # renderer late: hold the last frame, silence — never a black frame
            S["underruns"] += 1
            m = S["mode"] if DUAL else "pip"; n = 4 if m == "wide" else CHUNK
            lf = last[m] if last[m] is not None else (S.get("pip_first", np.zeros((512, 512, 3), np.uint8)) if m == "pip" else None)
            if lf is None: await asyncio.sleep(0.04); t0 = loop.time() - i / FPS; continue
            ch = {"frames": [lf] * n, "audio": np.zeros(n * STEP, np.float32), "speech": False, "t_arr": None, "mode": m, "n": n}
        if ch["speech"] and ch["t_arr"] is not None:
            S["arrive_to_publish_ms"].append(round((time.time() - ch["t_arr"]) * 1000))
        pcm = (np.clip(ch["audio"], -1, 1) * 32767).astype(np.int16)
        mode = ch["mode"]
        if mode not in rec and E("FACE_RECORD", "0") == "1":
            h0, w0 = ch["frames"][0].shape[:2]
            rec[mode] = _recorder("wide_published" if mode == "wide" else "face_published", w0, h0, 14 if mode == "wide" else 24)
        for k in range(len(ch["frames"])):
            dt = t0 + i / FPS - loop.time()
            if dt > 0: await asyncio.sleep(dt)
            elif dt < -0.5: t0 = loop.time() - i / FPS             # we fell far behind (stall): re-anchor the clock
            elif PUB_STEADY and dt < -PUB_STEADY_S:                # NOVA-AUDIT: behind by > 2 frames -> re-anchor, never burst
                t0 = loop.time() - i / FPS; S["pub_reanchors"] += 1
            if dt < -0.02: S["pub_late_frames"] += 1; S["pub_max_lag_ms"] = max(S["pub_max_lag_ms"], round(-dt * 1000))
            f = ch["frames"][k]; last[mode] = f
            if mode == "pip" and vdelay:
                vq.append(f)
                f = vq.popleft() if len(vq) > vdelay else vq[0]
            if time.time() >= S["paused_until"]:
                if mode == "wide":
                    g = cv2.resize(f, (WIDE_W, WIDE_H), interpolation=cv2.INTER_AREA) if f.shape[1] != WIDE_W else f
                    wsrc.capture_frame(rtc.VideoFrame(WIDE_W, WIDE_H, rtc.VideoBufferType.RGBA,
                                                      cv2.cvtColor(g, cv2.COLOR_BGR2RGBA).tobytes()))
                    S["wide_frames"] += 1
                else:
                    rgba = np.dstack([f[:, :, ::-1], np.full(f.shape[:2], 255, np.uint8)])
                    vsrc.capture_frame(rtc.VideoFrame(512, 512, rtc.VideoBufferType.RGBA, rgba.tobytes()))
                    S["frames"] += 1
            seg = pcm[k * STEP:(k + 1) * STEP]
            await asrc.capture_frame(rtc.AudioFrame(seg.tobytes(), SR, 1, len(seg)))
            rv = rec.get(mode)
            if rv:
                if REC_THREAD: rv[0].put(f.tobytes(), seg.tobytes())
                else:
                    try: rv[0].stdin.write(f.tobytes()); rv[1].writeframes(seg.tobytes())
                    except Exception: pass
            i += 1


# ───────────────────────── HTTP (the engine API rt_lk already speaks) ─────────────────────────
def wav_to_f32(b):
    with wave.open(io.BytesIO(b), "rb") as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0 if sw == 2 else np.frombuffer(raw, np.uint8).astype(np.float32) / 128 - 1
    if ch > 1: a = a.reshape(-1, ch).mean(1)
    if sr != SR:
        x = np.linspace(0, len(a), int(len(a) * SR / sr), endpoint=False)
        a = np.interp(x, np.arange(len(a)), a).astype(np.float32)
    return a


async def humanaudio(req):
    t = time.time()
    data = await req.post()
    f = data.get("file")
    b = f.file.read() if hasattr(f, "file") else (f if isinstance(f, (bytes, bytearray)) else b"")
    try:
        a = wav_to_f32(b)
    except Exception as e:
        return web.json_response({"code": 1, "msg": "bad wav: " + str(e)})
    with lock:
        if not pending: S["lines"] += 1
        voice_arrived(t, len(a))
        pending.append([a, t])
    have_speech.set()
    return web.json_response({"code": 0, "data": len(a)})


async def set_avatar(req):
    return web.json_response({"code": 0, "data": "face has no gestures"})


async def interrupt(req):
    with lock: pending.clear()
    have_speech.clear()
    return web.json_response({"code": 0})


async def is_speaking(req):
    with lock: v = bool(pending)
    return web.json_response({"code": 0, "data": v})


def stats():
    r = sorted(S["render_ms"]); ap = sorted(S["arrive_to_publish_ms"]); sh = sorted(S["sharp"])
    q = lambda xs, p: round(xs[min(len(xs) - 1, int(p * len(xs)))], 1) if xs else None
    return {"ok": S["ready"] and S["room"], "ready": S["ready"], "room": S["room"], "room_name": ROOM, "identity": IDENT,
            "renderer": E("FACE_RENDERER", "flashhead"), "chunks": S["chunks"], "speech_chunks": S["speech_chunks"],
            "frames_published": S["frames"], "underruns": S["underruns"], "lines": S["lines"],
            "render_ms_p50": q(r, .5), "render_ms_p95": q(r, .95),
            "arrive_to_publish_ms": {"n": len(ap), "p50": q(ap, .5), "p95": q(ap, .95), "all": ap[-40:]},
            "sharpness_laplacian_var": {"n": len(sh), "p50": q(sh, .5), "min": q(sh, 0), "max": q(sh, .999)},
            "error": S["error"], "uptime_s": round(time.time() - S["t_start"]),
            "mode": S["mode"], "mode_switches": S["mode_switches"], "wide_frames_published": S["wide_frames"],
            "wide_render_ms_p50": q(sorted(S["wide_ms"]), .5), "wide_render_ms_p95": q(sorted(S["wide_ms"]), .95),
            "wide_chunks_late": S["wide_late"], "wide_chunks": len(S["wide_ms"]),
            "pub_late_frames": S["pub_late_frames"], "pub_max_lag_ms": S["pub_max_lag_ms"], "pub_reanchors": S["pub_reanchors"],
            "rec_dropped": S["rec_dropped"], "rec_thread": REC_THREAD, "pub_steady": PUB_STEADY,
            "voice_prebuf_ms": PREBUF_MS, "voice_pads": S["voice_pads"], "voice_holes": S["voice_holes"], "voice_prebuf_waits": S["voice_prebuf_waits"], "voice_lines": S["voice_lines"]}


async def health(req):
    return web.json_response(stats(), status=200 if S["ready"] else 503)


async def pause(req):
    if E("FACE_TEST_HOOKS", "0") != "1": return web.Response(status=404)
    s = float(req.query.get("s", "5")); S["paused_until"] = time.time() + s
    return web.json_response({"code": 0, "paused_s": s})


async def face_mode(req):
    """NOVA-FINAL: which face talks. wide = Ditto body (intro/ending), pip = SoulX face (game). Pending voice is kept."""
    m = req.query.get("m", "")
    if m not in ("wide", "pip"): return web.json_response({"code": 1, "msg": "m=wide|pip"}, status=400)
    if DUAL is None: return web.json_response({"code": 1, "msg": "FACE_RENDERER is not dual", "mode": "pip"})
    if m != S["mode"]:
        with lock:                                   # chunks of the old face not yet published are dropped (≤ 1 chunk)
            for c in list(ready):
                if c["mode"] != m: ready.remove(c)
        if m == "wide": DUAL.r["wide"].reset()       # a fresh delay line (silence) — the old one belonged to before the game
        S["mode"] = m; S["mode_switches"].append([round(time.time() - S["t_start"], 2), m]); log("face mode ->", m)
    return web.json_response({"code": 0, "mode": S["mode"]})


async def finish(req):
    """close the recordings (proof runs): <name>.mp4 = exactly the frames + voice that went to LiveKit
       face_published.mp4 (SoulX, 512) and wide_published.mp4 (Ditto, the body's full 1080x1920 — the cut the gate reads)"""
    if E("FACE_RECORD", "0") != "1": return web.json_response({"code": 1, "msg": "FACE_RECORD off"})
    rec = S.setdefault("_rec", {}); tag = "".join(ch for ch in req.query.get("tag", "") if ch.isalnum())
    with lock: cur = dict(rec); rec.clear()           # the publisher opens fresh recorders on its next chunk
    files = []
    for mode, name in (("pip", "face_published"), ("wide", "wide_published")):
        rv = cur.get(mode)
        if not rv: continue
        try: (rv[0].close() if REC_THREAD else rv[0].stdin.close()); rv[0].wait(60); rv[1].close()
        except Exception as e: return web.json_response({"code": 1, "msg": str(e)})
        out = os.path.join(OUT, name + ("_" + tag if tag else "") + ".mp4")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", rv[2], "-i", rv[3], "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", out])
        for f_ in (rv[2], rv[3]):
            try: os.remove(f_)
            except Exception: pass
        files.append(out)
    return web.json_response({"code": 0, "files": files})


async def main():
    app = web.Application(client_max_size=64 * 1024 * 1024)
    app.router.add_post("/humanaudio", humanaudio)
    app.router.add_get("/set_avatar", set_avatar)
    app.router.add_post("/interrupt_talk", interrupt)
    app.router.add_post("/is_speaking", is_speaking)
    app.router.add_get("/", health)
    app.router.add_post("/pause", pause)
    app.router.add_post("/finish", finish)
    app.router.add_get("/face_mode", face_mode)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    log("HTTP on", PORT, "— loading renderer", E("FACE_RENDERER", "flashhead"), "face", FACE_IMG)
    t = time.time()
    R = await asyncio.get_event_loop().run_in_executor(None, make_renderer)      # flashhead: torch.compile warm-up here
    log(f"renderer ready in {time.time() - t:.1f} s")
    threading.Thread(target=render_loop, args=(R,), daemon=True).start()
    S["ready"] = True
    while True:
        try:
            await publisher()
        except Exception as e:
            S["room"] = False; S["error"] = "livekit: " + repr(e)[:300]; log("publisher error", e); await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
