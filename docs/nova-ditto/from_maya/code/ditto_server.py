#!/usr/bin/env python3
"""ditto_server.py -- Ditto (antgroup/ditto-talkinghead, Apache-2.0) as a LIVE renderer, in its own venv (TRT 8.6.1 engines),
served over HTTP to the shim (ditto_renderer.py). lane/live-trio 2026-10-25. Default OFF: only SHIM_RENDERER=ditto_renderer:Renderer
starts it. Port of bench/replace_musetalk_alt/ditto_wide.py (lane/replace-musetalk-alt), turned from a clip renderer into a stream:

  * source = the character's idle VIDEO at figure framing (1080x1920, face ~200-320 px, mouth closed). Output frame t is source
    frame mirror(t), so body, hands, hair and eyes are the real footage; only the 6 lip keypoints come from the audio
    (use_d_keys={"exp": DITTO_AMP}, video mode).
  * DITTO_AMP (default 0.6): the calm knob. 0.8 = the alt lane's proof ("her lips are very big" -- Refael); 0.55-0.65 asked.
  * our paste-back: only the lower face (under the nostrils, past the chin, cheek to cheek, wide feather), Lanczos, skin-ring
    colour match (bench LowerPutBack). Hand gate: source frames listed in <src>.gate.json get NO paste (her own frame).
  * silence gate: Ditto's vad_alpha per frame from the audio level (bench vad_alpha, causal + 2 frames lookahead) -> in pauses
    the lips fade back to her own closed mouth from the video.
  * one session for the whole show, never closed. The shim calls /render with exactly CHUNK frames of audio; the server feeds it
    in Ditto's 0.2 s hubert steps and returns CHUNK frames from its output FIFO. The FIFO is primed with DITTO_PRIME frames of
    silence at boot, so every returned frame is exactly DITTO_PRIME frames behind the audio just fed -> the shim delays its audio
    by the same amount (SHIM_AV_OFFSET_MS = -40 * DITTO_PRIME). Constant, so lips and voice stay locked.
  * frames go through /dev/shm (one .npy per chunk, 25 x 1080x1920x3 = 155 MB/s is too much for an HTTP body).
  * threads capped (OMP_NUM_THREADS, cv2.setNumThreads): the pod's CPU quota is ~18 cores although nproc says 128.
  * no InsightFace (non-commercial): first-frame crop from MediaPipe, later frames tracked by Ditto's 203-point landmarker.

API  GET  /health -> {"ready", "chunk_frames", "chunk_samples", "fps", "prime", "info", "renders", "ms_p95", "error"}
     POST /render  body = float32 mono 16 kHz, chunk_samples -> JSON {"path": "/dev/shm/...npy", "n", "h", "w"} (BGR uint8)
MOTION BANK (lane/live-motion, default OFF): DITTO_BANK=<bank.json> (motion_bank.py) replaces DITTO_SRC with the bank video and
     the mirror loop with a scheduler: long natural idle segments played forward in a shuffled order, gestures / product actions on
     demand (POST /gesture {"clip"|"action"|"cue", "hold_s"}), crossfade in, back to idle on the shared key frame, and the 'zoom'
     product cut-in drawn over the picture. Ditto still draws only the lips, on whatever bank frame is playing.
Env  DITTO_ROOT (/workspace/ditto) · DITTO_SRC (idle mp4) · DITTO_PORT 8031 · DITTO_AMP 0.6 · DITTO_CHUNK 25 · DITTO_PRIME 25
     DITTO_VAD 1 · DITTO_OUT_W/H (0 = source size) · DITTO_LM (face_landmarker.task) · DITTO_MASK lower|full
"""
import json, math, os, sys, threading, time, traceback
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import cv2

E = os.environ.get
if E("OMP_NUM_THREADS"): cv2.setNumThreads(int(E("OMP_NUM_THREADS")))
SR, FPS = 16000, 25
CH = (3, 5, 2); HOP = CH[1] * 640; WIN = int(sum(CH) * 0.04 * SR) + 80; PRE = CH[0] * 640
HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.abspath(os.path.join(HERE, "..", "..", "bench", "replace_musetalk_alt"))
sys.path.insert(0, BENCH)
import ditto_wide as DW            # noqa: E402  (LowerPutBack, vad_alpha, patch_first_frame_crop, mp_landmarker)


