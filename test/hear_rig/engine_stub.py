#!/usr/bin/env python3
"""rig: stand-in for tools/pod/nova_face.py (FACE_RENDERER=dual) with NO GPU and NO LiveKit.
POST /humanaudio (16 k wav, as rt_lk.feed_engine sends) -> the voice is streamed to the page's LiveKit shim over
ws /rigaudio in real time, after the face server's constant delay (wide: prebuf 0.4 + DITTO_PRIME 1.4 s; pip 1.0 s)."""
import asyncio, io, json, os, time, wave
import numpy as np
from aiohttp import web
SR = 16000; S = {"mode": "wide", "lines": 0, "clients": set(), "q": None, "log": []}
DELAY = {"wide": float(os.environ.get("RIG_WIDE_DELAY", "1.8")), "pip": float(os.environ.get("RIG_PIP_DELAY", "1.0"))}
def log(*a): print(time.strftime("%H:%M:%S"), "[ENGINE-STUB]", *a, flush=True)
async def humanaudio(req):
    data = await req.post(); f = data.get("file"); b = f.file.read()
    w = wave.open(io.BytesIO(b)); pcm = w.readframes(w.getnframes())
    await S["q"].put((time.time(), pcm, S["mode"]))
    return web.json_response({"code": 0, "data": len(pcm) // 2})
async def interrupt_talk(req):
    # NOVA_BARGE: cut the line (queued voice dropped, the piece loop stops) - as tools/pod/nova_face.py {"cut": true}
    S["cut_t"] = time.time(); n = 0
    while not S["q"].empty():
        S["q"].get_nowait(); n += 1
    log("CUT (barge-in): dropped", n, "queued pieces")
    return web.json_response({"code": 0})
async def face_mode(req):
    m = req.query.get("m", ""); S["mode"] = m; log("face mode ->", m)
    for c in list(S["clients"]):
        try: await c.send_str(json.dumps({"mode": m}))
        except Exception: pass
    return web.json_response({"code": 0, "mode": m})
async def health(req): return web.json_response({"ok": True, "ready": True, "room": True, "mode": S["mode"]})
async def rigaudio(req):
    ws = web.WebSocketResponse(); await ws.prepare(req); S["clients"].add(ws); log("page shim connected")
    try:
        async for _ in ws: pass
    finally: S["clients"].discard(ws)
    return ws
async def pump():
    t_free = 0.0
    while True:
        t_in, pcm, mode = await S["q"].get()
        start = max(t_in + DELAY.get(mode, 1.0), t_free)          # constant pipeline delay, lines never overlap
        if t_free < t_in: log("line starts: fed %.2f, audible in %.2f s (%s)" % (t_in % 1000, start - time.time(), mode))
        if t_in < S.get("cut_t", 0): continue
        for i in range(0, len(pcm), 6400):                         # 0.2 s pieces, real time
            if t_in < S.get("cut_t", 0): t_free = time.time(); break
            piece = pcm[i:i + 6400]; due = start + (i / 2) / SR
            d = due - time.time() - 0.15                           # sent 150 ms early: the shim schedules by due time
            if d > 0: await asyncio.sleep(d)
            for c in list(S["clients"]):
                try: await c.send_bytes(np.float64(due).tobytes() + piece)
                except Exception: pass
        else: t_free = start + (len(pcm) / 2) / SR
async def main():
    S["q"] = asyncio.Queue(); app = web.Application(client_max_size=64 * 1024 * 1024)
    app.router.add_post("/humanaudio", humanaudio); app.router.add_get("/face_mode", face_mode); app.router.add_post("/interrupt_talk", interrupt_talk)
    app.router.add_get("/", health); app.router.add_get("/rigaudio", rigaudio)
    r = web.AppRunner(app); await r.setup(); await web.TCPSite(r, "127.0.0.1", 8010).start(); log("on 8010")
    await pump()
asyncio.run(main())
