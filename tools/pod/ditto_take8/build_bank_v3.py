#!/usr/bin/env python3
"""build_bank_v3.py -- Seyzar take 3 body (2026-11-09): his whole 24 s clip, with a CLOSED SOURCE MOUTH ON EVERY FRAME.

Take 2 blended the lips 85 % toward a closed frame, so his own talking mouth still moved underneath Ditto in the pauses ("extra
lip moves when not talking", Refael). Here the lower-face mouth region is REPLACED (alpha 1.0 at the centre), every frame:
  1. MediaPipe 478 landmarks on the frame P and on his best closed-mouth frame R (--ref, default 127: neutral, lips together);
  2. a thin-plate spline maps the frame's pixels back into R:  the lips (outer + inner) go to their CLOSED shape, placed by an
     similarity fitted on eye corners + nose (head pose only, so the closed lips never change shape);  the mask's own border points -- nose base,
     cheeks beside the mouth, chin centre and jaw -- map to where they really are in this frame, so jaw, beard edge and head keep
     his real motion and the beard between the closed lower lip and his real chin is stretched to meet it;
  3. feathered mask = lips + the chin just below (to landmark 200) + a little cheek either side, alpha 1 inside, Gaussian edge;
  4. colour match: the warped patch's mean is shifted to this frame's on a ring just outside the mask (his light flickers).
Everything outside the mask (eyes, hair, hands, shoulders, light) is his real footage untouched. Then the same 1080x1920
framing and ping-pong as v2.
  python3 build_bank_v3.py SRC OUT.mp4 [--ref 127] [--face face_landmarker.task]
"""
import argparse, json, os, subprocess, sys
import numpy as np, cv2
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
from scipy.interpolate import RBFInterpolator

ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--ref", type=int, default=127); ap.add_argument("--face", default="/app/face_landmarker.task"); ap.add_argument("--crf", default="16")
ap.add_argument("--feather", type=float, default=0.10, help="edge feather sigma as a fraction of the inter-ocular distance")
ap.add_argument("--debug", default="")
a = ap.parse_args()

cap = cv2.VideoCapture(a.src); frames = []
while True:
    ok, f = cap.read()
    if not ok: break
    frames.append(f)
N = len(frames); H, W = frames[0].shape[:2]
print(f"[bank3] {N} frames {W}x{H}", flush=True)

OUTER = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
INNER = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191]
STABLE = [33, 133, 362, 263, 1, 168, 6, 98, 327]                    # eye corners + nose: they do not move with speech
ANCHOR = [2, 164, 98, 327, 167, 393, 206, 426, 216, 436, 212, 432, 202, 422, 204, 424, 194, 418, 200, 199, 175, 152, 148, 377,
          176, 400, 32, 262, 140, 369, 171, 396]                   # real-motion points: nose base, cheeks, chin, jaw
MASK_POLY = [164, 393, 391, 322, 410, 287, 273, 335, 406, 313, 18, 200, 83, 182, 106, 43, 57, 186, 92, 165, 167]
lmk = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=a.face), num_faces=1, running_mode=vision.RunningMode.IMAGE))

def pts(img):
    r = lmk.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
    if not r.face_landmarks: return None
    return np.array([[p.x * W, p.y * H] for p in r.face_landmarks[0]], np.float64)

