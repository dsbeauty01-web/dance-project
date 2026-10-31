#!/usr/bin/env python3
# LiveKit publisher bridge — FULLY ASYNC (no threads). livekit-rtc's native runtime
# deadlocks (futex) when mixed with Python threads, so everything lives in ONE asyncio
# loop: an async socket server receives the engine's frames, async tasks publish them.
import os, asyncio, struct, time
import numpy as np
from livekit import rtc, api

URL = os.environ["LIVEKIT_URL"]
KEY = os.environ["LIVEKIT_API_KEY"]
SEC = os.environ["LIVEKIT_API_SECRET"]
ROOM = os.environ.get("LK_ROOM", "nova-live")
PORT = int(os.environ.get("LK_BRIDGE_PORT", "9999"))
AUDIO_SR = 16000

def _has_viewer(room):
    try:
        rp = getattr(room, 'remote_participants', None)
        if rp is None: rp = getattr(room, 'participants', {})
        return len(rp) > 0
    except Exception:
        return True


vq = None
aq = None


def bgr_to_rgba(w, h, buf):
    arr = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 3)
    rgba = np.empty((h, w, 4), dtype=np.uint8)
    rgba[:, :, 0] = arr[:, :, 2]   # R <- B
    rgba[:, :, 1] = arr[:, :, 1]   # G
    rgba[:, :, 2] = arr[:, :, 0]   # B <- R
    rgba[:, :, 3] = 255
    return rgba.tobytes()

