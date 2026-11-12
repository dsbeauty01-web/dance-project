"""motion_bank.py -- lane/live-motion 2026-10-25. The body of a Ditto live: a MOTION BANK (one mp4 = several long natural idle
segments + short gesture / product-action clips, every one starting and ending on the SAME key frame) and the scheduler that
decides, frame by frame, which bank frame Ditto bends the lips on.

Default OFF: only DITTO_BANK=<bank.json> (ditto_server.py) uses it; without it the server keeps the mirror loop of one idle clip.

Why: the live-trio idles were 3-5 s clips played forward-then-back, so a slow sway visibly reversed. Here the idle is 20-30 s of
segments played FORWARD only, in a shuffled order that never repeats the last one; any segment can follow any other because they
all start and end on the key frame. A gesture (wave, nod, point, hold up) or a product action (open the bag, turn it, put an
earbud in) starts at the next frame with a short crossfade from wherever the idle is, plays once, and ends on the key frame,
where a fresh idle segment begins. 'zoom' (a product close-up cut-in) is drawn by the server over the picture while the idle
continues underneath.

bank.json:
  {"video": "maya_bank.mp4", "fps": 25, "frames": N, "zoom_img": "product.png",
   "segments": [{"name": "maya_idle1", "kind": "idle", "start": 0, "end": 250}, {"name": "bag_turn", "kind": "gesture", ...}],
   "aliases": {"wave": "maya_wave", "laugh": "maya_nod", "show_closer": "bag_closer", "detail_zoom": "zoom", ...}}
"""
from __future__ import annotations

import json, os, random, threading, time
from collections import deque

E = os.environ.get


class Bank:
    def __init__(self, spec: dict, base_dir: str = "."):
        self.spec = spec; self.dir = base_dir
        self.fps = int(spec.get("fps", 25)); self.frames = int(spec["frames"])
        self.seg = {s["name"]: s for s in spec["segments"]}
        self.idle = [s["name"] for s in spec["segments"] if s.get("kind") == "idle"]
        self.aliases = dict(spec.get("aliases") or {})
        self.skip = set(spec.get("skip") or [])            # held (near-identical) frames, skipped so a hold is never a freeze
        if not self.idle: raise ValueError("motion bank: no idle segment")

    @classmethod
    def load(cls, path: str) -> "Bank":
        return cls(json.load(open(path)), os.path.dirname(os.path.abspath(path)))

    def video_path(self) -> str:
        return os.path.join(self.dir, self.spec["video"])

    def zoom_path(self) -> str | None:
        z = self.spec.get("zoom_img")
        return os.path.join(self.dir, z) if z else None

    def resolve(self, ev: dict) -> str | None:
        """event (brain Gesture API v1, or our own {"clip": ...}) -> a segment name, 'zoom', or None.
        Order: the clip it names (if the bank has it) -> its action -> its cue -> its fallback."""
        for key in ("clip", "action", "cue", "fallback"):
            v = ev.get(key)
            if not v: continue
            if v in self.seg and self.seg[v].get("kind") != "idle": return v
            a = self.aliases.get(v)
            if a == "zoom" or (a and a in self.seg): return a
            if v in ("zoom", "detail_zoom") and self.zoom_path(): return "zoom"
        return None


