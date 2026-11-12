#!/usr/bin/env python3
"""bench/replace_musetalk_alt/ditto_wide.py -- ON the pod: Ditto (antgroup/ditto-talkinghead, Apache-2.0, LivePortrait
keypoint family) driven by the Hebrew audio, with the REAL wide bake video as its source (not a still):

  * source = the exact bake frames the wide / co-host shot shows, frame t of the output = bake frame t (so it lines up
    frame-for-frame with today's MuseTalk clip)
  * motion = expression only (use_d_keys={"exp": AMP}); Ditto's video mode keeps only the lip keypoints from the audio,
    so head pose, eyes, brows come from her real video. AMP < 1 = calmer mouth.
  * the render is a WARP of her own face (her lips, her teeth, her skin), the whole lower face deforms with the jaw.
  * paste-back: our own -- only the LOWER face (just below the nostrils, past the chin, cheek to cheek, wide feather),
    Lanczos, skin-ring colour match. DITTO_MASK=full = Ditto's stock 0.9 ellipse over the whole 512 crop.
  * InsightFace is never called: the first-frame face crop comes from MediaPipe (Apache-2.0); later frames are tracked
    by Ditto's own 203-point landmarker.

The audio is streamed PACED in Ditto's 0.2 s hubert chunks, like a live; every frame is time-stamped:
audio->frame(f) = emit(f) - (t0 + f/25).  Writes <out>/<tag>_full.mp4 (1920x1080, no audio), <tag>.json.

  python ditto_wide.py --ditto D --ckpt C --cfg CFG --src SRC.mp4 --wav W --out O --tag ditto_wide [--amp 1.0]
"""
import argparse, json, math, os, subprocess, sys, threading, time
import numpy as np
import cv2
if os.environ.get('OMP_NUM_THREADS'): cv2.setNumThreads(int(os.environ['OMP_NUM_THREADS']))

SR, FPS = 16000, 25
CH = (3, 5, 2)
HOP = CH[1] * 640
WIN = int(sum(CH) * 0.04 * SR) + 80
PRE = CH[0] * 640

OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149,
        150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]


def mp_landmarker(model):
    import mediapipe as mp
    from mediapipe.tasks.python import vision, BaseOptions
    o = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=model), num_faces=1)
    lm = vision.FaceLandmarker.create_from_options(o)

    def f(rgb):
        r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
        if not r.face_landmarks: return None
        h, w = rgb.shape[:2]
        return np.array([[p.x * w, p.y * h] for p in r.face_landmarks[0]], np.float32)
    return f


def lower_face_mask(pts, size=512, chin_drop=0.12, side=1.10, top_frac=0.30, feather=0.045):
    """float mask in crop space: from just under the nostrils down past the chin, cheek to cheek."""
    fw = float(np.linalg.norm(pts[454] - pts[234])); fh = float(pts[152][1] - pts[10][1])
    y_nose = float(pts[2][1]); y_lip = float(pts[0][1])
    y_top = y_nose + top_frac * (y_lip - y_nose)                     # between the nostril base and the upper lip
    c = np.array([pts[1][0], pts[13][1]], np.float32)
    oval = pts[OVAL].copy()
    oval = c + (oval - c) * side                                      # a little past her cheeks / jaw line
    oval[OVAL.index(152)][1] += chin_drop * fh                        # room for the chin to drop
    for i in (148, 377, 176, 400):
        oval[OVAL.index(i)][1] += 0.6 * chin_drop * fh
    m = np.zeros((size, size), np.float32)
    cv2.fillPoly(m, [np.round(oval).astype(np.int32)], 1.0)
    yy = np.arange(size, dtype=np.float32)[:, None]
    ramp = np.clip((yy - y_top) / (0.06 * fh), 0, 1)                  # soft top edge that ends below the nostrils
    m *= ramp
    k = max(3, int(feather * fw) | 1)
    m = cv2.GaussianBlur(m, (0, 0), k / 2.0)
    m *= (yy >= y_nose + 0.12 * (y_lip - y_nose))                     # nostrils + nose tip never touched
    m = cv2.GaussianBlur(m, (0, 0), 2.0)
    return np.clip(m, 0, 1)


