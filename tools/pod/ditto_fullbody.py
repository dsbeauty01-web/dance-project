#!/usr/bin/env python3
"""ditto_fullbody.py -- let Ditto start on a FULL-BODY source, by fixing the one thing that blocks it.

THE PROBLEM, exactly. `bench/replace_musetalk_alt/ditto_wide.py` (maya-lt @ lane/motion-transfer)
patches Ditto's first-frame crop so InsightFace is never called:

    def patch_first_frame_crop(lm_model):
        det = mp_landmarker(lm_model)
        orig = S.Source2Info._crop
        def _crop(self, img, last_lmk=None, **kw):
            if last_lmk is not None:
                return orig(self, img, last_lmk=last_lmk, **kw)
            p = det(img)                                     # <-- THE WHOLE FRAME
            if p is None: raise RuntimeError("mediapipe: no face in the first source frame")
            pt5 = np.stack([p[[33,133]].mean(0), p[[362,263]].mean(0), p[1], p[61], p[291]]).astype(np.float32)
            ext = float(np.ptp(pt5[:,1])); oval_h = float(p[152][1] - p[10][1])
            cd = crop_image(img, pt5, dsize=self.landmark203.dsize, scale=1.5*oval_h/max(ext,1.0), vy_ratio=-0.1, pt_crop_flag=False)
            lmk203 = self.landmark203(cd["img_crop"], cd["M_c2o"])
            return orig(self, img, last_lmk=lmk203, **kw)
        S.Source2Info._crop = _crop

`det(img)` is handed the ENTIRE source frame. MediaPipe's short-range face detector works on the
face's FRACTION of the image, not its pixel size, so at Nova's full-body framing (a ~160 px face in
a 1076x1924 frame, 8 % of the height) it returns nothing and `_crop` raises -- Ditto cannot even
register the source. Measured here, 2026-10-31, 9 frames of 3 full-body clips: the full frame finds
the face 0/9 times, THE FULL FRAME UPSCALED 3x ALSO FINDS IT 0/9 TIMES (so resolution is not the
problem), and the top third of the frame upscaled 3x finds it 9/9 at 154-172 px.

WHAT CAN AND CANNOT BE SUPPLIED, as the code actually stands:
  * A crop box CANNOT be passed in. `patch_first_frame_crop(lm_model)` takes a landmarker path and
    nothing else; there is no box, roi or pt5 argument anywhere in the call chain, and
    `ditto_server.py` calls it as `DW.patch_first_frame_crop(lm)`.
  * But the geometry channel EXISTS: `_crop` ends in `orig(self, img, last_lmk=lmk203)`, and the
    whole point of the `last_lmk is not None` early return is that Ditto's own tracker takes
    supplied landmarks and never detects. Frames 1..N already go down that path. Only frame 0 needs
    a detection, and the only thing wrong with it is the region it is given.
  * Paste-back ALREADY returns the full original frame. `DW.LowerPutBack.__call__` does
    `out = frame_rgb.copy()` and then writes only `out[y0:y1, x0:x1]` as `m*r + (1-m)*f`, where
    `frame_rgb` is the untouched source frame and `m` is a Gaussian-feathered lower-face oval. So
    there is nothing to add for paste-back: hand it a full-body frame and it returns a full-body
    frame with only the lower face repainted, feathered, no rectangle.

THE SHIM, therefore, is one function: make the detector region-aware and leave everything else --
the crop, the 203-point tracking, the paste-back, the server -- byte-identical.

`DW.patch_first_frame_crop` builds its detector with `det = mp_landmarker(lm_model)`, resolved from
the `ditto_wide` module namespace at call time. Replacing `DW.mp_landmarker` with a wrapper BEFORE
`patch_first_frame_crop` runs therefore changes the detector and nothing else. maya-lt is not
touched; no file there is edited, patched or copied over.

The wrapper is a no-op wherever detection already works: it runs the stock full-image detector
first and only falls back to the ROI ladder when that returns None. `LowerPutBack._build` also uses
`mp_landmarker`, on the 512 render crop, where the stock pass always succeeds -- so that call site
is unaffected.

  install(roi=(x0,y0,x1,y1), up=3.0)   explicit box, computed once by the caller
  install()                            auto: try the full frame, then the ROI ladder
  DITTO_FB_BOX="x0,y0,x1,y1"           the explicit box, for ditto_server.py which takes no args
  DITTO_FB_UP="3.0"                    upscale applied inside the box

Usage on the pod, before `DW.patch_first_frame_crop(...)` is reached:
    import ditto_fullbody; ditto_fullbody.install()      # reads DITTO_FB_BOX / DITTO_FB_UP
Everything after that is stock ditto_server.py.
"""
import os
import sys

