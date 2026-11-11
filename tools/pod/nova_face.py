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


def make_renderer():
    kind = E("FACE_RENDERER", "flashhead")
    if kind == "fake":
        return FakeRenderer()
    os.environ.setdefault("SHIM_FACE", FACE_IMG)                  # flashhead_renderer reads SHIM_FACE
    sys.path.insert(0, E("FACE_RENDERER_DIR", "/opt/maya-ops/lt"))
    from flashhead_renderer import Renderer                       # Maya's file, unchanged
    return Renderer()


# ───────────────────────── state ─────────────────────────
S = {"ready": False, "room": False, "chunks": 0, "speech_chunks": 0, "underruns": 0, "frames": 0,
     "render_ms": collections.deque(maxlen=400), "arrive_to_publish_ms": [], "sharp": [], "lines": 0,
     "error": "", "t_start": time.time(), "paused_until": 0.0}
lock = threading.Lock()
pending = collections.deque()        # [samples f32, t_arrival] — her voice waiting to be rendered
ready = collections.deque()          # rendered chunks waiting to be published
have_speech = threading.Event()


def pending_take(n):
    """Take up to n samples of queued voice. Returns (audio, t_first_arrival or None)."""
    got, t0, need = [], None, n
    with lock:
        while need and pending:
            a, t = pending[0]
            if t0 is None: t0 = t
            if len(a) <= need:
                got.append(a); need -= len(a); pending.popleft()
            else:
                got.append(a[:need]); pending[0] = [a[need:], t]; need = 0
        if not pending: have_speech.clear()
    if not got: return None, None
    a = np.concatenate(got)
    if len(a) < n: a = np.concatenate([a, np.zeros(n - len(a), np.float32)])
    return a, t0


