#!/usr/bin/env python3
"""roi_probe.py -- THE KEY INSIGHT TEST, free, CPU, no pod.

Claim under test: at full-body framing MediaPipe fails not because the face is blurry but because
the face is too small a FRACTION of the frame for the short-range detector. If so, detecting on an
upscaled sub-region (ROI) and mapping the points back to full-frame coordinates must find the same
face that the full-frame pass misses.

For each clip, on frame 0 (and a few more):
  A) detect on the FULL frame, as DW.patch_first_frame_crop does today
  B) detect on an upscaled ROI, map back to full-frame pixels
and print face height in px plus the 5-point set Ditto's crop is built from.

  python3 -I roi_probe.py --lm face_landmarker.task CLIP [CLIP...]
"""
import argparse, json, os, sys
import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions


def make_lm(model):
    o = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=model), num_faces=1)
    return vision.FaceLandmarker.create_from_options(o)


def detect(lm, rgb):
    """-> (478,2) float32 in pixels of the image handed in, or None. Same shape DW.mp_landmarker returns."""
    r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
    if not r.face_landmarks:
        return None
    h, w = rgb.shape[:2]
    return np.array([[p.x * w, p.y * h] for p in r.face_landmarks[0]], np.float32)


def detect_roi(lm, rgb, roi, up):
    """detect inside roi=(x0,y0,x1,y1) of rgb, upscaled by `up`, and map the points back to rgb pixels."""
    x0, y0, x1, y1 = [int(v) for v in roi]
    sub = np.ascontiguousarray(rgb[y0:y1, x0:x1])
    if up != 1.0:
        sub = cv2.resize(sub, (int(round(sub.shape[1] * up)), int(round(sub.shape[0] * up))),
                         interpolation=cv2.INTER_CUBIC)
    p = detect(lm, sub)
    if p is None:
        return None
    return p / up + np.array([x0, y0], np.float32)


def face_px(p):
    return float(np.linalg.norm(p[152] - p[10]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="+")
    ap.add_argument("--lm", required=True)
    ap.add_argument("--frames", default="0,30,60")
    ap.add_argument("--json")
    a = ap.parse_args()
    lm = make_lm(a.lm)
    want = [int(x) for x in a.frames.split(",")]
    out = []
    for clip in a.clips:
        cap = cv2.VideoCapture(clip)
        W, H = int(cap.get(3)), int(cap.get(4))
        i = -1
        while True:
            ok, f = cap.read()
            if not ok:
                break
            i += 1
            if i not in want:
                continue
            rgb = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
            rec = {"clip": os.path.basename(clip), "frame": i, "wh": [W, H]}
            # A -- what Ditto does today: the whole frame
            pA = detect(lm, rgb)
            rec["full_frame_found"] = pA is not None
            rec["full_frame_face_px"] = round(face_px(pA), 1) if pA is not None else None
            # A' -- the whole frame upscaled 3x (the thing DITTO-TRY already proved does NOT help)
            pA3 = detect(lm, cv2.resize(rgb, (W * 3, H * 3), interpolation=cv2.INTER_CUBIC))
            rec["full_frame_3x_found"] = pA3 is not None
            # B -- the ROI ladder: upper band of the frame, upscaled
            rec["roi"] = None
            for frac_y, frac_x, up in [(0.33, 1.00, 3.0), (0.33, 0.60, 3.0), (0.40, 1.00, 2.0),
                                       (0.25, 0.50, 4.0), (0.50, 1.00, 2.0)]:
                rx0 = int(W * (1 - frac_x) / 2); rx1 = W - rx0
                roi = (rx0, 0, rx1, int(H * frac_y))
                pB = detect_roi(lm, rgb, roi, up)
                if pB is not None:
                    box = [float(pB[:, 0].min()), float(pB[:, 1].min()), float(pB[:, 0].max()), float(pB[:, 1].max())]
                    rec["roi"] = {"roi_px": list(roi), "upscale": up, "face_px": round(face_px(pB), 1),
                                  "face_box_fullframe": [round(v, 1) for v in box],
                                  "pt5": [[round(float(x), 1), round(float(y), 1)] for x, y in
                                          np.stack([pB[[33, 133]].mean(0), pB[[362, 263]].mean(0), pB[1], pB[61], pB[291]])],
                                  "oval_h": round(float(pB[152][1] - pB[10][1]), 1)}
                    break
            out.append(rec)
            print(json.dumps(rec), flush=True)
        cap.release()
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