class Scheduler:
    """next_index() is called ONCE per generated frame, in order (Ditto's audio2motion thread). Each call also queues one
    instruction (idx, bg_idx, alpha, zoom_k) that the putback hook pops in the same order (putback is 1:1 and FIFO).
      idx    bank frame Ditto renders (face, pose and lips come from it)
      bg_idx -1, or the bank frame the picture is crossfaded FROM (alpha = weight of idx)
      zoom_k -1, or the frame number inside a zoom cut-in"""

    def __init__(self, bank: Bank, xfade: int | None = None, seed: int | None = None, clock=time.time):
        self.b = bank; self.clock = clock
        self.xf = int(xfade if xfade is not None else E("DITTO_GESTURE_XFADE", "8"))
        self.rng = random.Random(seed)
        self.lock = threading.Lock(); self.instr: deque = deque()
        self.cur = self._pick_idle(None); self.pos = 0; self.kind = "idle"
        self.pending: dict | None = None; self.blend: deque = deque()
        self.zoom_left = 0; self.zoom_n = 0; self.zoom_total = 0
        self.played: list = []; self.n = 0; self.last_idle = self.cur

    def _pick_idle(self, last):
        c = [s for s in self.b.idle if s != last] or self.b.idle
        return self.rng.choice(c)

    # ---- requests (any thread)
    def request(self, ev: dict) -> dict:
        name = self.b.resolve(ev)
        if not name: return {"ok": False, "why": "no clip", "ev": ev}
        pri = 2 if ev.get("type") == "product_action" or name == "zoom" else 1
        hold = float(ev.get("hold_s") or 3.0)
        with self.lock:
            if name == "zoom":
                n = int(round(max(1.5, min(6.0, hold)) * self.b.fps)) + 2 * self.xf
                self.zoom_left = self.zoom_total = n; self.zoom_n = 0
                self.played.append({"t": round(self.clock(), 3), "frame": self.n, "clip": "zoom", "ev": ev.get("seq")})
                return {"ok": True, "clip": "zoom"}
            if self.pending and self.pending["pri"] > pri: return {"ok": False, "why": "busy (higher priority pending)"}
            self.pending = {"name": name, "pri": pri, "t": self.clock(), "ev": ev}
        return {"ok": True, "clip": name, "queued": True}

    # ---- per frame (Ditto thread)
    def _start(self, name):
        s = self.b.seg[name]; self.played.append({"t": round(self.clock(), 3), "frame": self.n, "clip": name,
                                                  "ev": (self.pending or {}).get("ev", {}).get("seq")})
        if self.kind == "idle" and self.xf > 0:
            seg = self.b.seg[self.cur]; p = seg["start"] + self.pos; hi = (seg.get("raw") or [0, seg["end"]])[1]
            self.blend = deque((min(p + i, hi - 1), i / (self.xf + 1)) for i in range(1, self.xf + 1))
        self.cur, self.pos, self.kind = name, 0, "gesture"; self.pending = None

    def next_index(self, *_):
        with self.lock:
            if self.pending and (self.kind == "idle"):
                if self.clock() - self.pending["t"] > float(E("DITTO_GESTURE_STALE_S", "8")): self.pending = None
                else: self._start(self.pending["name"])
            seg = self.b.seg[self.cur]
            if seg["start"] + self.pos >= seg["end"]:
                # junction (lane/live-motion D3): segments are trimmed off their eased still ends; the next one fades in over the
                # outgoing clip's own raw tail for DITTO_JUNCTION_XFADE frames, so the cut is neither a freeze nor a jump
                xj = int(E("DITTO_JUNCTION_XFADE", "5")); hi = (seg.get("raw") or [0, seg["end"]])[1]
                jb = deque((min(seg["end"] + i, hi - 1), (i + 1) / (xj + 1)) for i in range(xj)) if xj > 0 and hi > seg["end"] else deque()
                if self.pending and self.clock() - self.pending["t"] <= float(E("DITTO_GESTURE_STALE_S", "8")):
                    self._start(self.pending["name"])
                else:
                    self.pending = None; nxt = self._pick_idle(self.last_idle if self.kind == "idle" else self.last_idle)
                    self.cur, self.pos, self.kind = nxt, 0, "idle"; self.last_idle = nxt
                if not self.blend: self.blend = jb
                seg = self.b.seg[self.cur]
            while self.b.skip and seg["start"] + self.pos in self.b.skip and seg["start"] + self.pos < seg["end"] - 1: self.pos += 1
            idx = seg["start"] + self.pos; self.pos += 1
            bg, alpha = -1, 1.0
            if self.blend:
                bg, alpha = self.blend.popleft()
            zk = -1
            if self.zoom_left > 0:
                zk = self.zoom_n; self.zoom_n += 1; self.zoom_left -= 1
            self.instr.append((idx, bg, alpha, zk, self.zoom_total))
            self.n += 1
            return idx

    def pop(self):
        try: return self.instr.popleft()
        except IndexError: return None

    def status(self) -> dict:
        with self.lock:
            return {"cur": self.cur, "kind": self.kind, "pos": self.pos, "pending": (self.pending or {}).get("name"),
                    "zoom_left": self.zoom_left, "frames": self.n, "played": self.played[-12:], "n_played": len(self.played)}


def zoom_alpha(k: int, total: int, xf: int) -> float:
    """cut-in opacity for frame k of a zoom of `total` frames: ramp in over xf, hold, ramp out over xf"""
    if total <= 0 or k < 0: return 0.0
    if k < xf: return (k + 1) / (xf + 1)
    if k >= total - xf: return max(0.0, (total - k) / (xf + 1))
    return 1.0


class ZoomCard:
    """the product close-up cut-in: the product photo over a soft blurred bed of itself, slow push-in (Ken Burns 1.00 -> 1.10)"""

    def __init__(self, img_path: str, w: int, h: int):
        import cv2, numpy as np
        self.cv2, self.np = cv2, np
        im = cv2.imread(img_path, cv2.IMREAD_COLOR)
        if im is None: raise FileNotFoundError(img_path)
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)                       # Ditto's putback works in RGB
        self.w, self.h = w, h
        bed = cv2.resize(im, (w, int(round(im.shape[0] * w / im.shape[1]))))
        bed = cv2.resize(bed, (w, h)); bed = cv2.GaussianBlur(bed, (0, 0), 40)
        bed = (bed.astype(np.float32) * 0.55 + 20).clip(0, 255).astype(np.uint8)
        s = min(w * 0.92 / im.shape[1], h * 0.62 / im.shape[0])
        pw, ph = int(im.shape[1] * s), int(im.shape[0] * s)
        prod = cv2.resize(im, (pw, ph), interpolation=cv2.INTER_LANCZOS4 if s > 1 else cv2.INTER_AREA)
        base = bed.copy(); x0, y0 = (w - pw) // 2, int(h * 0.40 - ph / 2)
        base[y0:y0 + ph, x0:x0 + pw] = prod
        self.base = base

    def frame(self, k: int, total: int):
        cv2 = self.cv2
        z = 1.0 + 0.10 * (k / max(1, total - 1))
        M = cv2.getRotationMatrix2D((self.w / 2, self.h * 0.40), 0, z)
        return cv2.warpAffine(self.base, M, (self.w, self.h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