class LowerPutBack:
    def __init__(self, mode, lm_model, amp_mask=None, debug_dir=None):
        self.mode, self.lm_model, self.mask, self.debug_dir = mode, lm_model, None, debug_dir
        self.ms = []

    def _build(self, render):
        render = np.clip(render, 0, 255).astype(np.uint8)
        if self.mode == "full":
            sys_mask = __import__("core.utils.get_mask", fromlist=["get_mask"]).get_mask(512, 512, 0.9, 0.9)
            self.mask = sys_mask[..., 0].astype(np.float32)
        else:
            pts = mp_landmarker(self.lm_model)(render)
            if pts is None: raise RuntimeError("no face in the first Ditto render")
            self.mask = lower_face_mask(pts)
        ys, xs = np.where(self.mask > 0.003)
        self.box = np.array([[xs.min(), ys.min()], [xs.max(), ys.min()], [xs.min(), ys.max()], [xs.max(), ys.max()]], np.float32)
        ring = (self.mask > 0.12) & (self.mask < 0.6)
        self.ring = ring.astype(np.float32)
        if self.debug_dir:
            cv2.imwrite(f"{self.debug_dir}/mask_crop.png", (self.mask * 255).astype(np.uint8))
            cv2.imwrite(f"{self.debug_dir}/render0.png", cv2.cvtColor(render, cv2.COLOR_RGB2BGR))

    def __call__(self, frame_rgb, render, M_c2o):
        t = time.perf_counter()
        if self.mask is None: self._build(render)
        h, w = frame_rgb.shape[:2]
        M = M_c2o[:2].astype(np.float64)
        bx = self.box @ M[:, :2].T + M[:, 2]
        x0, y0 = np.floor(bx.min(0)).astype(int) - 2; x1, y1 = np.ceil(bx.max(0)).astype(int) + 2
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
        Mr = M.copy(); Mr[:, 2] -= (x0, y0); sz = (x1 - x0, y1 - y0)
        m = cv2.warpAffine(self.mask, Mr, sz, flags=cv2.INTER_LINEAR)[..., None]
        r = cv2.warpAffine(render, Mr, sz, flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
        f = frame_rgb[y0:y1, x0:x1].astype(np.float32)
        if self.mode != "full":
            ring = cv2.warpAffine(self.ring, Mr, sz, flags=cv2.INTER_NEAREST) > 0.5
            if ring.sum() > 50:
                r += np.clip((f[ring] - r[ring]).mean(0), -12, 12)
        out = frame_rgb.copy()
        out[y0:y1, x0:x1] = np.clip(m * r + (1 - m) * f + 0.5, 0, 255).astype(np.uint8)
        self.ms.append((time.perf_counter() - t) * 1000)
        return out


class Recorder:
    def __init__(self, path=None):
        self.t = []; self.ff = None; self.path = path; self.shape = None

    def __call__(self, img, fmt="rgb"):
        self.t.append(time.perf_counter())
        if self.path:
            if self.ff is None:
                self.shape = img.shape
                self.ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                            "-s", f"{img.shape[1]}x{img.shape[0]}", "-r", str(FPS), "-i", "-",
                                            "-c:v", "libx264", "-crf", "10", "-preset", "veryfast", "-pix_fmt", "yuv420p", self.path],
                                           stdin=subprocess.PIPE)
            self.ff.stdin.write(np.ascontiguousarray(img, dtype=np.uint8).tobytes())

    def close(self):
        if self.ff:
            self.ff.stdin.close(); self.ff.wait(); self.ff = None