import numpy as np
import cv2

# the ROI ladder, tried in order when the stock full-image pass finds nothing.
# (height fraction, width fraction, upscale) -- a band at the TOP of the frame, where a standing
# figure's head is. Measured 2026-10-31: (0.33, 1.00, 3.0) found the face on 9/9 full-body frames.
LADDER = [(0.33, 1.00, 3.0), (0.33, 0.60, 3.0), (0.40, 1.00, 2.0), (0.25, 0.50, 4.0), (0.50, 1.00, 2.0)]

# stderr, never stdout: this module is imported by a sitecustomize that is on PYTHONPATH for every
# python the pod runs, including `python -c "import site; print(...)"` calls whose stdout is captured.
_LOG = lambda m: print(f"[ditto_fullbody] {m}", file=sys.stderr, flush=True)


def _detect_in(base, rgb, roi, up):
    """run `base` (a stock DW.mp_landmarker detector) inside roi=(x0,y0,x1,y1), upscaled by `up`,
    and map the returned points back into `rgb`'s own pixel coordinates."""
    h, w = rgb.shape[:2]
    x0, y0, x1, y1 = (max(0, int(roi[0])), max(0, int(roi[1])), min(w, int(roi[2])), min(h, int(roi[3])))
    if x1 - x0 < 32 or y1 - y0 < 32:
        return None
    sub = np.ascontiguousarray(rgb[y0:y1, x0:x1])
    if up and up != 1.0:
        sub = cv2.resize(sub, (int(round(sub.shape[1] * up)), int(round(sub.shape[0] * up))),
                         interpolation=cv2.INTER_CUBIC)
    p = base(sub)
    if p is None:
        return None
    return (p / (up or 1.0) + np.array([x0, y0], np.float32)).astype(np.float32)


def install(roi=None, up=None, ladder=None, module=None):
    """Wrap ditto_wide.mp_landmarker so its detectors fall back to an upscaled ROI.

    roi -- (x0, y0, x1, y1) in SOURCE pixels: the explicit box. Defaults to DITTO_FB_BOX, else the
           ladder is used. up defaults to DITTO_FB_UP, else 3.0.
    Returns the stats dict the wrapper keeps (so a caller can assert the ROI path was really used).
    """
    DW = module or sys.modules.get("ditto_wide")
    if DW is None:
        import ditto_wide as DW  # noqa: N806
    if getattr(DW, "_fullbody_installed", False):
        return DW._fullbody_stats
    if roi is None and os.environ.get("DITTO_FB_BOX"):
        roi = tuple(float(x) for x in os.environ["DITTO_FB_BOX"].split(","))
        if len(roi) != 4:
            raise SystemExit("DITTO_FB_BOX must be x0,y0,x1,y1")
    if up is None:
        up = float(os.environ.get("DITTO_FB_UP", "3.0"))
    rungs = ladder if ladder is not None else LADDER
    stats = {"calls": 0, "stock_hits": 0, "roi_hits": 0, "misses": 0, "roi_used": None,
             "explicit_box": list(roi) if roi else None, "up": up, "face_px": None}
    orig_factory = DW.mp_landmarker

    def factory(model):
        base = orig_factory(model)

        def det(rgb):
            stats["calls"] += 1
            p = base(rgb)                                    # pass 1: exactly the stock behaviour
            if p is not None:
                stats["stock_hits"] += 1
                return p
            h, w = rgb.shape[:2]
            tries = ([(roi, up)] if roi else
                     [((int(w * (1 - fx) / 2), 0, w - int(w * (1 - fx) / 2), int(h * fy)), u) for fy, fx, u in rungs])
            for r, u in tries:
                q = _detect_in(base, rgb, r, u)
                if q is not None:
                    stats["roi_hits"] += 1
                    stats["roi_used"] = [int(v) for v in r] + [u]
                    stats["face_px"] = round(float(np.linalg.norm(q[152] - q[10])), 1)
                    _LOG(f"ROI hit on a {w}x{h} frame: roi={[int(v) for v in r]} up={u} "
                         f"face_px={stats['face_px']} (stock full-frame pass found nothing)")
                    return q
            stats["misses"] += 1
            _LOG(f"NO FACE on a {w}x{h} frame, stock pass and all {len(tries)} ROI rungs")
            return None
        return det

    DW.mp_landmarker = factory
    DW._fullbody_installed = True
    DW._fullbody_stats = stats
    _LOG(f"installed: explicit_box={stats['explicit_box']} up={up} rungs={len(rungs)}")
    return stats