class Collector:
    """Ditto's writer: every finished frame (RGB) lands in the FIFO, converted to BGR (and resized if DITTO_OUT_W/H)."""
    def __init__(self, out_wh):
        self.q = deque(); self.cv = threading.Condition(); self.n = 0; self.out_wh = out_wh; self.last = None

    def __call__(self, img, fmt="rgb"):
        f = cv2.cvtColor(np.ascontiguousarray(img, dtype=np.uint8), cv2.COLOR_RGB2BGR)
        if self.out_wh and (f.shape[1], f.shape[0]) != self.out_wh:
            f = cv2.resize(f, self.out_wh, interpolation=cv2.INTER_AREA)
        with self.cv:
            self.q.append(f); self.n += 1; self.last = f; self.cv.notify_all()

    def close(self): pass

    def take(self, n, timeout):
        t_end = time.time() + timeout
        with self.cv:
            while len(self.q) < n:
                left = t_end - time.time()
                if left <= 0: break
                self.cv.wait(left)
            k = min(n, len(self.q)); out = [self.q.popleft() for _ in range(k)]
        return out


class Engine:
    def __init__(self):
        self.info = {}; self.ready = False; self.error = None; self.renders = 0; self.ms = deque(maxlen=500); self.late = 0
        self.chunk = int(E("DITTO_CHUNK", "25")); self.prime = int(E("DITTO_PRIME", "25"))
        self.lock = threading.Lock(); self.fed = 0; self.k = 0; self.debt = 0

    def load(self):
        root = E("DITTO_ROOT", "/workspace/ditto"); src = E("DITTO_SRC"); amp = float(E("DITTO_AMP", "0.6"))
        lm = E("DITTO_LM", f"{root}/face_landmarker.task")
        self.sched = None; self.zoom = None
        if E("DITTO_BANK"):                                                # lane/live-motion: the motion bank (default off)
            sys.path.insert(0, HERE)
            import motion_bank as MB
            self.MB = MB; bank = MB.Bank.load(E("DITTO_BANK")); src = bank.video_path(); self.sched = MB.Scheduler(bank)
        sys.path.insert(0, f"{root}/src"); os.chdir(f"{root}/src")
        DW.patch_first_frame_crop(lm)
        if E("DITTO_EYE_HOLD", "0") == "1":                                # lane/motion-transfer EDGE ladder (default off)
            # Stock Ditto registers a video source frame by frame and asks MediaPipe-478 for the EYES of every crop. On a
            # turned head (profile) that model finds nothing, get() returns None and register() dies with
            # "'NoneType' object has no attribute 'reshape'" -> the whole source fails to load (measured: edge-prof
            # sj8iot7umbvn78). Eyes are not driven in video mode (drive_eye False), so hold the last good eye landmarks.
            import core.aux_models.mediapipe_landmark478 as LM478
            _orig_call = LM478.Landmark478.__call__
            eng_hold = self; eng_hold.eye_holds = 0; eng_hold._last478 = None

            def _held(this, image):
                if this.model_type != "ori":
                    l = this.get(image)
                    if l is None:
                        eng_hold.eye_holds += 1
                        if eng_hold._last478 is not None: return eng_hold._last478
                        raise RuntimeError("DITTO_EYE_HOLD: no eye landmarks on the first source frame")
                    out = l.reshape(1, -1, 3).astype(np.float32); eng_hold._last478 = out; return out
                return _orig_call(this, image)
            LM478.Landmark478.__call__ = _held
        import stream_pipeline_online as SPO
        from stream_pipeline_online import StreamSDK
        if self.sched is not None:
            SPO._mirror_index = self.sched.next_index                      # Ditto asks "which source frame" once per output frame
        t0 = time.time()
        sdk = StreamSDK(f"{root}/ckpt/ditto_cfg/v0.4_hubert_cfg_trt_online.pkl", f"{root}/ckpt/ditto_trt_Ampere_Plus")
        pb = DW.LowerPutBack(E("DITTO_MASK", "lower"), lm, debug_dir=E("MAYA_LOGS", "/workspace/logs")); self.pb = pb
        gate_p = os.path.splitext(src)[0] + ".gate.json"
        self.gate = set(json.load(open(gate_p)).get("no_paste", [])) if os.path.exists(gate_p) else set()
        cap = cv2.VideoCapture(src); nsrc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); sw, sh = int(cap.get(3)), int(cap.get(4)); cap.release()
        ow, oh = int(E("DITTO_OUT_W", "0")), int(E("DITTO_OUT_H", "0"))
        self.col = Collector((ow, oh) if ow and oh else None)
        eng = self

        def gated_putback(frame_rgb, render, M_c2o):
            if eng.sched is not None: return eng._bank_putback(frame_rgb, render, M_c2o)
            # the hand gate, by SOURCE frame: the stock worker hands us source_info["img_rgb_lst"][i] itself, so its id() is i
            if eng._gate_ids and id(frame_rgb) in eng._gate_ids: return frame_rgb
            return pb(frame_rgb, render, M_c2o)
        self._gate_ids = set()
        sdk.putback = gated_putback
        sdk.setup(src, "/tmp/ditto_unused.mp4", use_d_keys={"exp": amp}, template_n_frames=nsrc)
        sdk.setup_Nd(N_d=10 ** 7)
        try: sdk.writer.close()
        except Exception: pass
        sdk.writer = self.col
        lst = sdk.source_info["img_rgb_lst"]
        self._gate_ids = {id(lst[i]) for i in self.gate if 0 <= i < len(lst)}
        self.sdk = sdk
        if self.sched is not None:
            zp = self.sched.b.zoom_path() or E("SHIM_PRODUCT_IMG")
            try: self.zoom = self.MB.ZoomCard(zp, sw, sh) if zp else None
            except Exception as e: print(f"[ditto_server] zoom card unavailable: {e}", flush=True)
            self.mismatch = 0
        self.info = {"src": os.path.basename(src), "src_frames": nsrc, "src_wh": [sw, sh], "amp": amp, "gate_frames": len(self.gate),
                     "out_wh": list(self.col.out_wh) if self.col.out_wh else [sw, sh], "setup_s": round(time.time() - t0, 1),
                     "bank": E("DITTO_BANK") or None, "zoom": bool(self.zoom), "eye_holds": getattr(self, "eye_holds", None)}
        # prime: DITTO_PRIME frames of silence -> the FIFO holds them, every later frame is exactly that far behind its audio
        self._feed(np.zeros(self.prime * 640, np.float32), vad=True)
        got = 0; t1 = time.time()
        while time.time() - t1 < 120:
            with self.col.cv: got = len(self.col.q)
            if got >= self.prime - 12: break                     # Ditto emits in 10-frame steps (+2 lookahead): the rest follows
            if sdk.stop_event.is_set(): raise RuntimeError(f"ditto worker died: {sdk.worker_exception!r}")
            time.sleep(0.05)
        # warm the clock: a few silent chunks through the full request path (TRT first-call costs never on air)
        for _ in range(3): self.render(np.zeros(self.chunk * 640, np.float32))
        self.renders = 0; self.ms.clear(); self.late = 0
        self.info["prime_s"] = round(time.time() - t1, 1)
        self.ready = True
        print(f"[ditto_server] ready {json.dumps(self.info)}", flush=True)

    def _bank_putback(self, frame_rgb, render, M_c2o):
        """motion bank: the instruction the scheduler queued for THIS output frame (same order as Ditto's frames)"""
        ins = self.sched.pop()
        lst = self.sdk.source_info["img_rgb_lst"]
        if ins is None:
            return frame_rgb if id(frame_rgb) in self._gate_ids else self.pb(frame_rgb, render, M_c2o)
        idx, bg, alpha, zk, ztot = ins
        if lst[idx] is not frame_rgb: self.mismatch += 1                 # never seen; counted in /health
        f = frame_rgb
        if bg >= 0: f = cv2.addWeighted(frame_rgb, alpha, lst[bg], 1.0 - alpha, 0.0)
        out = f if idx in self.gate else self.pb(f, render, M_c2o)
        if zk >= 0 and self.zoom is not None:
            a = self.MB.zoom_alpha(zk, ztot, self.sched.xf)
            out = cv2.addWeighted(self.zoom.frame(zk, ztot), a, out, 1.0 - a, 0.0) if a < 1 else self.zoom.frame(zk, ztot)
        return out

    def gesture(self, ev):
        if self.sched is None: return {"ok": False, "why": "no motion bank (DITTO_BANK unset)"}
        r = self.sched.request(ev)
        try:
            with open(os.path.join(E("MAYA_LOGS", "/workspace/logs"), "proof_gesture_server.jsonl"), "a") as f:
                f.write(json.dumps({"t": round(time.time(), 3), "ev": ev, "r": r}, ensure_ascii=False) + "\n")
        except Exception: pass
        return r

    def _feed(self, audio, vad=True):
        """audio (16 kHz float32, n x 640 samples) -> Ditto in its 0.2 s hubert steps (bench stream(): window = 3 frames before,
        5 new, 2 after + 80 samples), with the per-frame silence gate. A step runs once its 2-frame lookahead has arrived."""
        n = len(audio) // 640; f0 = self.fed
        if vad and E("DITTO_VAD", "1") == "1":
            va = DW.vad_alpha(audio, n)
            for i, v in enumerate(va): self.sdk.ctrl_info[f0 + i] = {"vad_alpha": float(max(v, 1e-3))}
            for k in [k for k in list(self.sdk.ctrl_info) if isinstance(k, int) and k < f0 - 400]: self.sdk.ctrl_info.pop(k, None)
        if not hasattr(self, "_x"): self._x = np.zeros(PRE, np.float32)            # left context of step 0 = silence
        self._x = np.concatenate([self._x, audio[:n * 640]])
        while len(self._x) >= WIN:
            self.sdk.run_chunk(self._x[:WIN], CH)
            self._x = self._x[HOP:]
        self.fed += n

    def render(self, audio):
        t = time.time()
        with self.lock:
            a = np.asarray(audio, np.float32)
            want = self.chunk * 640
            if len(a) != want: a = np.pad(a, (0, max(0, want - len(a))))[:want]
            self._feed(a)
            if self.debt:                                                   # frames we already covered with a hold: drop them
                with self.col.cv:
                    while self.debt and len(self.col.q) > self.chunk: self.col.q.popleft(); self.debt -= 1
            frames = self.col.take(self.chunk, float(E("DITTO_TAKE_TIMEOUT", "0.9")))
            if len(frames) < self.chunk:                                    # late: hold the last frame, never stop the clock
                self.late += 1; self.debt += self.chunk - len(frames)        # ...and drop as many later, so the A/V lag stays fixed
                last = frames[-1] if frames else self.col.last
                frames += [last] * (self.chunk - len(frames))
            if self.sdk.stop_event.is_set(): raise RuntimeError(f"ditto worker died: {self.sdk.worker_exception!r}")
            self.k += 1; p = f"/dev/shm/ditto_{os.getpid()}_{self.k % 8}.npy"
            np.save(p, np.stack(frames))
            self.renders += 1; self.ms.append((time.time() - t) * 1000)
            if E("DITTO_STATS_EVERY") and self.renders % int(E("DITTO_STATS_EVERY")) == 0:     # lane/live-motion diagnostics
                with self.col.cv: qn = len(self.col.q)
                print(f"[ditto_server] stats renders={self.renders} late={self.late} fifo={qn} debt={self.debt} "
                      f"ms_p95={sorted(self.ms)[int(0.95 * (len(self.ms) - 1))]:.0f}", flush=True)
            h, w = frames[0].shape[:2]
            return {"path": p, "n": len(frames), "h": h, "w": w}

    def health(self):
        ms = sorted(self.ms) or [0]
        return {"ready": self.ready, "chunk_frames": self.chunk, "chunk_samples": self.chunk * 640, "fps": FPS, "prime": self.prime,
                "info": self.info, "renders": self.renders, "late": self.late, "ms_p50": round(ms[len(ms) // 2], 1),
                "ms_p95": round(ms[int(0.95 * (len(ms) - 1))], 1), "error": self.error,
                "motion": (dict(self.sched.status(), mismatch=getattr(self, "mismatch", 0)) if getattr(self, "sched", None) else None),
                "putback_ms_p95": round(sorted(self.pb.ms[-500:] or [0])[int(0.95 * (len(self.pb.ms[-500:] or [0]) - 1))], 1) if hasattr(self, "pb") else None}


ENG = Engine()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _j(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/health"): return self._j(200, ENG.health())
        self._j(404, {})

    def do_POST(self):
        if self.path.startswith("/gesture"):
            n = int(self.headers.get("Content-Length", "0"))
            try: ev = json.loads(self.rfile.read(n) or b"{}")
            except Exception: return self._j(400, {"error": "json"})
            return self._j(200, ENG.gesture(ev))
        if not self.path.startswith("/render"): return self._j(404, {})
        if not ENG.ready: return self._j(503, {"error": "not ready"})
        n = int(self.headers.get("Content-Length", "0")); a = np.frombuffer(self.rfile.read(n), np.float32)
        try: self._j(200, ENG.render(a))
        except Exception as e:
            ENG.error = f"{type(e).__name__}: {e}"; self._j(500, {"error": ENG.error})


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", int(E("DITTO_PORT", "8031"))), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"[ditto_server] listening on :{E('DITTO_PORT', '8031')}", flush=True)
    try:
        ENG.load()
    except Exception as e:
        ENG.error = f"{type(e).__name__}: {e}"; print(traceback.format_exc(), flush=True)
    while True: time.sleep(3600)


if __name__ == "__main__":
    main()
