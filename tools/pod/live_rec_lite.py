#!/usr/bin/env python3
"""live_rec_lite.py -- record Nova's LIVE stream the way a remote viewer receives it, without a browser on the pod.
(session nova-take8c, 2026-11-11)

WHY: the pod's container has a CPU QUOTA of 6.8 CPUs (cpu.cfs_quota_us 680000 / period 100000) although nproc says 32.
The headless-Chromium recorder (live_intro_harness.py) used ~5.4 of them by itself, so the whole container was throttled
in 48 % of all scheduling periods and Ditto -- 294 ms per 1 s chunk alone on the same pod -- fell to ~1.2 s. In production
the viewer is the kid's own browser, not a process on the pod. This recorder is the cheap stand-in for that viewer:

  * joins the LiveKit room with the brain's own /token (exactly what the page does), subscribes to nova-avatar's video +
    audio, and writes them: video -> ffmpeg (arrival wall-clock timestamps, constant 25 fps output, so a frozen picture is
    recorded as frozen, x264 ultrafast), audio -> 16 kHz mono PCM; muxed at the end with the measured start offset.
  * plays the kid: the same {"type": "text"} turns the page's chat box sends, on the brain's /rt websocket
    (?commercial=1 = the pre-game talk phase; no game-start is sent, so every word she says goes through Ditto's lips).
  * logs the bridge's face metadata (A8) as the page's shared/nova-face.js would read it.

  python3 live_rec_lite.py OUT_PREFIX SECONDS KID_SCRIPT.json     (KID_SCRIPT = [[t_seconds, "line"], ...])
Writes OUT_PREFIX.mp4, OUT_PREFIX.json (transcript, face metadata, frame/arrival counts).
Runs in the bridge's own Python (livekit.rtc + websockets + numpy are there).
"""
import asyncio, json, os, subprocess, sys, time, urllib.request
import numpy as np
from livekit import rtc
import websockets

OUT, DUR, KIDS = sys.argv[1], float(sys.argv[2]), json.load(open(sys.argv[3]))
BRAIN = "127.0.0.1:8765"
W, H = 720, 1288


async def main():
    rep = {"nova_lines": [], "kid_lines": [], "face_meta": [], "video_frames": 0, "audio_frames": 0, "errors": []}
    tok = json.loads(urllib.request.urlopen(f"http://{BRAIN}/token", timeout=10).read())
    room = rtc.Room()
    t_v0 = t_a0 = None
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-use_wallclock_as_timestamps", "1", "-f", "rawvideo", "-pix_fmt", "yuv420p",
                           "-s", f"{W}x{H}", "-i", "-", "-vf", "fps=25", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16",
                           "-pix_fmt", "yuv420p", OUT + ".v.mp4"], stdin=subprocess.PIPE)
    af = open(OUT + ".pcm", "wb")
    stop = asyncio.Event()

    async def video(track):
        nonlocal t_v0
        async for ev in rtc.VideoStream(track):
            if stop.is_set(): break
            f = ev.frame
            if (f.width, f.height) != (W, H):
                rep["errors"].append(f"video size {f.width}x{f.height}"); continue
            b = bytes(f.convert(rtc.VideoBufferType.I420).data)
            if t_v0 is None: t_v0 = time.time()
            try: ff.stdin.write(b)
            except Exception as e: rep["errors"].append(repr(e)); break
            rep["video_frames"] += 1

    async def audio(track):
        nonlocal t_a0
        async for ev in rtc.AudioStream(track, sample_rate=16000, num_channels=1):
            if stop.is_set(): break
            if t_a0 is None: t_a0 = time.time() - ev.frame.samples_per_channel / 16000.0
            af.write(bytes(ev.frame.data)); rep["audio_frames"] += 1

    def meta(p):
        if p.identity == "nova-avatar":
            rep["face_meta"].append({"t": round(time.time(), 2), "metadata": p.metadata})

    @room.on("track_subscribed")
    def _sub(track, pub, p):
        if p.identity != "nova-avatar": return
        meta(p)
        if track.kind == rtc.TrackKind.KIND_VIDEO: asyncio.ensure_future(video(track))
        elif track.kind == rtc.TrackKind.KIND_AUDIO: asyncio.ensure_future(audio(track))

    @room.on("participant_metadata_changed")
    def _meta(p, old, new):
        meta(p)

    await room.connect(tok["url"], tok["token"])
    t0 = time.time()

    async def kid():
        async with websockets.connect(f"ws://{BRAIN}/rt?commercial=1", max_size=16 * 1024 * 1024) as ws:
            async def rx():
                async for m in ws:
                    if isinstance(m, (bytes, bytearray)): continue
                    try: d = json.loads(m)
                    except Exception: continue
                    if d.get("type") == "nova_done": rep["nova_lines"].append([round(time.time() - t0, 1), d.get("text", "")])
            rt = asyncio.ensure_future(rx())
            for ts, line in KIDS:
                while time.time() - t0 < ts:
                    await asyncio.sleep(0.2)
                await ws.send(json.dumps({"type": "text", "text": line}))
                rep["kid_lines"].append([round(time.time() - t0, 1), line])
            while time.time() - t0 < DUR:
                await asyncio.sleep(0.5)
            rt.cancel()

    try:
        await kid()
    except Exception as e:
        rep["errors"].append(f"kid: {e!r}")
        while time.time() - t0 < DUR: await asyncio.sleep(0.5)
    stop.set()
    await room.disconnect()
    await asyncio.sleep(0.5)
    ff.stdin.close(); ff.wait(); af.close()
    off = (t_a0 - t_v0) if (t_a0 and t_v0) else 0.0          # audio starts this much after video
    rep.update(t_video0=t_v0, t_audio0=t_a0, audio_offset_s=round(off, 3))
    # place the audio on the video's clock. A negative -itsoffset is silently dropped by the mp4 mux (measured on take 3:
    # audio start_time 0.000 although the offset was -0.46 s -> lips read 480 ms early), so trim or delay the samples.
    af_ = f"atrim=start={-off:.3f},asetpts=PTS-STARTPTS" if off < 0 else f"adelay={int(off * 1000)}:all=1"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", OUT + ".v.mp4", "-f", "s16le", "-ar", "16000", "-ac", "1",
                    "-i", OUT + ".pcm", "-map", "0:v", "-map", "1:a", "-af", af_, "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", OUT + ".mp4"])
    for p in (OUT + ".v.mp4", OUT + ".pcm"):
        try: os.remove(p)
        except Exception: pass
    json.dump(rep, open(OUT + ".json", "w"), indent=1)
    print(json.dumps({k: rep[k] for k in ("video_frames", "audio_frames", "audio_offset_s", "errors")}), "nova_lines", len(rep["nova_lines"]))


asyncio.run(main())
