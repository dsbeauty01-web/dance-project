#!/usr/bin/env python3
"""
director.py — the on-screen SELLING layer. Sits between OpenTalking's output and Facebook/Amazon/YouTube.

   OpenTalking ──RTMPS──▶ mediamtx (local) ──RTSP──▶ director.py (composite) ──RTMP──▶ Facebook (+Amazon, +YouTube)

What it draws on top of Maya (all switchable live over HTTP, no restart):
   · PRODUCT PiP (corner) or FULL cutaway (macro/apply clip loops) while her voice keeps going
   · PRICE BANNER (product · live price · reg price · "type ME")
   · CHAT OVERLAY (last 4 comments + her replies, names highlighted)
   · RESPONSE TIMER ("last reply: 2.6s") + AI-host label
   · Audio passes through untouched (lips stay in sync; offset configurable)

   python director.py --source rtsp://127.0.0.1:8554/maya --targets fb            # live
   python director.py --source test --targets file:/tmp/out.flv --seconds 20      # self-test, no stream

CONTROL (POST JSON to :8796):
   /scene  {"scene": "HOST"|"PIP"|"CUTAWAY", "clip": "apply"|"examine"|"hero"}   /banner {"on": true, "price": "149", "reg": "249", "product": "Vitamin C Serum · 20% · 30 ml"}
   /chat   {"name": "Dana", "text": "how much?", "reply": "Dana — 149 shekels…", "latency": 2.6}   /timer {"seconds": 2.6}
   GET /health

ENV: DIRECTOR_PORT=8796  CLIPS_DIR=/workspace/maya-ops/bake/src1080 (files: cutaway_apply*.mp4, cutaway_examine*.mp4, hero*.mp4)
     AUDIO_OFFSET_MS=180 (delay audio to match the video path) · FB_RTMP_URL / AMAZON_* / YT_* for push targets (same as push.py)
Requires: ffmpeg, numpy, Pillow. CPU-only compositing at 1080p25 (≈ 15-25 ms/frame with cached overlays).
"""
import argparse, json, os, subprocess, sys, threading, time, glob, queue
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 25
E = os.environ.get
for p in (os.path.expanduser("~/.maya/host.env"), os.path.expanduser("~/.maya/amazon.env")):
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1); os.environ.setdefault(k, v.strip().strip('"'))
CLIPS = E("CLIPS_DIR", "/workspace/maya-ops/bake/src1080")
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"; FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
GOLD = (255, 209, 102, 255); WHITE = (255, 255, 255, 255)


def log(m):
    print(f"[director {time.strftime('%H:%M:%S')}] {m}", flush=True)


# ------------------------------------------------------------------ state + overlays
class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.scene, self.clip = "HOST", "apply"
        self.banner = {"on": True, "price": E("SHOWCASE_PRICE", "149"), "reg": E("SHOWCASE_REG", "249"), "product": E("SHOWCASE_PRODUCT", "Vitamin C Serum · 20% · 30 ml"), "cta": "Tap the link below · or type ME"}
        self.chat: list = []
        self.timer = None
        self.version = 0
        self._layer = None; self._layer_ver = -1
        self.frames_out = 0; self.started = time.time()

    def bump(self):
        self.version += 1

    def layer(self) -> np.ndarray:
        """RGBA overlay (banner + chat + label + timer), re-rendered only when state changes."""
        with self.lock:
            if self._layer is not None and self._layer_ver == self.version:
                return self._layer
            im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            fb, fr, fs, fp = ImageFont.truetype(FONT_B, 34), ImageFont.truetype(FONT_R, 28), ImageFont.truetype(FONT_R, 24), ImageFont.truetype(FONT_B, 76)
            # AI label
            d.rounded_rectangle([40, 40, 470, 100], 12, fill=(0, 0, 0, 150)); d.ellipse([58, 60, 78, 80], fill=(255, 59, 48, 255))
            d.text((92, 52), "AI host — Maya — LIVE", font=fb, fill=WHITE)
            # timer
            if self.timer is not None:
                d.rounded_rectangle([1560, 40, 1880, 100], 12, fill=(0, 0, 0, 150)); d.text((1580, 54), f"last reply: {self.timer:.1f}s", font=fb, fill=GOLD)
            # chat (last 4)
            y = 140
            for c in self.chat[-4:]:
                d.rounded_rectangle([40, y - 10, 700, y + 78], 10, fill=(0, 0, 0, 140))
                d.text((60, y), f"{c['name']}: {c['text'][:44]}", font=fr, fill=WHITE)
                if c.get("reply"):
                    d.text((60, y + 36), f"↳ {c['reply'][:52]}", font=fs, fill=GOLD)
                y += 100
            # banner
            b = self.banner
            if b.get("on"):
                d.rectangle([0, 900, W, H], fill=(8, 10, 16, 200)); d.rectangle([0, 900, W, 904], fill=GOLD)
                d.text((60, 925), b["product"], font=ImageFont.truetype(FONT_B, 46), fill=WHITE)
                d.text((60, 995), b["cta"], font=fr, fill=GOLD)
                d.text((1380, 915), "LIVE PRICE", font=fr, fill=GOLD); d.text((1380, 945), f"₪{b['price']}", font=fp, fill=GOLD)
                if b.get("reg"):
                    d.text((1700, 1000), f"reg ₪{b['reg']}", font=fr, fill=(230, 230, 230, 255))
            arr = np.asarray(im).copy()
            a = arr[:, :, 3]
            rows = np.where(a.any(axis=1))[0]
            boxes = []
            if len(rows):
                start = rows[0]; prev = rows[0]
                for r in rows[1:]:
                    if r != prev + 1:
                        boxes.append((start, prev + 1)); start = r
                    prev = r
                boxes.append((start, prev + 1))
            self._boxes = []
            for y0, y1 in boxes:
                cols = np.where(a[y0:y1].any(axis=0))[0]
                self._boxes.append((y0, y1, cols[0], cols[-1] + 1))
            self._layer = arr; self._layer_ver = self.version
            return self._layer

    def boxes(self):
        return getattr(self, "_boxes", [])


