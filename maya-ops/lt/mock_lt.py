#!/usr/bin/env python3
"""
mock_lt.py — fake LiveTalking on :8010 for offline QA of maya_lt.py. Behaves like the free edition:
  /human → "speaking" for ~len(text)/14 seconds (≈2.6 words/s); /set_audiotype → records the silent-state clip;
  /is_speaking → true while speaking; action clips are "visible" only while not speaking (recorded for the QA to check).
Writes mock_lt_timeline.jsonl with every event so the QA can assert ORDER and TIMING (gesture before speech, idle after).
"""
import json, os, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATE = {"audiotype": 1, "speaking_until": 0.0, "events": []}
LOG = open("mock_lt_timeline.jsonl", "a", encoding="utf-8")
lock = threading.Lock()


def ev(kind, **k):
    e = {"t": time.time(), "kind": kind, **k}
    with lock:
        STATE["events"].append(e); LOG.write(json.dumps(e, ensure_ascii=False) + "\n"); LOG.flush()


class H(BaseHTTPRequestHandler):
    def _j(self):
        n = int(self.headers.get("Content-Length", 0))
        if self.headers.get("Content-Type", "").startswith("multipart/"):
            self.rfile.read(n); return {}
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def _s(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_POST(self):
        j = self._j(); p = self.path.split("?")[0]
        now = time.time(); speaking = now < STATE["speaking_until"]
        if p == "/human":
            txt = j.get("text", ""); dur = max(0.8, len(txt) / 14.0)
            if speaking and not j.get("interrupt"):
                STATE["speaking_until"] += dur          # queued behind current speech (LiveTalking queues text)
            else:
                STATE["speaking_until"] = now + dur
            ev("speak", text=txt, dur=round(dur, 2), interrupt=bool(j.get("interrupt")), audiotype_at_call=STATE["audiotype"], was_speaking=speaking)
            return self._s(200, {"code": 0, "data": "ok"})
        if p == "/set_audiotype":
            STATE["audiotype"] = int(j.get("audiotype", 1))
            ev("audiotype", audiotype=STATE["audiotype"], visible_now=(not speaking))
            return self._s(200, {"code": 0})
        if p == "/is_speaking":
            return self._s(200, {"code": 0, "data": speaking})
        if p == "/interrupt_talk":
            STATE["speaking_until"] = now; ev("interrupt"); return self._s(200, {"code": 0})
        if p == "/humanaudio":
            STATE["speaking_until"] = now + 2.0; ev("speak_audio"); return self._s(200, {"code": 0})
        self._s(404, {"code": 1, "msg": "unknown " + p})

    def do_GET(self):
        self._s(200, {"ok": True, "mock": "livetalking", "audiotype": STATE["audiotype"], "speaking": time.time() < STATE["speaking_until"]})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("MOCK_LT_PORT", "8010"))
    print(f"mock LiveTalking on :{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
