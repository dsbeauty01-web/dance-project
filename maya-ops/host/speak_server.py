#!/usr/bin/env python3
"""
speak_server.py v2 — runs ON THE POD next to the engine. Bridges maya_host → engine (LiveTalking/MuseTalk).

  POST /speak {"text","gesture","interrupt"} → engine /human {"text","type":"echo","interrupt":<bool>,"sessionid":SID}
                                              (+ optional gesture → GESTURE_MAP[gesture] avatar/clip switch)
  POST /scene {"scene","gesture"}            → engine /set_avatar {"avatar": SCENE_MAP[scene] or GESTURE_MAP[gesture]}
  POST /interrupt                            → next line carries interrupt=true; engine cuts current audio
  GET  /health

ENV
  ENGINE_URL=http://127.0.0.1:8010   ENGINE_SESSION_ID=0   SPEAK_PORT=8790
  SCENE_MAP='{"IDLE":"maya_idle","LISTEN":"maya_listen","SPEAK":"maya_speak","PITCH":"maya_serum","CUT_APPLY":"cut_apply","CUT_EXAMINE":"cut_examine"}'
  GESTURE_MAP='{"WAVE":"maya_wave","POINT_DOWN":"maya_point","SHOW":"maya_serum","NOISE_GLANCE":"maya_idle_b","NOISE_SIP":"maya_idle_c"}'
  Unknown scene/gesture = no-op (safe). Missing bakes just never switch.
"""
import json, os, threading, time, logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

ENGINE = os.environ.get("ENGINE_URL", "http://127.0.0.1:8010").rstrip("/")
SID = int(os.environ.get("ENGINE_SESSION_ID", "0"))
PORT = int(os.environ.get("SPEAK_PORT", "8790"))
SCENE_MAP = json.loads(os.environ.get("SCENE_MAP", "{}"))
GESTURE_MAP = json.loads(os.environ.get("GESTURE_MAP", "{}"))
logging.basicConfig(level=logging.INFO, format="%(asctime)s speak: %(message)s")
log = logging.getLogger()
_lock = threading.Lock()
_state = {"last": "", "ts": 0.0, "ok": None, "pending_interrupt": False, "avatar": ""}


def engine_alive() -> bool:
    try:
        return requests.get(ENGINE + "/", timeout=3).status_code < 500
    except Exception:
        return False


def set_avatar(name: str) -> bool:
    if not name or name == _state["avatar"]:
        return True
    try:
        r = requests.post(ENGINE + "/set_avatar", json={"avatar": name, "sessionid": SID}, timeout=5)
        if r.status_code < 300:
            _state["avatar"] = name
        return r.status_code < 300
    except Exception as e:
        log.warning("set_avatar failed: %s", e); return False


def speak(text: str, gesture: str, interrupt: bool) -> bool:
    with _lock:
        interrupt = interrupt or _state["pending_interrupt"]
        _state["pending_interrupt"] = False
        if gesture and gesture in GESTURE_MAP:
            set_avatar(GESTURE_MAP[gesture])
        try:
            r = requests.post(ENGINE + "/human", json={"text": text, "type": "echo", "interrupt": interrupt, "sessionid": SID}, timeout=10)
            ok = r.status_code < 300
        except Exception as e:
            log.error("engine /human failed: %s", e); ok = False
        _state.update(last=text, ts=time.time(), ok=ok)
        time.sleep(min(20.0, 0.35 + len(text.split()) / 2.6))  # pace so lines never overlap
    return ok


class H(BaseHTTPRequestHandler):
    def _json(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        self._send(200, {"ok": True, "engine": engine_alive(), "state": _state})

    def do_POST(self):
        j = self._json()
        if self.path == "/speak":
            t = (j.get("text") or "").strip()
            if not t:
                return self._send(400, {"ok": False})
            threading.Thread(target=speak, args=(t, j.get("gesture", ""), bool(j.get("interrupt"))), daemon=True).start()
            return self._send(202, {"ok": True})
        if self.path == "/scene":
            name = SCENE_MAP.get(j.get("scene", "")) or GESTURE_MAP.get(j.get("gesture", ""))
            return self._send(200, {"ok": set_avatar(name) if name else True})
        if self.path == "/interrupt":
            _state["pending_interrupt"] = True
            return self._send(200, {"ok": True})
        self._send(404, {"ok": False})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    log.info("speak_server v2 on :%d → engine %s (alive=%s)", PORT, ENGINE, engine_alive())
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()