def vad_alpha(audio, n, look=2, back=1, floor_db=-45.0, span_db=12.0, release=0.6):
    """per-frame lip gate from the audio level, causal + `look` frames of lookahead (the online feed already holds 2
    frames ahead). 1 = speech (Ditto's lips), 0 = silence (her own closed mouth from the video)."""
    x = audio.astype(np.float64) * 32768
    r = np.array([np.sqrt((x[i * 640:(i + 1) * 640] ** 2).mean() + 1e-9) for i in range(n)])
    env = np.array([r[max(0, i - back):i + look + 1].max() for i in range(n)])
    a = np.clip((20 * np.log10(env / 32768) - floor_db) / span_db, 0, 1)
    out = np.zeros(n); prev = 0.0
    for i in range(n):
        prev = max(a[i], prev * release); out[i] = prev
    return out


def patch_first_frame_crop(lm_model):
    """Source2Info._crop without InsightFace (non-commercial): MediaPipe 478 -> 5 points -> Ditto's own crop + 203 lmk."""
    from core.atomic_components import source2info as S
    from core.utils.crop import crop_image
    det = mp_landmarker(lm_model)
    orig = S.Source2Info._crop

    def _crop(self, img, last_lmk=None, **kw):
        if last_lmk is not None:
            return orig(self, img, last_lmk=last_lmk, **kw)
        p = det(img)
        if p is None: raise RuntimeError("mediapipe: no face in the first source frame")
        pt5 = np.stack([p[[33, 133]].mean(0), p[[362, 263]].mean(0), p[1], p[61], p[291]]).astype(np.float32)
        ext = float(np.ptp(pt5[:, 1])); oval_h = float(p[152][1] - p[10][1])
        cd = crop_image(img, pt5, dsize=self.landmark203.dsize, scale=1.5 * oval_h / max(ext, 1.0), vy_ratio=-0.1, pt_crop_flag=False)
        lmk203 = self.landmark203(cd["img_crop"], cd["M_c2o"])
        return orig(self, img, last_lmk=lmk203, **kw)
    S.Source2Info._crop = _crop


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ditto", required=True); ap.add_argument("--ckpt", required=True); ap.add_argument("--cfg", required=True)
    ap.add_argument("--src", required=True); ap.add_argument("--wav", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default="ditto_wide"); ap.add_argument("--amp", type=float, default=1.0)
    ap.add_argument("--mask", default=os.environ.get("DITTO_MASK", "lower")); ap.add_argument("--lm", required=True)
    ap.add_argument("--crop-scale", type=float, default=0); ap.add_argument("--steps", type=int, default=0)
    ap.add_argument("--paced", type=int, default=1); ap.add_argument("--soak", type=int, default=0)
    ap.add_argument("--vad", type=int, default=int(os.environ.get("DITTO_VAD", "0")))
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    R = {"engine": "ditto (video source, exp-only, lower-face paste)", "args": vars(a)}
    save = lambda: json.dump(R, open(f"{a.out}/{a.tag}.json", "w"), indent=1)
    T0 = time.time(); log = lambda m: print(f"[ditto_wide {time.time() - T0:7.1f}s] {m}", flush=True)
    try:
        sys.path.insert(0, a.ditto); os.chdir(a.ditto)
        patch_first_frame_crop(a.lm)
        from stream_pipeline_online import StreamSDK
        import librosa
        sdk = StreamSDK(a.cfg, a.ckpt)
        pb = LowerPutBack(a.mask, a.lm, debug_dir=a.out); sdk.putback = pb
        reg = sdk.avatar_registrar; cache = {}

        def reg_cached(path, **kw):
            if path not in cache:
                t = time.time(); cache[path] = reg(path, **kw); R["register_s"] = round(time.time() - t, 1)
            return cache[path]
        sdk.avatar_registrar = reg_cached
        wav = librosa.load(a.wav, sr=SR)[0].astype(np.float32)
        nsrc = int(cv2.VideoCapture(a.src).get(cv2.CAP_PROP_FRAME_COUNT))
        nf = int(math.ceil(len(wav) / SR * FPS)) if a.soak else min(nsrc, int(math.ceil(len(wav) / SR * FPS)))
        kw = dict(use_d_keys={"exp": a.amp}, template_n_frames=nsrc)
        if a.crop_scale > 0: kw["crop_scale"] = a.crop_scale
        if a.steps > 0: kw["sampling_timesteps"] = a.steps

        def session(n, rec):
            sdk.setup(a.src, "/tmp/ditto_unused.mp4", **kw); sdk.setup_Nd(N_d=n)
            try: sdk.writer.close()
            except Exception: pass
            sdk.writer = rec

        RC = []

        def stream(audio, paced):
            x = np.concatenate([np.zeros(PRE, np.float32), audio]); n = int(math.ceil(len(audio) / HOP)); t0 = time.perf_counter()
            for i in range(n):
                c = x[i * HOP:i * HOP + WIN]
                if len(c) < WIN: c = np.pad(c, (0, WIN - len(c)))
                if paced:
                    d = t0 + (i * HOP + WIN - PRE) / SR - time.perf_counter()
                    if d > 0: time.sleep(d)
                tc = time.perf_counter(); sdk.run_chunk(c, CH); RC.append((time.perf_counter() - tc) * 1000)
                if sdk.stop_event.is_set(): raise RuntimeError(f"ditto worker died: {sdk.worker_exception!r}")
            return t0

        rec = Recorder(); session(75, rec); log(f"registered {nsrc} source frames in {R.get('register_s')} s")
        stream(np.zeros(3 * SR, np.float32), False); sdk.close(); log(f"warm frames {len(rec.t)}"); save()
        rec = Recorder(None if a.soak else f"{a.out}/{a.tag}_full.mp4"); session(nf, rec); RC.clear()
        if a.vad:
            va = vad_alpha(wav[:int(nf / FPS * SR)], nf)
            sdk.ctrl_info = {i: {"vad_alpha": float(max(v, 1e-3))} for i, v in enumerate(va)}
            R["vad_closed_frac"] = round(float((va < 0.05).mean()), 3)
        t0 = stream(wav[:int(nf / FPS * SR)], bool(a.paced)); sdk.close(); rec.close()
        e = np.array(rec.t) - t0; f = np.arange(len(e)); lat = e - f / FPS; st = lat[f >= 25]
        pbm = sorted(pb.ms[5:]) or [0]
        R["live"] = {"frames": int(len(e)), "frames_expected": nf, "paced": bool(a.paced),
                     "first_frame_s": round(float(e[0]), 3), "fps_sustained": round(len(e) / float(e[-1]), 2),
                     "audio_to_frame_p50_s": round(float(np.percentile(st, 50)), 3),
                     "audio_to_frame_p95_s": round(float(np.percentile(st, 95)), 3),
                     "audio_to_frame_max_s": round(float(st.max()), 3),
                     "run_chunk_ms_p50": round(float(np.percentile(RC, 50)), 1), "run_chunk_ms_p95": round(float(np.percentile(RC, 95)), 1),
                     "run_chunk_ms_max": round(float(max(RC)), 1),
                     "putback_ms_p50": round(pbm[len(pbm) // 2], 1), "putback_ms_p95": round(pbm[int(0.95 * (len(pbm) - 1))], 1)}
        R["status"] = "ok"; log(json.dumps(R["live"]))
    except Exception as ex:
        import traceback
        R["status"] = "crash"; R["error"] = f"{type(ex).__name__}: {ex}"; R["trace"] = traceback.format_exc()[-4000:]
        print(R["trace"], flush=True)
    finally:
        try: R["gpu"] = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.used", "--format=csv,noheader"], text=True).strip()
        except Exception: pass
        save()
    os._exit(0 if R.get("status") == "ok" else 2)


if __name__ == "__main__":
    main()
