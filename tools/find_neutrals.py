#!/usr/bin/env python3
"""READY.md PART 2a — neutral crossings + arrival in-points (offline build step).

Scans the groove bake (as a video) for its NEUTRAL CROSSINGS: frames whose pose best
matches the freeze clips' first-frame pose (the standing start). The runtime swap
scheduler cuts bodies only at these timestamps — never a teleport between mismatched
poses. Also finds each freeze clip's ARRIVAL in-point: the first frame where motion
energy settles, minus 0.3s — she lands INTO the pose on screen, then holds.

Usage: find_neutrals.py <groove.mp4> <clip1.mp4> [clip2.mp4 ...] --out neutrals.json
Needs: mediapipe 1.0.1 + pose_landmarker_lite.task next to this script or --model.
"""
import sys, os, json, argparse
import numpy as np

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
import cv2

# torso+limbs joints used for the pose signature (BlazePose indices)
JOINTS = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]

def make_lm(model):
    opts = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=model),
        running_mode=vision.RunningMode.VIDEO)
    return vision.PoseLandmarker.create_from_options(opts)

def sig(landmarks):
    """normalized pose signature: joints relative to hip-center, scaled by shoulder-hip size."""
    pts = np.array([[landmarks[j].x, landmarks[j].y] for j in JOINTS])
    hips = (pts[JOINTS.index(23)] + pts[JOINTS.index(24)]) / 2
    sh   = (pts[JOINTS.index(11)] + pts[JOINTS.index(12)]) / 2
    scale = np.linalg.norm(sh - hips) or 1e-6
    return (pts - hips) / scale

def video_sigs(path, model, max_frames=100000):
    lm = make_lm(model)
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    out, ts = [], []
    i = 0
    while i < max_frames:
        ok, frame = cap.read()
        if not ok: break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        res = lm.detect_for_video(img, int(i / fps * 1000))
        out.append(sig(res.pose_landmarks[0]) if res.pose_landmarks else None)
        ts.append(i / fps)
        i += 1
    cap.release(); lm.close()
    return out, ts, fps

def motion_energy(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    prev, e = None, []
    while True:
        ok, frame = cap.read()
        if not ok: break
        g = cv2.cvtColor(cv2.resize(frame, (96, 170)), cv2.COLOR_BGR2GRAY).astype(np.float32)
        e.append(float(np.abs(g - prev).mean()) if prev is not None else 0.0)
        prev = g
    cap.release()
    return e, fps

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("groove"); ap.add_argument("clips", nargs="+")
    ap.add_argument("--out", default="neutrals.json")
    ap.add_argument("--model", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "pose_landmarker_lite.task"))
    ap.add_argument("--top", type=int, default=12)
    a = ap.parse_args()

    print("pose-scanning groove:", a.groove)
    gsigs, gts, gfps = video_sigs(a.groove, a.model)
    print(f"  {len(gsigs)} frames @ {gfps:.1f}fps, {sum(1 for s in gsigs if s is None)} no-pose")

    # target = mean standing-start pose across the freeze clips' first frames
    targets = []
    for c in a.clips:
        csigs, _, _ = video_sigs(c, a.model, max_frames=1)
        if csigs and csigs[0] is not None:
            targets.append(csigs[0]); print("  target pose from", os.path.basename(c))
        else:
            print("  WARN no pose in first frame of", c)
    tgt = np.mean(targets, axis=0)

    d = np.array([np.linalg.norm(s - tgt) if s is not None else 9e9 for s in gsigs])
    # local minima only (a neutral is a crossing, not a plateau), then best N spread out
    order = np.argsort(d)
    picked = []
    for i in order:
        t = gts[i]
        if d[i] > 8e9: continue
        if all(abs(t - p) > 1.0 for p in picked):
            picked.append(round(t, 2))
        if len(picked) >= a.top: break
    picked.sort()

    arrivals = {}
    for c in a.clips:
        e, cfps = motion_energy(c)
        if len(e) < 5: continue
        # the pose ARRIVAL is the stillness AFTER the main move-into-pose motion —
        # clips open standing still, so search only after the global motion peak.
        ea = np.array(e); pk = int(np.argmax(ea))
        thr = 0.12 * (ea[pk] or 1.0)
        still = next((i for i in range(pk + 1, len(e) - 2)
                      if ea[i] < thr and ea[i+1] < thr and ea[i+2] < thr), pk + 1)
        inpoint = max(0.0, still / cfps - 0.3)
        arrivals[os.path.splitext(os.path.basename(c))[0]] = round(inpoint, 2)
        print(f"  {os.path.basename(c)}: peak@{pk/cfps:.2f}s still@{still/cfps:.2f}s -> in-point {inpoint:.2f}s")

    out = {"loop_dur": round(len(gsigs)/gfps, 3), "fps": gfps, "mirror": True,
           "neutrals": picked, "arrivals": arrivals,
           "note": "neutrals = groove-loop timestamps whose pose best matches the freeze clips' standing start; mirror=True: engine ping-pongs the loop (period = 2*loop_dur)"}
    json.dump(out, open(a.out, "w"), indent=1)
    print("wrote", a.out, "->", out["neutrals"])

if __name__ == "__main__":
    main()