def render_loop(R):
    import cv2
    while True:
        # keep exactly one chunk ahead of the publisher; speech pre-empts a silence chunk that has not started
        while True:
            with lock:
                n = len(ready)
                if n and have_speech.is_set() and not ready[-1]["speech"]:
                    ready.pop(); n -= 1
            if n == 0: break
            have_speech.wait(0.01)
        audio, t_arr = pending_take(SAMPLES)
        speech = audio is not None
        if not speech: audio = np.zeros(SAMPLES, np.float32)
        t = time.time()
        try:
            frames = R.render(audio)
        except Exception as e:
            S["error"] = "render: " + repr(e)[:300]; log("RENDER ERROR", e); time.sleep(0.2); continue
        S["render_ms"].append((time.time() - t) * 1000)
        if speech:
            S["speech_chunks"] += 1
            g = cv2.cvtColor(frames[CHUNK // 2], cv2.COLOR_BGR2GRAY)
            S["sharp"].append(float(cv2.Laplacian(g[96:416, 96:416], cv2.CV_64F).var()))   # centre of the face
            if S["speech_chunks"] <= 3 or S["speech_chunks"] % 15 == 0:
                cv2.imwrite(os.path.join(OUT, f"published_speech_{S['speech_chunks']:03d}.png"), frames[CHUNK // 2])
        with lock:
            ready.append({"frames": frames, "audio": audio, "speech": speech, "t_arr": t_arr})
        S["chunks"] += 1


# ───────────────────────── LiveKit publisher ─────────────────────────
async def publisher():
    from livekit import rtc, api
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
    await room.local_participant.publish_track(atr, ao)
    S["room"] = True; log("LiveKit: published as", IDENT, "in room", ROOM)

    rec_v = rec_a = None
    if E("FACE_RECORD", "0") == "1":
        rec_v = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", "512x512",
                                  "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
                                  "-pix_fmt", "yuv420p", os.path.join(OUT, "face_published_video.mp4")], stdin=subprocess.PIPE)
        rec_a = wave.open(os.path.join(OUT, "face_published_voice.wav"), "wb"); rec_a.setnchannels(1); rec_a.setsampwidth(2); rec_a.setframerate(SR)
    S["_rec"] = (rec_v, rec_a)

    # FACE_VIDEO_DELAY_FRAMES (default 0): hold the face back N frames behind the voice. Do NOT set it: judged BY EYE on the
    # pod recordings (2026-11-11) the mouth already starts ~120-160 ms AFTER her voice with 0, and 3 frames made it later.
    # (The in-page mouth-motion probe said "133 ms before" — it counts head motion in silence; the frames say otherwise.)
    vdelay = int(E("FACE_VIDEO_DELAY_FRAMES", "0")); vq = collections.deque()
    log("video delay frames:", vdelay)
    loop = asyncio.get_event_loop()
    t0, i, last = loop.time(), 0, None
    while True:
        with lock:
            ch = ready.popleft() if ready else None
        if ch is None:                                  # renderer late: hold the last frame, silence — never a black frame
            S["underruns"] += 1
            ch = {"frames": [last] * CHUNK if last is not None else [np.zeros((512, 512, 3), np.uint8)] * CHUNK,
                  "audio": np.zeros(SAMPLES, np.float32), "speech": False, "t_arr": None}
        if ch["speech"] and ch["t_arr"] is not None:
            S["arrive_to_publish_ms"].append(round((time.time() - ch["t_arr"]) * 1000))
        pcm = (np.clip(ch["audio"], -1, 1) * 32767).astype(np.int16)
        for k in range(CHUNK):
            dt = t0 + i / FPS - loop.time()
            if dt > 0: await asyncio.sleep(dt)
            elif dt < -0.5: t0 = loop.time() - i / FPS             # we fell far behind (stall): re-anchor the clock
            f = ch["frames"][k]; last = f
            if vdelay:
                vq.append(f)
                f = vq.popleft() if len(vq) > vdelay else vq[0]
            if time.time() >= S["paused_until"]:
                rgba = np.dstack([f[:, :, ::-1], np.full(f.shape[:2], 255, np.uint8)])
                vsrc.capture_frame(rtc.VideoFrame(512, 512, rtc.VideoBufferType.RGBA, rgba.tobytes()))
                S["frames"] += 1
            seg = pcm[k * STEP:(k + 1) * STEP]
            await asrc.capture_frame(rtc.AudioFrame(seg.tobytes(), SR, 1, len(seg)))
            if rec_v:
                try: rec_v.stdin.write(f.tobytes()); rec_a.writeframes(seg.tobytes())
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
            "error": S["error"], "uptime_s": round(time.time() - S["t_start"])}


async def health(req):
    return web.json_response(stats(), status=200 if S["ready"] else 503)


async def pause(req):
    if E("FACE_TEST_HOOKS", "0") != "1": return web.Response(status=404)
    s = float(req.query.get("s", "5")); S["paused_until"] = time.time() + s
    return web.json_response({"code": 0, "paused_s": s})


async def finish(req):
    """close the recording (proof runs): face_published.mp4 = exactly the frames + voice that went to LiveKit"""
    rv, ra = S.get("_rec", (None, None))
    if not rv: return web.json_response({"code": 1, "msg": "FACE_RECORD off"})
    S["_rec"] = (None, None)
    try: rv.stdin.close(); rv.wait(30); ra.close()
    except Exception as e: return web.json_response({"code": 1, "msg": str(e)})
    out = os.path.join(OUT, "face_published.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(OUT, "face_published_video.mp4"),
                    "-i", os.path.join(OUT, "face_published_voice.wav"), "-c:v", "copy", "-c:a", "aac", "-b:a", "64k", "-shortest", out])
    return web.json_response({"code": 0, "file": out})


async def main():
    app = web.Application(client_max_size=64 * 1024 * 1024)
    app.router.add_post("/humanaudio", humanaudio)
    app.router.add_get("/set_avatar", set_avatar)
    app.router.add_post("/interrupt_talk", interrupt)
    app.router.add_post("/is_speaking", is_speaking)
    app.router.add_get("/", health)
    app.router.add_post("/pause", pause)
    app.router.add_post("/finish", finish)
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
