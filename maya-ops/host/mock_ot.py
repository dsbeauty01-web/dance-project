#!/usr/bin/env python3
"""
mock_ot.py — a fake OpenTalking API for offline QA of ot_live.py / maya_ot.py (no GPU, no Facebook).
Implements the routes we use; records every /speak with a timestamp to mock_speak.jsonl.
  python mock_ot.py            # :8210
Avatar-switch route returns 404 on purpose → proves the runtime disables gestures gracefully.
Set MOCK_AVATAR_SWITCH=1 to make /sessions/{sid}/avatar succeed instead.
"""
import json, os, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SESS = {}
LOG = open("mock_speak.jsonl", "a", encoding="utf-8")


class H(BaseHTTPRequestHandler):
    def _j(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def _s(self, code, obj=None):
        b = json.dumps(obj or {}).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        p = self.path.split("?")[0].rstrip("/")
        if p.startswith("/sessions/") and p.endswith("/outputs"):
            sid = p.split("/")[2]
            return self._s(200, [{"output_id": o, "state": "connected"} for o in SESS.get(sid, {}).get("outputs", [])])
        if p.startswith("/sessions/"):
            sid = p.split("/")[2]
            return self._s(200 if sid in SESS else 404, {"session_id": sid, "state": "ready"})
        self._s(200, {"ok": True, "mock": True})

    def do_POST(self):
        p = self.path.split("?")[0].rstrip("/"); j = self._j()
        if p == "/sessions":
            sid = uuid.uuid4().hex[:12]; SESS[sid] = {"cfg": j, "outputs": []}
            return self._s(201, {"session_id": sid})
        parts = p.split("/")
        if len(parts) >= 4 and parts[1] == "sessions":
            sid, action = parts[2], parts[3]
            if sid not in SESS:
                return self._s(404, {"error": "no session"})
            if action == "start":
                return self._s(200, {"state": "ready"})
            if action == "outputs":
                oid = "out-" + uuid.uuid4().hex[:6]; SESS[sid]["outputs"].append(oid)
                return self._s(201, {"output_id": oid, "state": "connecting"})
            if action == "speak":
                rec = {"ts": time.time(), "sid": sid, "text": j.get("text", ""), "mode": j.get("mode")}
                LOG.write(json.dumps(rec, ensure_ascii=False) + "\n"); LOG.flush()
                return self._s(202, {"accepted": True, "command_id": j.get("command_id")})
            if action == "interrupt":
                return self._s(202, {"ok": True})
            if action in ("avatar", "switch_avatar"):
                return self._s(200 if os.environ.get("MOCK_AVATAR_SWITCH") == "1" else 404, {"avatar_id": j.get("avatar_id")})
            if action == "stop":
                return self._s(200, {})
        self._s(404, {"error": "unknown route " + p})

    def do_DELETE(self):
        self._s(204)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("mock OpenTalking on :8210", flush=True)
    ThreadingHTTPServer(("0.0.0.0", 8210), H).serve_forever()
