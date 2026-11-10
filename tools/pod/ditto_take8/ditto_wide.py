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
    # DITTO_FACE_ROBUST (default off -> professor/maya banks unchanged): a small portrait face
    # (chef ~205 px, zara idle ~240 px) letterboxes BELOW the tasks FaceLandmarker's 0.5 default
    # threshold on a full 1080x1920 frame -- chef frame 0 returns NO FACE, so patch_first_frame_crop
    # raised "no face in the first source frame", the Ditto worker died and ditto_up.sh exited 3
    # (the three chef failures). The same model also misses intermittently on Ditto's own 512 render
    # crop (zara 2026-11-01: 121/1338 frames fell back to the stock ellipse). Measured locally with
    # this exact model: chef full-frame@0.5=NO FACE, @0.1=FACE, Haar+crop=FACE 207 px. So lower the
    # threshold AND, when the whole image still finds nothing, retry on a Haar-localised square crop
    # (the same trick bench/lips/audit_measure.py uses) and map the landmarks back to image coords.
    robust = os.environ.get("DITTO_FACE_ROBUST", "0") == "1"
    conf = float(os.environ.get("DITTO_FACE_CONF", "0.25" if robust else "0.5"))
    o = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=model), num_faces=1,
                                     min_face_detection_confidence=conf)
    lm = vision.FaceLandmarker.create_from_options(o)
    haar = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml") if robust else None

    def _detect(rgb):
        r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
        return r.face_landmarks[0] if r.face_landmarks else None

    def f(rgb):
        h, w = rgb.shape[:2]
        pl = _detect(rgb)
        if pl is None and haar is not None:
            g = cv2.cvtColor(np.ascontiguousarray(rgb), cv2.COLOR_RGB2GRAY)
            fcs = haar.detectMultiScale(g, 1.2, 5, minSize=(60, 60))
            if len(fcs):
                fx, fy, fw, fh = sorted(fcs, key=lambda b: b[2] * b[3])[-1]
                cx, cy = fx + fw // 2, fy + fh // 2; half = int(fw * 1.4)
                x0, y0 = max(0, cx - half), max(0, cy - half)
                x1, y1 = min(w, cx + half), min(h, cy + half)
                sub = np.ascontiguousarray(rgb[y0:y1, x0:x1])
                pl = _detect(sub)
                if pl is not None:
                    ch, cw = sub.shape[:2]
                    return np.array([[p.x * cw + x0, p.y * ch + y0] for p in pl], np.float32)
        if pl is None: return None
        return np.array([[p.x * w, p.y * h] for p in pl], np.float32)
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


LIP_OUTER = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
LIP_INNER = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191]


def lips_mask(pts, size=512):
    """DITTO_MASK=lips (Seyzar take 4, default off): only the lips + the band the lower lip travels into when the mouth
    opens, tight feather -- the beard, chin and cheeks stay the SOURCE pixels (Ditto's redraw smears beard texture).
    Returns (paste mask, lip-core mask) in crop space. Env: DITTO_LIP_DROP 0.28 (x inter-ocular, how far down the lower lip may
    travel), DITTO_LIP_SIDE 0.10 (x mouth width, past each corner), DITTO_LIP_FEATHER 0.05 (x inter-ocular)."""
    E_ = os.environ.get
    iod = float(np.linalg.norm(pts[33] - pts[263])); mw = float(np.linalg.norm(pts[61] - pts[291]))
    drop = float(E_("DITTO_LIP_DROP", "0.28")) * iod; side = float(E_("DITTO_LIP_SIDE", "0.10")) * mw
    poly = pts[LIP_OUTER].astype(np.float32).copy(); c = poly.mean(0)
    poly[:, 0] = c[0] + (poly[:, 0] - c[0]) * (1 + 2 * side / max(mw, 1))            # a little past the corners
    core = np.zeros((size, size), np.float32); cv2.fillPoly(core, [np.round(poly).astype(np.int32)], 1.0)
    m = core.copy(); steps = max(1, int(drop / 2))
    for k in range(1, steps + 1):                                                       # sweep the lip down (jaw open)
        M = np.float32([[1, 0, 0], [0, 1, drop * k / steps]])
        m = np.maximum(m, cv2.warpAffine(core, M, (size, size)))
    up = np.float32([[1, 0, 0], [0, 1, -0.04 * iod]])                                  # a hair above the upper lip line
    m = np.maximum(m, cv2.warpAffine(core, up, (size, size)))
    fe = max(1.0, float(E_("DITTO_LIP_FEATHER", "0.05")) * iod)
    m = cv2.GaussianBlur(m, (0, 0), fe); core = cv2.GaussianBlur(cv2.erode(core, np.ones((3, 3), np.uint8), iterations=2), (0, 0), max(1.0, fe / 3))
    return np.clip(m, 0, 1), np.clip(core, 0, 1)


