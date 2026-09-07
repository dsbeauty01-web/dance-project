#!/usr/bin/env python3
"""
gesture_router.py — gestures, reactions, and instant acknowledgments for the slot stream.

CONTRACT (what this file expects — adapt the two URLs if yours differ, nothing else):
  SLOT_URL   POST {SLOT_URL}/insert  {"clip": "/abs/path.mp4", "priority": 0-9}  → inserts a clip into the next slot(s)
  RENDER_URL POST {RENDER_URL}/render {"text": "..."}  → {"clip": "/abs/path.mp4"}    (warm MuseTalk answer render)

SERVES (maya_host hooks):
  POST /scene {"scene": "IDLE|LISTEN|SPEAK|PITCH|SHOW|POINT|WAVE|CUT_APPLY|CUT_EXAMINE"}
       → inserts a random clip variant for that scene from LIB/<scene>/*.mp4 (silent gestures)
  POST /ack   {"name": "Dana"}  → inserts a pre-rendered acknowledgment clip within ~1 slot
       (from ACK_DIR/*.mp4, produced by precache_ack.py) — the "she heard you" beat in ≤2-5s
  POST /speak {"text": "..."}   → render_server → landscape → insert (full spoken answer)
  GET  /health

IDLE MICRO-BEATS: if nothing was inserted for IDLE_BEAT_SEC (20-40s random), insert a random
  LIB/IDLE/*.mp4 variant so she never looks frozen. Disabled while an answer is queued.

ENV: SLOT_URL=http://127.0.0.1:8792  RENDER_URL=http://127.0.0.1:8793  GESTURE_LIB=/workspace/maya-ops/bake/gestures
     ACK_DIR=/workspace/maya-ops/bake/ack  ROUTER_PORT=8791  IDLE_BEAT_MIN=20 IDLE_BEAT_MAX=40  LANDSCAPE=1
LIB layout:  gestures/IDLE/*.mp4  gestures/LISTEN/*.mp4  gestures/SHOW/*.mp4  gestures/POINT/*.mp4 ...
             (put ≥2 variants per folder; missing folder = scene ignored, logged once)
"""
import glob, json, logging, os, random, subprocess, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

E = os.environ.get
SLOT = E("SLOT_URL", "http://127.0.0.1:8792").rstrip("/")
RENDER = E("RENDER_URL", "http://127.0.0.1:8793").rstrip("/")
LIB = E("GESTURE_LIB", "/workspace/maya-ops/bake/gestures")
ACK_DIR = E("ACK_DIR", "/workspace/maya-ops/bake/ack")
PORT = int(E("ROUTER_PORT", "8791"))
IDLE_MIN, IDLE_MAX = int(E("IDLE_BEAT_MIN", "20")), int(E("IDLE_BEAT_MAX", "40"))
LANDSCAPE = E("LANDSCAPE", "1") == "1"
HERE = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(level=logging.INFO, format="%(asctime)s router: %(message)s")
log = logging.getLogger()
state = {"last_insert": time.time(), "answer_queued": False, "missing_warned": set(), "inserted": 0}
lock = threading.Lock()

# keyword → gesture used when the answer text is rendered (SHOW/POINT ride along the answer)
GESTURE_HINTS = [
    (("price", "shekel", "149", "cost", "link", "type me"), "POINT"),
    (("serum", "bottle", "drop", "vitamin"), "SHOW"),
    (("welcome", "hi ", "hey", "hello"), "WAVE"),
]


def pick(scene: str):
    files = sorted(glob.glob(os.path.join(LIB, scene, "*.mp4")))
    if not files:
        if scene not in state["missing_warned"]:
            state["missing_warned"].add(scene); log.warning("no clips for scene %s (%s/%s/*.mp4)", scene, LIB, scene)
        return None
    return random.choice(files)


def insert(clip: str, priority: int = 5) -> bool:
    try:
        r = requests.post(SLOT + "/insert", json={"clip": clip, "priority": priority}, timeout=5)
        ok = r.status_code < 300
    except Exception as e:
        log.error("slot insert failed: %s", e); ok = False
    if ok:
        with lock:
            state["last_insert"] = time.time(); state["inserted"] += 1
        log.info("inserted p%d %s", priority, os.path.basename(clip))
    return ok


def to_landscape(path: str) -> str:
    if not LANDSCAPE:
        return path
    out = path.replace(".mp4", "_1080.mp4")
    try:
        subprocess.run(["python3", os.path.join(HERE, "to_landscape.py"), path, out], check=True, capture_output=True)
        return out
    except Exception as e:
        log.warning("landscape convert failed (%s) — using original", e); return path


def speak(text: str):
    with lock:
        state["answer_queued"] = True
    try:
        gesture = next((g for keys, g in GESTURE_HINTS if any(k in text.lower() for k in keys)), None)
        if gesture:
            c = pick(gesture)
            if c:
                insert(c, priority=2)  # gesture beat right before she talks
        r = requests.post(RENDER + "/render", json={"text": text}, timeout=120)
        clip = r.json().get("clip")
        if not clip:
            log.error("render returned no clip: %s", r.text[:200]); return
        insert(to_landscape(clip), priority=1)
    finally:
        with lock:
            state["answer_queued"] = False


def ack(name: str = ""):
    files = sorted(glob.glob(os.path.join(ACK_DIR, "*.mp4")))
    named = [f for f in files if name and os.path.basename(f).lower().startswith(name.lower() + "_")]
    pool = named or [f for f in files if os.path.basename(f).startswith("generic_")] or files
    if not pool:
        log.warning("no ack clips in %s — run precache_ack.py", ACK_DIR); return False
    return insert(random.choice(pool), priority=0)


def idle_beats():
    while True:
        wait = random.randint(IDLE_MIN, IDLE_MAX)
        time.sleep(5)
        with lock:
            due = (time.time() - state["last_insert"]) >= wait and not state["answer_queued"]
        if due:
            c = pick("IDLE")
            if c:
                insert(c, priority=8)


class H(BaseHTTPRequestHandler):
    def _j(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def _s(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        with lock:
            s = dict(state); s["missing_warned"] = sorted(s["missing_warned"])
        self._s(200, {"ok": True, **s, "slot": SLOT, "render": RENDER})

    def do_POST(self):
        j = self._j()
        if self.path == "/scene":
            c = pick(j.get("scene", "IDLE"))
            return self._s(200, {"ok": bool(c and insert(c, 6))})
        if self.path == "/ack":
            return self._s(200, {"ok": ack(j.get("name", ""))})
        if self.path == "/speak":
            t = (j.get("text") or "").strip()
            if not t:
                return self._s(400, {"ok": False})
            threading.Thread(target=speak, args=(t,), daemon=True).start()
            return self._s(202, {"ok": True})
        self._s(404, {"ok": False})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    threading.Thread(target=idle_beats, daemon=True).start()
    log.info("gesture_router on :%d  lib=%s ack=%s slot=%s render=%s", PORT, LIB, ACK_DIR, SLOT, RENDER)
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()