ST = State()


def alpha_over(base: np.ndarray, layer: np.ndarray, boxes):
    """In-place alpha blend of an RGBA layer onto RGB base, only inside the layer's opaque boxes (integer math)."""
    for y0, y1, x0, x1 in boxes:
        L = layer[y0:y1, x0:x1]; a = L[:, :, 3:4].astype(np.uint16)
        roi = base[y0:y1, x0:x1]
        roi[:] = ((L[:, :, :3].astype(np.uint16) * a + roi.astype(np.uint16) * (255 - a)) // 255).astype(np.uint8)


# ------------------------------------------------------------------ clip source (loops a product clip as frames)
class ClipSource:
    def __init__(self):
        self.proc = None; self.name = None

    def _path(self, name):
        for pat in (f"cutaway_{name}*.mp4", f"{name}*.mp4", "*.mp4"):
            hits = sorted(glob.glob(os.path.join(CLIPS, pat)))
            if hits:
                return hits[0]
        return None

    def frame(self, name: str, size):
        if self.name != name or self.proc is None or self.proc.poll() is not None:
            self.close(); p = self._path(name)
            if not p:
                return None
            self.proc = subprocess.Popen(["ffmpeg", "-v", "error", "-stream_loop", "-1", "-re", "-i", p, "-vf", f"scale={size[0]}:{size[1]}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10 ** 7)
            self.name = name
        raw = self.proc.stdout.read(size[0] * size[1] * 3)
        return np.frombuffer(raw, np.uint8).reshape(size[1], size[0], 3) if len(raw) == size[0] * size[1] * 3 else None

    def close(self):
        if self.proc:
            self.proc.kill(); self.proc = None


CLIP = ClipSource()


# ------------------------------------------------------------------ pipeline
def has_nvenc() -> bool:
    if E("DIRECTOR_FORCE_X264") == "1":
        return False
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=10).stdout
        if "h264_nvenc" not in out:
            return False
        t = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=64x64:r=1", "-frames:v", "1", "-c:v", "h264_nvenc", "-f", "null", "-"], capture_output=True, timeout=15)
        return t.returncode == 0  # nvenc listed AND usable (a GPU is present)
    except Exception:
        return False


def build_encoder(source: str, targets: list, seconds: int) -> list:
    from push import target_url  # same env/targets as push.py
    tees = []
    for t in targets:
        if t.startswith("file:"):
            tees.append(f"[f=flv]{t[5:]}")
        else:
            tees.append(f"[f=flv:onfail=ignore]{target_url(t)}")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if source == "test":
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100"]
    else:
        cmd += ["-itsoffset", f"{int(E('AUDIO_OFFSET_MS', '180')) / 1000:.3f}", "-i", source]
    venc = ["-c:v", "h264_nvenc", "-preset", "p4", "-tune", "ll", "-rc", "cbr", "-b:v", "4500k", "-maxrate", "4500k", "-bufsize", "9000k"] if has_nvenc() else \
           ["-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency", "-b:v", "4500k", "-maxrate", "4500k", "-bufsize", "9000k"]
    cmd += ["-map", "0:v", "-map", "1:a"] + venc + ["-g", "50", "-keyint_min", "50", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", "-shortest"]
    if seconds:
        cmd += ["-t", str(seconds)]
    cmd += ["-flags", "+global_header", "-f", "tee", "|".join(tees)]
    return cmd


def decoder(source: str) -> subprocess.Popen:
    if source == "test":
        cmd = ["ffmpeg", "-v", "error", "-re", "-f", "lavfi", "-i", f"testsrc2=size={W}x{H}:rate={FPS}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    else:
        cmd = ["ffmpeg", "-v", "error", "-rtsp_transport", "tcp", "-i", source, "-vf", f"scale={W}:{H},fps={FPS}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10 ** 8)


def run(source: str, targets: list, seconds: int):
    dec = decoder(source)
    enc = subprocess.Popen(build_encoder(source, targets, seconds), stdin=subprocess.PIPE)
    n = W * H * 3; pip_size = (576, 324); pip_pos = (W - 576 - 60, 120)
    log(f"pipeline up: {source} → {targets}")
    while True:
        raw = dec.stdout.read(n)
        if len(raw) != n:
            log("decoder ended"); break
        frame = np.frombuffer(raw, np.uint8).copy().reshape(H, W, 3)
        with ST.lock:
            scene, clip = ST.scene, ST.clip
        if scene == "CUTAWAY":
            f = CLIP.frame(clip, (W, H))
            if f is not None:
                frame = f.copy()
        elif scene == "PIP":
            f = CLIP.frame(clip, pip_size)
            if f is not None:
                x, y = pip_pos; frame[y:y + pip_size[1], x:x + pip_size[0]] = f
                frame[y - 4:y, x - 4:x + pip_size[0] + 4] = frame[y + pip_size[1]:y + pip_size[1] + 4, x - 4:x + pip_size[0] + 4] = (255, 209, 102)
        else:
            CLIP.close()
        layer = ST.layer(); alpha_over(frame, layer, ST.boxes())
        try:
            enc.stdin.write(frame.tobytes())
        except BrokenPipeError:
            log("encoder closed"); break
        ST.frames_out += 1
        if ST.frames_out % 250 == 0:
            log(f"frames={ST.frames_out} avg_fps={ST.frames_out / max(1, time.time() - ST.started):.1f}")
    try:
        enc.stdin.close(); enc.wait(timeout=20)
    except Exception:
        enc.kill()
    dec.kill(); CLIP.close()


# ------------------------------------------------------------------ control API
class Ctl(BaseHTTPRequestHandler):
    def _j(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def _s(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        self._s(200, {"ok": True, "scene": ST.scene, "clip": ST.clip, "banner": ST.banner["on"], "chat": len(ST.chat), "frames_out": ST.frames_out,
                      "fps_avg": round(ST.frames_out / max(1, time.time() - ST.started), 1)})

    def do_POST(self):
        j = self._j()
        with ST.lock:
            if self.path == "/scene":
                ST.scene = j.get("scene", "HOST").upper(); ST.clip = j.get("clip", ST.clip)
            elif self.path == "/banner":
                ST.banner.update({k: v for k, v in j.items() if k in ("on", "price", "reg", "product", "cta")})
            elif self.path == "/chat":
                if j.get("name"):
                    ST.chat.append({"name": j["name"], "text": j.get("text", ""), "reply": j.get("reply", "")}); ST.chat = ST.chat[-8:]
                if j.get("latency") is not None:
                    ST.timer = float(j["latency"])
            elif self.path == "/timer":
                ST.timer = float(j.get("seconds", 0))
            else:
                return self._s(404, {"ok": False})
            ST.bump()
        self._s(200, {"ok": True})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--source", default="rtsp://127.0.0.1:8554/maya"); ap.add_argument("--targets", default="fb")
    ap.add_argument("--seconds", type=int, default=0); a = ap.parse_args()
    threading.Thread(target=lambda: ThreadingHTTPServer(("0.0.0.0", int(E("DIRECTOR_PORT", "8796"))), Ctl).serve_forever(), daemon=True).start()
    log(f"control on :{E('DIRECTOR_PORT', '8796')}")
    while True:
        run(a.source, [t.strip() for t in a.targets.split(",") if t.strip()], a.seconds)
        if a.seconds:
            break
        log("restarting pipeline in 3s"); time.sleep(3)
