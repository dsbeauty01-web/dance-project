#!/usr/bin/env python3
"""prebake_gate.py -- CPU-only pre-bake gate for a Ditto source video (no GPU, no network, no money).

Answers: is this moving source calm enough for Ditto's lips?  PASS / SOFTEN / REJECT, per clip and per segment.

Per frame (MediaPipe FaceLandmarker with the facial transformation matrix, + optional HandLandmarker):
  yaw / pitch / roll (deg, true 3-D head pose)      yaw_proxy (|nose - eye-mid| / inter-ocular, same as build_zara_gate.py)
  face_px  (forehead 10 -> chin 152, scaled to a 1920-high delivered frame)
  disp     (nose-tip move since last frame, % of face height)      rot_v (deg/frame, max of the 3 angles)
  smo_res  (pose minus its 13-frame mean = what Ditto's smo_k_s=13 source smoothing gets wrong, deg)
  mouth    (inner-lip gap 13-14 / face height)      hand (any hand landmark inside the lower-face box)
  blur     (Laplacian variance of the mouth crop resized to 128 px, divided by the clip median)

  python3 prebake_gate.py SRC.mp4 --face face_landmarker.task [--hand hand_landmarker.task] [--every 1]
                          [--bank bank.json] [--json out.json] [--gate-out SRC.gate.json]
Thresholds live in TH below; each one says where it comes from (DOC / MEASURED / GUESS). See ../SKILL.md.
"""
import argparse, json, math, os, sys
import numpy as np, cv2
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions

# (pass_max, soften_max) -- above soften_max = REJECT.  Provenance in SKILL.md section 4.
TH = {
    # key                  PASS bound, SOFTEN bound   provenance (DOC = Ditto repo/paper, MEASURED = our live runs, GUESS = needs the ladder)
    "face_found_pct_min": (99.0, 95.0),      # MEASURED: Maya bank 99.5 / Nova 99.9 / Daniel 100 all went live (corr 0.26-0.38)
    "no_face_run_ms":     (120, 600),        # MEASURED: live banks <=80 ms; BAKED-TAKE-PROCEDURE gesture bar ~600 ms
    "face_px_lo":         (200, 180),        # MEASURED: ditto_server docstring 200-320; maya-lips wide band 180-365
    "face_px_hi":         (470, 520),        # MEASURED: Professor 462 px (1.35x of Ditto's ~341 px face) held; >2x upscale = soft
    "yaw_range_deg":      (10, 25),          # GUESS: live-proven <=3 deg; clips >=34.5 deg lost the face 5-45 %
    "yaw_abs_deg":        (25, 35),          # MEASURED/GUESS: Zara rests at 23 deg, corr 0.477; clips 49-64 deg lost the face
    "pitch_range_deg":    (12, 20),          # MEASURED/GUESS: live-proven <=11.6 (Nova); rejected clips 15-37
    "roll_range_deg":     (8, 15),           # MEASURED/GUESS: live-proven <=7.9 (Nova)
    "disp_p95_pct":       (2.5, 4.0),        # MEASURED: Maya bank 2.17 live OK; clips >=3.9 lost the face. DOC: tracker crop = 1.5x lmk box of LAST frame
    "disp_max_pct":       (7.0, 10.0),       # MEASURED: Maya bank 6.72 live OK; GUESS above
    "rot_v_p95_deg":      (1.5, 3.0),        # MEASURED: Daniel 0.82 / Maya 0.93 / Nova 1.76 (weakest corr); wild clips 3.7-6.4
    "smo_res_p95_deg":    (1.5, 3.0),        # DOC mechanism (smo_k_s=13 mean filter); MEASURED: Daniel 0.99 / Maya 1.06 / Nova 2.29
    "mouth_p95":          (0.025, 0.040),    # MEASURED: Zara 0.0235 corr 0.477; Nova 0.0345 corr 0.26; Nova still 0.047 failed
    "hand_pct":           (0.0, 5.0),        # MEASURED (rule): maya-lips -- a hand over the face gets painted over; gate those frames
    "hand_run_ms":        (0, 600),          # same 600 ms gesture bar; gated frames = her own frozen mouth
    "blur_p05_rel":       (0.5, 0.35),       # MEASURED: live banks 0.53-0.80; GUESS below
}


