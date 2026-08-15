#!/usr/bin/env python3
# tools/pod/clip_scan.py <mp4> [--json]
# SOURCE CLIP PRE-FLIGHT (2026-08-15) — no bake starts on a clip without a verdict.
# Runs the SAME face detector the bake uses (FaceAlignment bbox + face_recognition
# landmarks) over every frame, maps the FACE-CLEAR windows, and issues a verdict:
#   BAKEABLE   — one continuous clean window >= 15s (bake whole)
#   PARTS      — 3+ clean windows >= 6s        (bake windows a/b/c, chain)
#   VOICE-ONLY — neither                       (regenerate the clip; emit a KLING card)
import sys, os, json
sys.path.insert(0, "/workspace/_sys/pylibs311_good/dist-packages")
sys.path.insert(0, "/workspace/LiveTalking")
sys.path.insert(0, "/workspace/LiveTalking/avatars/musetalk/utils")

def scan(vid):
    import cv2, numpy as np, face_recognition, torch
    from face_detection import FaceAlignment, LandmarksType
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    fa = FaceAlignment(LandmarksType._2D, flip_input=False, device=dev)
    cap = cv2.VideoCapture(vid)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    clean = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        f = fa.get_detections_for_batch(np.asarray([frame]))[0]
        good = False
        if f is not None:
            lms = face_recognition.face_landmarks(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if lms:
                lm = lms[0]
                pts = np.array(lm["chin"]+lm["left_eyebrow"]+lm["right_eyebrow"]+lm["nose_bridge"]+
                               lm["nose_tip"]+lm["left_eye"]+lm["right_eye"]+lm["top_lip"]+lm["bottom_lip"]).astype(np.int32)
                x1 = int(np.min(pts[:,0])); x2 = int(np.max(pts[:,0])); y2 = int(np.max(pts[:,1]))
                half = pts[29]; y1 = max(0, half[1]-int(np.max(pts[:,1])-half[1]))
                good = (x2-x1) > 0 and (y2-y1) > 0 and x1 >= 0
        clean.append(good)
    cap.release()
    n = len(clean)
    wins = []; s = None
    for i, c in enumerate(clean):
        if c and s is None: s = i
        if (not c) and s is not None: wins.append((s/fps, (i-1)/fps)); s = None
    if s is not None: wins.append((s/fps, (n-1)/fps))
    wins = [(a, b, b-a) for (a, b) in wins]
    longest = max((w[2] for w in wins), default=0)
    big = [w for w in wins if w[2] >= 6.0]
    if longest >= 15.0:      verdict = "BAKEABLE"
    elif len(big) >= 3:      verdict = "PARTS"
    else:                    verdict = "VOICE-ONLY"
    return dict(frames=n, fps=round(fps,2), dur=round(n/fps,1) if n else 0,
                clean_pct=round(100*sum(clean)/n) if n else 0,
                longest=round(longest,1), windows=[[round(a,2),round(b,2),round(L,2)] for a,b,L in wins if L>=1.0],
                verdict=verdict)

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv
    vid = args[0]
    r = scan(vid)
    name = os.path.basename(vid)
    if as_json:
        r["clip"] = name
        print(json.dumps(r))
    else:
        print(f"CLIP {name}  dur={r['dur']}s  clean={r['clean_pct']}%  longest={r['longest']}s  VERDICT={r['verdict']}")
        for a,b,L in r["windows"][:12]:
            print(f"   {a:6.2f}s -> {b:6.2f}s  ({L:.1f}s)")