def _lab_target():
    """DITTO_LIP_LAB = "L,a,b" (OpenCV 8-bit Lab, mean of his real lips from his own clip) or empty."""
    v = os.environ.get("DITTO_LIP_LAB", "")
    try:
        t = [float(z) for z in v.split(",")]
        return np.array(t[:3], np.float32) if len(t) >= 3 else None
    except ValueError:
        return None


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
            if pts is None:
                # 2026-11-01: mediapipe occasionally finds no face in Ditto's OWN first rendered 512 crop,
                # even when the source frame has a clear one (zara bank frame 0: face 272 px, haar finds it,
                # ditto's warm-up render does not). It killed three zara shows at prof_job.sh:50 while a
                # fourth run of the same bank on the same GPU succeeded -- i.e. a warm-up flake, not content.
                # Dying there wastes the whole pod. Fall back to Ditto's stock ellipse for this build and
                # let the next frame rebuild the precise lower-face mask once a face is found.
                print("[ditto_wide] no face in the first render; using the stock ellipse for now", flush=True)
                sys_mask = __import__("core.utils.get_mask", fromlist=["get_mask"]).get_mask(512, 512, 0.9, 0.9)
                self.mask = sys_mask[..., 0].astype(np.float32)
                self._provisional = True
            elif self.mode == "lips":
                self.mask, self.core = lips_mask(pts)
                self._provisional = False
                # lip colour: a fixed Lab map fitted once on Ditto's first render (closed lips) -> his real lips (DITTO_LIP_LAB):
                # L shifted, a/b chroma scaled around neutral (teeth / dark mouth stay neutral, pink lips lose the pink).
                self.lab_map = None; tgt = _lab_target()
                if tgt is not None:
                    ring = np.zeros((512, 512), np.uint8)
                    cv2.fillPoly(ring, [np.round(pts[LIP_OUTER]).astype(np.int32)], 1); cv2.fillPoly(ring, [np.round(pts[LIP_INNER]).astype(np.int32)], 0)
                    lab = cv2.cvtColor(render, cv2.COLOR_RGB2LAB)[cv2.erode(ring, np.ones((3, 3), np.uint8)) > 0].astype(np.float32)
                    if len(lab) > 30:
                        mu = lab.mean(0); dl = float(np.clip(tgt[0] - mu[0], -25, 25))
                        cs = lambda t, r: float(np.clip((t - 128) / (r - 128), 0.3, 1.5)) if abs(r - 128) > 2 and (t - 128) * (r - 128) > 0 else 1.0
                        sa = cs(tgt[1], mu[1]); sb = cs(tgt[2], mu[2])
                        self.lab_map = (dl, sa, sb)
                        print(f"[ditto_wide] lip colour map: render lips Lab {mu.round(1).tolist()} -> target {tgt.tolist()}: dL {dl:+.1f}, a x{sa:.2f}, b x{sb:.2f}", flush=True)
                self.grain = os.environ.get("DITTO_GRAIN", "0") == "1"; self.rng = np.random.default_rng(7)
            else:
                self.mask = lower_face_mask(pts)
                self._provisional = False
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
        elif getattr(self, "_provisional", False):
            self._build(render)                       # retry the precise mask until mediapipe finds the face
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
        if self.mode == "lips":
            if getattr(self, "lab_map", None) is not None:                # his lip colour, on the lip core only
                dl, sa, sb = self.lab_map
                lab = cv2.cvtColor(np.clip(r, 0, 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
                lab[..., 0] += dl; lab[..., 1] = 128 + (lab[..., 1] - 128) * sa; lab[..., 2] = 128 + (lab[..., 2] - 128) * sb
                r2 = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)
                cw = cv2.warpAffine(self.core, Mr, sz, flags=cv2.INTER_LINEAR)[..., None]
                r = cw * r2 + (1 - cw) * r
            if getattr(self, "grain", False):                             # his camera grain back on the redrawn pixels
                k = (m[..., 0] > 0.5)
                if k.sum() > 50:
                    hf_s = (f - cv2.GaussianBlur(f, (0, 0), 1.2))[k].std(); hf_r = (r - cv2.GaussianBlur(r, (0, 0), 1.2))[k].std()
                    add = float(np.sqrt(max(0.0, hf_s ** 2 - hf_r ** 2)))
                    if add > 0.3: r += self.rng.normal(0, add, r.shape[:2]).astype(np.float32)[..., None]
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