def euler(m):
    R = np.asarray(m)[:3, :3]
    pitch = math.degrees(math.atan2(R[2, 1], R[2, 2]))
    yaw = math.degrees(math.asin(max(-1.0, min(1.0, -R[2, 0]))))
    roll = math.degrees(math.atan2(R[1, 0], R[0, 0]))
    return yaw, pitch, roll


def mean_filter(a, k=13):
    h = k // 2; n = len(a)
    return np.array([a[max(0, i - h):min(n, i + h + 1)].mean(0) for i in range(n)])


def scan(path, face_task, hand_task=None, every=1, track=False):
    """track=True (flag, default off): like Ditto's tracker, detect on a 2.5x crop around the LAST face instead of the
    full 1080x1920 frame (MediaPipe's short-range detector misses a 250 px face on a full tall frame when a dark
    garment sits under the chin -- measured on Zara B 2026-10-30; the same frames are found at once on a crop)."""
    fl = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=face_task), num_faces=1, output_facial_transformation_matrixes=True))
    hl = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=hand_task), num_hands=2)) if hand_task else None
    cap = cv2.VideoCapture(path); fps = cap.get(cv2.CAP_PROP_FPS) or 25; rows = []; i = -1; prev = None; last_box = None
    while True:
        ok, f = cap.read()
        if not ok: break
        i += 1
        if i % every: continue
        h, w = f.shape[:2]; s = 1920.0 / h
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)))
        r = fl.detect(img); ox = oy = 0; cw, chh = w, h
        if not r.face_landmarks and track and last_box is None:   # seed like Ditto's register(): the upper 60 % of the frame
            last_box = (w / 2.0, h * 0.3, h * 0.24)
        if not r.face_landmarks and track and last_box is not None:
            bx, by, bs = last_box; half = int(bs * 1.25)
            x0, y0 = max(0, int(bx - half)), max(0, int(by - half)); x1, y1 = min(w, int(bx + half)), min(h, int(by + half))
            if x1 - x0 > 32 and y1 - y0 > 32:
                crop = np.ascontiguousarray(f[y0:y1, x0:x1]); cw, chh = crop.shape[1], crop.shape[0]; ox, oy = x0, y0
                r = fl.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)))
        if not r.face_landmarks:
            rows.append({"i": i, "face": False}); prev = None; continue
        p = np.array([[q.x * cw + ox, q.y * chh + oy] for q in r.face_landmarks[0]], np.float32)
        last_box = (float(p[:, 0].mean()), float(p[:, 1].mean()), float(np.linalg.norm(p[152] - p[10])))
        fh = float(np.linalg.norm(p[152] - p[10])) or 1.0
        yaw, pitch, roll = euler(r.facial_transformation_matrixes[0])
        io = float(np.linalg.norm(p[33] - p[263])) or 1.0
        row = {"i": i, "face": True, "face_px": fh * s, "yaw": yaw, "pitch": pitch, "roll": roll,
               "yaw_proxy": float(abs(p[1][0] - (p[33][0] + p[263][0]) / 2) / io),
               "mouth": float(p[14][1] - p[13][1]) / fh, "nx": float(p[1][0]), "ny": float(p[1][1]), "fh": fh}
        # mouth crop sharpness (normalised to a 128 px crop so face size does not dominate)
        mx0, mx1 = p[[61, 291], 0].min(), p[[61, 291], 0].max(); my0, my1 = p[[0, 17], 1].min(), p[[0, 17], 1].max()
        cx, cy, half = (mx0 + mx1) / 2, (my0 + my1) / 2, max(mx1 - mx0, my1 - my0) * 0.75
        x0, y0 = int(max(0, cx - half)), int(max(0, cy - half)); x1, y1 = int(min(w, cx + half)), int(min(h, cy + half))
        crop = cv2.cvtColor(f[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY) if x1 > x0 + 4 and y1 > y0 + 4 else None
        row["sharp"] = float(cv2.Laplacian(cv2.resize(crop, (128, 128), interpolation=cv2.INTER_AREA), cv2.CV_64F).var()) if crop is not None else 0.0
        # hand over lower face: box from the nose bridge (6) down past the chin, cheek to cheek
        row["hand"] = False
        if hl:
            hr = hl.detect(img)
            bx0, bx1 = p[[234, 454], 0].min(), p[[234, 454], 0].max(); by0, by1 = p[6][1], p[152][1] + 0.1 * fh
            for hand in hr.hand_landmarks or []:
                hp = np.array([[q.x * w, q.y * h] for q in hand])
                if np.any((hp[:, 0] > bx0) & (hp[:, 0] < bx1) & (hp[:, 1] > by0) & (hp[:, 1] < by1)):
                    row["hand"] = True; break
        if prev is not None and prev.get("face"):
            row["disp"] = 100.0 * math.hypot(row["nx"] - prev["nx"], row["ny"] - prev["ny"]) / fh / every
            row["rot_v"] = max(abs(row[k] - prev[k]) for k in ("yaw", "pitch", "roll")) / every
        rows.append(row); prev = row
    cap.release()
    return rows, fps


def runs(flags):
    out, cur = [], 0
    for x in flags:
        if x: cur += 1
        elif cur: out.append(cur); cur = 0
    if cur: out.append(cur)
    return max(out) if out else 0


def summarise(rows, fps, every=1):
    n = len(rows); ok = [r for r in rows if r["face"]]
    pc = lambda a, q: float(np.percentile(a, q)) if len(a) else 0.0
    if not ok: return {"frames": n, "face_found_pct": 0.0}
    Y = np.array([[r["yaw"], r["pitch"], r["roll"]] for r in ok])
    # MediaPipe pose jitters ~1 deg frame to frame on a still face: take a 3-frame median before any velocity/residual
    Ys = np.array([np.median(Y[max(0, i - 1):i + 2], 0) for i in range(len(Y))])
    res = np.abs(Ys - mean_filter(Ys, max(1, 13 // every))).max(1) if len(Y) > 2 else np.zeros(1)
    rv = list(np.abs(np.diff(Ys, axis=0)).max(1) / every) if len(Ys) > 1 else []
    disp = [r["disp"] for r in ok if "disp" in r]
    sharp = np.array([r["sharp"] for r in ok]); med = float(np.median(sharp)) or 1.0
    yaw0 = float(np.median(Y[:, 0]))
    hand = [r.get("hand", False) for r in rows]
    return {
        "frames": n, "secs": round(n * every / fps, 2), "face_found_pct": round(100.0 * len(ok) / n, 1),
        "no_face_run_ms": round(runs([not r["face"] for r in rows]) * every * 1000 / fps),
        "face_px_p5": round(pc([r["face_px"] for r in ok], 5)), "face_px_p50": round(pc([r["face_px"] for r in ok], 50)),
        "face_px_p95": round(pc([r["face_px"] for r in ok], 95)),
        "yaw_rest_deg": round(yaw0, 1), "yaw_abs_p99_deg": round(pc(np.abs(Y[:, 0]), 99), 1),
        "yaw_range_deg": round(pc(Y[:, 0], 95) - pc(Y[:, 0], 5), 1),
        "pitch_range_deg": round(pc(Y[:, 1], 95) - pc(Y[:, 1], 5), 1),
        "roll_range_deg": round(pc(Y[:, 2], 95) - pc(Y[:, 2], 5), 1),
        "yaw_proxy_p50": round(pc([r["yaw_proxy"] for r in ok], 50), 3), "yaw_proxy_max": round(max(r["yaw_proxy"] for r in ok), 3),
        "disp_p95_pct": round(pc(disp, 95), 2), "disp_max_pct": round(max(disp) if disp else 0, 2),
        "rot_v_p95_deg": round(pc(rv, 95), 2), "rot_v_max_deg": round(max(rv) if rv else 0, 2),
        "smo_res_p95_deg": round(pc(res, 95), 2), "smo_res_max_deg": round(float(res.max()), 2),
        "mouth_p50": round(pc([r["mouth"] for r in ok], 50), 4), "mouth_p95": round(pc([r["mouth"] for r in ok], 95), 4),
        "hand_pct": round(100.0 * sum(hand) / n, 1), "hand_run_ms": round(runs(hand) * every * 1000 / fps),
        "blur_p05_rel": round(pc(sharp, 5) / med, 2),
    }


def verdict(s):
    """returns (overall, {metric: PASS|SOFTEN|REJECT})"""
    v = {}
    def hi(key, val):   # bigger is worse
        a, b = TH[key]; v[key] = "PASS" if val <= a else ("SOFTEN" if val <= b else "REJECT")
    def lo(key, val):   # smaller is worse
        a, b = TH[key]; v[key] = "PASS" if val >= a else ("SOFTEN" if val >= b else "REJECT")
    lo("face_found_pct_min", s["face_found_pct"])
    if s["face_found_pct"] == 0: return "REJECT", v
    hi("no_face_run_ms", s["no_face_run_ms"])
    lo("face_px_lo", s["face_px_p5"]); hi("face_px_hi", s["face_px_p95"])
    for k, m in [("yaw_range_deg", "yaw_range_deg"), ("yaw_abs_deg", "yaw_abs_p99_deg"), ("pitch_range_deg", "pitch_range_deg"),
                 ("roll_range_deg", "roll_range_deg"), ("disp_p95_pct", "disp_p95_pct"), ("disp_max_pct", "disp_max_pct"),
                 ("rot_v_p95_deg", "rot_v_p95_deg"), ("smo_res_p95_deg", "smo_res_p95_deg"), ("mouth_p95", "mouth_p95"),
                 ("hand_pct", "hand_pct"), ("hand_run_ms", "hand_run_ms")]:
        hi(k, s[m])
    lo("blur_p05_rel", s["blur_p05_rel"])
    vals = set(v.values())
    return ("REJECT" if "REJECT" in vals else "SOFTEN" if "SOFTEN" in vals else "PASS"), v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("--face", required=True); ap.add_argument("--hand")
    ap.add_argument("--every", type=int, default=1); ap.add_argument("--bank", help="bank.json: also judge each segment")
    ap.add_argument("--json"); ap.add_argument("--gate-out", help="write a ditto_server <src>.gate.json (no face / hand frames)")
    ap.add_argument("--track", action="store_true", help="Ditto-like: retry a missed frame on a crop around the last face (default off)")
    a = ap.parse_args()
    rows, fps = scan(a.video, a.face, a.hand, a.every, a.track)
    s = summarise(rows, fps, a.every); ov, v = verdict(s)
    out = {"clip": os.path.basename(a.video), "verdict": ov, "summary": s, "checks": v, "segments": []}
    if a.bank:
        for seg in json.load(open(a.bank))["segments"]:
            sr = [r for r in rows if seg["start"] <= r["i"] < seg["end"]]
            if len(sr) < 3: continue
            ss = summarise(sr, fps, a.every); so, sv = verdict(ss)
            out["segments"].append({"name": seg["name"], "kind": seg.get("kind"), "verdict": so,
                                    "fails": {k: x for k, x in sv.items() if x != "PASS"}, "summary": ss})
    print(json.dumps({k: out[k] for k in ("clip", "verdict", "summary")}, indent=1, default=float))
    print("non-PASS checks:", {k: x for k, x in v.items() if x != "PASS"})
    for seg in out["segments"]:
        print(f"  {seg['name']:<16s} {seg['kind'] or '':<8s} {seg['verdict']:<7s} {seg['fails']}")
    if a.json: json.dump(out | {"rows": rows}, open(a.json, "w"), default=float)
    if a.gate_out and a.every == 1:
        bad = [r["i"] for r in rows if not r["face"] or r.get("hand")]
        json.dump({"no_paste": bad, "rule": "prebake_gate: no face or hand over lower face"}, open(a.gate_out, "w"))


if __name__ == "__main__":
    main()