# DOWNSCALE (2026-10-22): publish 720x1288 (0.129 bpp @3Mbit/25fps) instead of 1076x1924
# (0.06 bpp = bitrate starvation). numpy-only nearest-neighbour, index maps cached per (w,h).
_RIDX = {}
_TW, _TH = 720, 1288
def _downscale(w, h, rgba):
    if (w, h) == (_TW, _TH):
        return w, h, rgba
    m = _RIDX.get((w, h))
    if m is None:
        yi = (np.arange(_TH) * h // _TH).astype(np.intp)
        xi = (np.arange(_TW) * w // _TW).astype(np.intp)
        m = (yi, xi); _RIDX[(w, h)] = m
    yi, xi = m
    a = np.frombuffer(rgba, dtype=np.uint8).reshape(h, w, 4)
    return _TW, _TH, np.ascontiguousarray(a[yi][:, xi]).tobytes()


async def handle_conn(reader, writer):
    print("bridge: engine connected", flush=True)
    # BRIDGE_DROP diagnostics 2026-08-05.
    # The engine<->bridge link drops mid-session; frames stop reaching LiveKit and Nova
    # freezes on her last rendered frame, which reads to a user as "slow net". The old
    # handler swallowed asyncio.IncompleteReadError with a bare `pass` and printed only
    # "engine disconnected", so the CAUSE was never recorded and every drop looked the same.
    # This adds one line describing HOW the read ended. No other behaviour changes:
    # the loop, the queues, the drop-oldest policy and the existing prints are untouched.
    last_frame = time.monotonic()
    frames = 0
    exc_type = "CleanClose"      # loop exited without an exception
    errno_val = ""
    msg = ""
    try:
        while True:
            kind = await reader.readexactly(1)
            if kind == b'V':
                w, h, ln = struct.unpack('>III', await reader.readexactly(12))
                data = await reader.readexactly(ln)
                rgba = bgr_to_rgba(w, h, data)
                if vq.full():
                    try: vq.get_nowait()
                    except asyncio.QueueEmpty: pass
                vq.put_nowait((w, h, rgba))
                last_frame = time.monotonic(); frames += 1
            elif kind == b'A':
                (ln,) = struct.unpack('>I', await reader.readexactly(4))
                data = await reader.readexactly(ln)
                if not aq.full():
                    aq.put_nowait(np.frombuffer(data, dtype=np.int16).copy())
                last_frame = time.monotonic()
            else:
                # engine sent a byte that is neither 'V' nor 'A' -- the original code
                # broke out of the loop here silently. Now it is named.
                exc_type = "UnknownKind"; msg = repr(kind)
                break
    except asyncio.IncompleteReadError as e:
        # the clean-close path: the peer stopped mid-message. Previously `pass`.
        exc_type = "IncompleteReadError"
        msg = "expected=%s partial=%d" % (getattr(e, "expected", "?"), len(getattr(e, "partial", b"") or b""))
    except Exception as e:
        exc_type = type(e).__name__
        errno_val = getattr(e, "errno", "")
        msg = str(e)
        print("bridge conn err:", e, flush=True)
    print("BRIDGE_DROP: %s errno=%s msg=%s since_last_frame=%.2fs frames_this_conn=%d" % (
        exc_type, errno_val, msg, time.monotonic() - last_frame, frames), flush=True)
    print("bridge: engine disconnected", flush=True)


async def main():
    global vq, aq
    vq = asyncio.Queue(maxsize=120)
    aq = asyncio.Queue(maxsize=600)

    # Connect LiveKit FIRST (exact order of the proven dance publisher) so its native
    # runtime initializes cleanly before anything else touches the event loop.
    g = api.VideoGrants(room_join=True, room=ROOM, can_publish=True, can_subscribe=True)
    tok = (api.AccessToken(KEY, SEC).with_identity("nova-avatar").with_name("Nova")
           .with_grants(g).to_jwt())
    room = rtc.Room()
    await room.connect(URL, tok)
    print(f"bridge: connected to LiveKit room '{ROOM}'", flush=True)

    asrc = rtc.AudioSource(AUDIO_SR, 1)
    atrack = rtc.LocalAudioTrack.create_audio_track("nova-audio", asrc)
    await room.local_participant.publish_track(
        atrack, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))
    print("bridge: audio track published", flush=True)

    # socket server AFTER LiveKit is up
    server = await asyncio.start_server(handle_conn, "127.0.0.1", PORT)
    print(f"bridge: listening on 127.0.0.1:{PORT}", flush=True)

    vstate = {"src": None}

    async def drain_video():
        n = 0
        while True:
            w, h, rgba = await vq.get()
            w, h, rgba = _downscale(w, h, rgba)
            if vstate["src"] is None:
                vstate["src"] = rtc.VideoSource(w, h)
                vt = rtc.LocalVideoTrack.create_video_track("nova-video", vstate["src"])
                await room.local_participant.publish_track(
                    vt, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_CAMERA, simulcast=True, video_encoding=rtc.VideoEncoding(max_framerate=25, max_bitrate=3_000_000)))
                print(f"bridge: video track published {w}x{h}", flush=True)
            if not _has_viewer(room):
                continue   # VIEWER-GATED: no viewer -> don't stream (save LiveKit bandwidth)
            vstate["src"].capture_frame(rtc.VideoFrame(w, h, rtc.VideoBufferType.RGBA, rgba))
            n += 1
            if n % 100 == 0:
                print(f"bridge: published {n} frames", flush=True)

    async def drain_audio():
        # AUDIO COUNTER 2026-08-05: video logged every 100 frames, audio logged NOTHING,
        # so "no sound" could not be traced -- there was no way to tell whether audio
        # reached the bridge, was dropped by the viewer gate, or died in the browser.
        an = 0
        agated = 0
        while True:
            pcm = await aq.get()
            n = int(pcm.shape[0])
            fr = rtc.AudioFrame.create(AUDIO_SR, 1, n)
            np.frombuffer(fr.data, dtype=np.int16)[:] = pcm[:n]
            # VIEWER GATE REMOVED FOR AUDIO 2026-08-05.
            # It dropped every audio frame whenever room.remote_participants read empty,
            # producing TOTAL SILENCE with no error anywhere: the track was "published",
            # the engine was emitting hundreds of chunks, and every one was discarded here.
            # The gate exists to save LiveKit bandwidth, which is a video concern -- audio
            # is a rounding error beside 1076x1924 video, and LiveKit already stops sending
            # to a room nobody is subscribed to. Keeping it on video only.
            # Asymmetry of failure: a wrong gate on video freezes the picture (obvious and
            # recoverable); on audio it is silence with no clue, which cost days here.
            if not _has_viewer(room):
                agated += 1
                if agated % 200 == 0:
                    print(f"bridge: (note) no viewer detected, still sending audio x{agated}", flush=True)
            await asrc.capture_frame(fr)
            an += 1
            if an % 100 == 0:
                print(f"bridge: audio published {an} frames ({n} samples @ {AUDIO_SR}Hz)", flush=True)

    async with server:
        await asyncio.gather(server.serve_forever(), drain_video(), drain_audio())

asyncio.run(main())