ref = frames[a.ref]; R = pts(ref); assert R is not None, "no face on the reference frame"
LIPS = OUTER + INNER
stats = {"ref": a.ref, "no_face": 0, "gap_before_px": [], "frames": N}
out = []
for i, f in enumerate(frames):
    P = pts(f)
    if P is None:
        stats["no_face"] += 1; out.append(f); continue
    stats["gap_before_px"].append(float(np.linalg.norm(P[14] - P[13])))
    iod = float(np.linalg.norm(P[33] - P[263]))
    A, _ = cv2.estimateAffinePartial2D(R[STABLE].astype(np.float32), P[STABLE].astype(np.float32), method=cv2.LMEDS)
    lip_tgt = (A[:, :2] @ R[LIPS].T).T + A[:, 2]
    tgt = np.vstack([lip_tgt, P[ANCHOR]]); srcp = np.vstack([R[LIPS], R[ANCHOR]])
    # mask in this frame: the polygon around lips + chin just below, unioned with the closed lips' footprint
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [cv2.convexHull(P[MASK_POLY].astype(np.int32))], 255)
    cv2.fillPoly(m, [np.vstack([P[OUTER], lip_tgt[:len(OUTER)]]).astype(np.int32)], 255)
    cv2.fillPoly(m, [cv2.convexHull(lip_tgt[:len(OUTER)].astype(np.int32))], 255)
    sig = max(2.0, a.feather * iod)
    ys, xs = np.where(m > 0); pad = int(4 * sig) + 4
    x0, x1 = max(0, xs.min() - pad), min(W, xs.max() + pad); y0, y1 = max(0, ys.min() - pad), min(H, ys.max() + pad)
    # thin-plate map target -> ref on a 4 px grid over the box, then upsampled to a dense remap
    rbf = RBFInterpolator(tgt, srcp, kernel="thin_plate_spline", smoothing=0.5)
    gx = np.arange(x0, x1 + 4, 4, dtype=np.float64); gy = np.arange(y0, y1 + 4, 4, dtype=np.float64)
    GX, GY = np.meshgrid(gx, gy); mp_ = rbf(np.c_[GX.ravel(), GY.ravel()]).reshape(len(gy), len(gx), 2)
    bw, bh = x1 - x0, y1 - y0
    mx = cv2.resize(mp_[..., 0].astype(np.float32), (len(gx) * 4, len(gy) * 4), interpolation=cv2.INTER_LINEAR)[:bh, :bw]
    my = cv2.resize(mp_[..., 1].astype(np.float32), (len(gx) * 4, len(gy) * 4), interpolation=cv2.INTER_LINEAR)[:bh, :bw]
    patch = cv2.remap(ref, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    mb = m[y0:y1, x0:x1]
    alpha = cv2.GaussianBlur((mb > 0).astype(np.float32), (0, 0), sig)
    alpha = np.clip(alpha * 2.0, 0, 1)                              # ~1.0 over the whole mask, soft only at its edge
    roi = f[y0:y1, x0:x1].astype(np.float32)
    ring = (cv2.dilate((alpha > 0.02).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0) & (alpha <= 0.02)
    if ring.sum() > 50: patch = np.clip(patch + (roi[ring].mean(0) - patch[ring].mean(0)), 0, 255)
    g = f.copy(); g[y0:y1, x0:x1] = (roi * (1 - alpha[..., None]) + patch * alpha[..., None]).astype(np.uint8)
    out.append(g)
    if a.debug and i in (0, 100, 200, 300, 400, 500):
        cv2.imwrite(f"{a.debug}/v3_{i:03d}.jpg", np.hstack([f[y0 - 60:y1 + 60, x0 - 60:x1 + 60], g[y0 - 60:y1 + 60, x0 - 60:x1 + 60]]))
    if i % 100 == 0: print(f"[bank3] {i}/{N}", flush=True)
frames = out
gb = np.array(stats["gap_before_px"]); stats["gap_before_px"] = {"max": round(float(gb.max()), 2), "p50": round(float(np.median(gb)), 2)}

seq = frames + frames[-2:0:-1]                              # ping-pong, endpoints not doubled
fw, fhh = 1080, int(round(H * 1080 / W / 2) * 2)
y0 = (1920 - fhh) // 2
cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "25", "-i", "-",
       "-filter_complex",
       f"[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=40:2,eq=brightness=-0.06[bg];"
       f"[b]scale={fw}:{fhh}:flags=lanczos[fg];[bg][fg]overlay=0:{y0},format=yuv420p",
       "-c:v", "libx264", "-preset", "slow", "-crf", a.crf, "-g", "50", "-an", a.out]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for f in seq: p.stdin.write(np.ascontiguousarray(f).tobytes())
p.stdin.close(); p.wait()
stats.update({"src_frames": N, "bank_frames": len(seq), "fps": 25, "seconds": round(len(seq) / 25, 2), "fg": [fw, fhh], "y0": y0})
json.dump(stats, open(a.out + ".build.json", "w"), indent=1)
print("[bank3] done", json.dumps({k: v for k, v in stats.items()}), flush=True)