def box_from_clip(clip, lm_model, frame=0, pad=1.6):
    """Compute the explicit box ONCE, on CPU, off the pod: detect on an upscaled ROI of `frame`,
    map back, and return a padded box in full-frame pixels plus the measured face height."""
    import mediapipe as mp
    from mediapipe.tasks.python import vision, BaseOptions
    o = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=lm_model), num_faces=1)
    lmk = vision.FaceLandmarker.create_from_options(o)

    def base(rgb):
        r = lmk.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
        if not r.face_landmarks:
            return None
        hh, ww = rgb.shape[:2]
        return np.array([[q.x * ww, q.y * hh] for q in r.face_landmarks[0]], np.float32)

    cap = cv2.VideoCapture(clip)
    for _ in range(frame + 1):
        ok, f = cap.read()
    cap.release()
    if not ok:
        raise SystemExit(f"cannot read frame {frame} of {clip}")
    rgb = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    p = base(rgb)
    if p is None:
        for fy, fx, u in LADDER:
            r = (int(w * (1 - fx) / 2), 0, w - int(w * (1 - fx) / 2), int(h * fy))
            p = _detect_in(base, rgb, r, u)
            if p is not None:
                break
    if p is None:
        raise SystemExit(f"no face anywhere in frame {frame} of {clip}")
    cx, cy = float(p[:, 0].mean()), float(p[:, 1].mean())
    fh = float(np.linalg.norm(p[152] - p[10]))
    half = fh * pad
    box = (max(0, int(cx - half)), max(0, int(cy - half)), min(w, int(cx + half)), min(h, int(cy + half)))
    return {"clip": clip, "frame": frame, "wh": [w, h], "face_px": round(fh, 1),
            "face_centre": [round(cx, 1), round(cy, 1)], "box": list(box),
            "box_str": ",".join(str(v) for v in box)}


def _selftest():
    """prove the wrapper on a synthetic DW: stock pass wins when it can, ROI pass rescues it."""
    import types
    fake = types.ModuleType("ditto_wide_fake")
    truth = np.zeros((478, 2), np.float32)
    truth[10] = (500.0, 400.0); truth[152] = (500.0, 560.0)       # a 160 px face at (500, 480)

    def mp_landmarker(_model):
        def det(rgb):
            h, w = rgb.shape[:2]
            if (w, h) == (1076, 1924):     # stand-in for the real failure: the full full-body frame finds nothing
                return None
            return truth.copy()
        return det
    fake.mp_landmarker = mp_landmarker
    st = install(module=fake, ladder=LADDER, up=3.0)
    det = fake.mp_landmarker("x")
    ok = []
    small = np.zeros((512, 512, 3), np.uint8)
    ok.append(("stock pass used on a 512 crop", det(small) is not None and st["stock_hits"] == 1))
    big = np.zeros((1924, 1076, 3), np.uint8)
    p = det(big)
    ok.append(("ROI pass rescues a 1076x1924 frame", p is not None and st["roi_hits"] == 1))
    ok.append(("ROI points are mapped back to full-frame pixels", p is not None and abs(p[10][1] - 400.0 / 3.0) < 1e-3))
    ok.append(("no miss recorded", st["misses"] == 0))
    ok.append(("idempotent", install(module=fake) is st))
    for name, good in ok:
        print(f"  {'PASS' if good else 'FAIL'}  {name}")
    print(f"stats: {st}")
    return 0 if all(g for _, g in ok) else 1


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--box", help="compute the explicit box for this clip")
    ap.add_argument("--lm"); ap.add_argument("--frame", type=int, default=0)
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(_selftest())
    if a.box:
        print(json.dumps(box_from_clip(a.box, a.lm, a.frame), indent=1))
