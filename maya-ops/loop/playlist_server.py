#!/usr/bin/env python3
"""LOOP MODE step 3 — the playlist player: baked segments -> one continuous RTMP stream,
with gapless reply-insertion (pod-side).

Usage:  RTMP_URL=rtmp://a.rtmp.youtube.com/live2/<key> \
        python3 playlist_server.py bakes/ [--port 8020]

Design (Ctrip playlist pattern):
  - ONE ffmpeg process for the whole stream: `-re -f mpegts -i pipe: -c copy -f flv $RTMP_URL`.
    We feed it .ts segment BYTES on stdin in queue order. Segment boundaries are therefore
    free insertion points — no reconnect, no gap, no re-encode.
  - The playlist loops product blocks head-to-tail forever.
  - POST /insert queues a one-shot segment (a generated answer clip); it plays after the
    CURRENT segment finishes, then is deleted — it never recurs on the next loop.
  - POST /kill flips to the BRB card loop (operator supremacy, same as live mode);
    POST /resume returns to the playlist.
  - GET /state for the director.

Untested-on-pod honesty: written 2026-08-07 with the pod stopped. The ffmpeg pipe design
is standard, but first run on the pod must verify (a) YouTube accepts the TS timestamps
across segment boundaries, (b) all bakes share codec params (bake_playlist.py pins them).
"""
import argparse, json, os, pathlib, subprocess, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RTMP = os.environ.get("RTMP_URL", "")
CHUNK = 188 * 1024  # TS packet aligned

class Player:
    def __init__(self, bakes_dir, brb_ts=None):
        self.playlist = []          # [(path, label)] — the loop
        self.inserts = []           # one-shot queue, consumed between segments
        self.lock = threading.Lock()
        self.killed = False
        self.now_playing = None
        self.played = 0
        self.brb = brb_ts
        for mf in sorted(pathlib.Path(bakes_dir).glob("*/manifest.json")):
            m = json.loads(mf.read_text(encoding="utf-8"))
            for s in m["segments"]:
                self.playlist.append((str(mf.parent / s["file"]), f"{m['product_id']}/{s['role']}"))
        if not self.playlist:
            raise SystemExit(f"no baked segments under {bakes_dir}")

    def next_segment(self):
        with self.lock:
            if self.killed and self.brb:
                return (self.brb, "BRB"), False
            if self.inserts:
                return self.inserts.pop(0), True   # (path,label), one_shot
        item = self.playlist[self.played % len(self.playlist)]
        self.played += 1
        return item, False

    def run(self):
        if not RTMP: raise SystemExit("set RTMP_URL")
        ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "warning", "-re",
                               "-f", "mpegts", "-i", "pipe:0", "-c", "copy", "-f", "flv", RTMP],
                              stdin=subprocess.PIPE)
        while True:
            (path, label), one_shot = self.next_segment()
            self.now_playing = label
            print(f"[PLAY] {label} {'(insert)' if one_shot else ''}", flush=True)
            try:
                with open(path, "rb") as f:
                    while chunk := f.read(CHUNK):
                        ff.stdin.write(chunk)
                ff.stdin.flush()
            finally:
                if one_shot:
                    try: os.unlink(path)           # played once, gone forever
                    except OSError: pass
            if ff.poll() is not None:
                raise SystemExit(f"ffmpeg died: {ff.returncode}")

PLAYER = None

class Api(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        if self.path == "/state":
            with PLAYER.lock:
                self._json(200, {"ok": True, "now": PLAYER.now_playing, "played": PLAYER.played,
                                 "loop_len": len(PLAYER.playlist), "inserts_waiting": len(PLAYER.inserts),
                                 "killed": PLAYER.killed})
        else: self._json(404, {"ok": False})
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}") if n else {}
        if self.path == "/insert":
            p = body.get("file", "")
            if not (p and pathlib.Path(p).is_file()): return self._json(400, {"ok": False, "err": "file not found"})
            with PLAYER.lock: PLAYER.inserts.append((p, body.get("label", "answer")))
            return self._json(200, {"ok": True, "queued_behind": PLAYER.now_playing})
        if self.path == "/kill":
            with PLAYER.lock: PLAYER.killed = True
            return self._json(200, {"ok": True})
        if self.path == "/resume":
            with PLAYER.lock: PLAYER.killed = False
            return self._json(200, {"ok": True})
        self._json(404, {"ok": False})
    def log_message(self, *a): pass

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("bakes"); ap.add_argument("--port", type=int, default=8020)
    ap.add_argument("--brb", default=None, help="path to a baked BRB .ts for /kill")
    a = ap.parse_args()
    PLAYER = Player(a.bakes, a.brb)
    threading.Thread(target=lambda: ThreadingHTTPServer(("0.0.0.0", a.port), Api).serve_forever(),
                     daemon=True).start()
    PLAYER.run()
