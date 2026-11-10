#!/usr/bin/env python3
"""lip_proof.py -- Nova's lip + sharpness yardstick. CPU only, no pod, no keys.

The SAME measurement the Maya build used to judge its best Ditto take ("Seyzar take 8",
maya-lt lane/motion-transfer: bench/lead_seyzar/take5_gate.py + tools/prof_qa.py), ported
so Nova is judged by numbers and pictures instead of opinion.

Per frame (MediaPipe FaceLandmarker, VIDEO mode), on the video resampled to a constant 25 fps
(so a variable-rate screen recording keeps its real timing against its own audio):
  lip SHAPE         16 lip landmarks relative to the nose tip / face height (landmarks 10-152)
  lip-shape motion  mean |shape(t) - shape(t-1)| x 1000          (take5_gate.py)
  gap               inner lips 13-14 / face height; width 61-291 / face height
  audio             rms per 40 ms frame of the file's own track, 16 kHz
  voiced            rms >= 20 % of the speech level (p60 of frames above 5 % of the loudest)
  silent            not voiced, >= 0.2 s after the last voiced frame, not right before an onset
  corr              Pearson(gap, rms), best lag in -8..+8 frames (the Maya gate) and, separately,
                    in -75..+75 frames: a best lag far from 0 means the lips are OUT OF SYNC
  mouth sharp @256  Laplacian variance / 100 of the mouth box resized to 256x256  (prof_qa.py)
  face sharp        Laplacian variance of the face box at delivered pixels (not resized)
  duplicates        share of 25 fps frames identical to the one before (mean abs diff < 0.1
                    on a 135x240 gray copy -- the calibrated method of docs/nova-ditto/DITTO-LIVE.md §6)

BARS (each one cited, none invented):
  corr_best >= 0.35               Nova's own bar           docs/NOVA-DITTO.md RUN-ME §5
  no frozen stretch > 2 s         docs/NOVA-DITTO.md RUN-ME §5 ("25 fps, no frozen stretch > 2 s")
  duplicates <= 15 %              [CLI-FILL] that doc says "25 fps" but sets no duplicate bar. The Maya
                                  reference take itself reads 10 % here (a still body in silence), so 15 %.
  face found >= 95 %              QUESTION: no Nova doc sets it; 95 % is this tool's default
  corr_best >= 0.50, silent motion <= 1.2, 0 open-in-silence, 0 pucker
                                  the Maya take-5..8 gate (take5_gate.py). Reported as "maya_gate";
                                  Seyzar take 8 itself measured corr 0.701, speaking 2.73, silent 1.98.

  python3 lip_proof.py VIDEO [--ref BODY.mp4] [--ss S] [--to S] [--json OUT.json] [--strip OUT.jpg]
                             [--model face_landmarker.task] [--label NAME] [--roi-top 0.0]
  --roi-top F   detect the face in the top F of the frame, upscaled (full-body framing: MediaPipe
                misses a face that is ~8 % of the frame -- docs/DITTO-FULLBODY.md §1). 0 = whole frame.
"""
import argparse, json, os, subprocess, sys
import numpy as np, cv2
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision

LIPS = [61, 291, 0, 17, 13, 14, 78, 308, 82, 312, 87, 317, 37, 267, 84, 314]
FPS = 25


def find_model(p):
    for c in (p, os.environ.get("FACE_LANDMARKER", ""), "/app/face_landmarker.task",
              os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_landmarker.task")):
        if c and os.path.exists(c): return c
    sys.exit("lip_proof: no face_landmarker.task (pass --model). REFUSING to guess.")


def probe(path):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,avg_frame_rate,nb_frames:format=duration", "-of", "json", path],
                       capture_output=True, text=True).stdout
    j = json.loads(o); s = j["streams"][0]
    num, den = s["avg_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(num) / max(float(den), 1e-9), float(j["format"]["duration"])


def frames_cfr(path, W, H, ss, to):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(ss)] if ss else []) + ["-i", path] + (["-t", str(to - ss)] if to else []) + \
          ["-vf", f"fps={FPS}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)
    p.wait()


def measure(path, model, ss=0.0, to=0.0, roi_top=0.0, keep_every=0):
    W, H, src_fps, dur = probe(path)
    fl = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=model), running_mode=vision.RunningMode.VIDEO, num_faces=1))
    P, G, Wd, FH, MS, FS, dup, crops = [], [], [], [], [], [], [], []
    prev_small = None; i = 0
    for f in frames_cfr(path, W, H, ss, to):
        small = cv2.cvtColor(cv2.resize(f, (135, 240), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
        dup.append(bool(prev_small is not None and float(np.abs(small - prev_small).mean()) < 0.1)); prev_small = small
        if roi_top > 0:
            hh = int(H * roi_top); up = 3 if hh * 3 <= 4096 else 2
            img = cv2.resize(f[:hh], (W * up, hh * up), interpolation=cv2.INTER_CUBIC); sx, sy = W, hh
        else:
            img, sx, sy = f, W, H
        r = fl.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB)), int(i * 1000 / FPS))
        if r.face_landmarks:
            L = np.array([[q.x * sx, q.y * sy] for q in r.face_landmarks[0]])
            pts = L[LIPS]; fh = float(np.linalg.norm(L[10] - L[152]))
            P.append(((pts - L[1]) / fh).ravel()); G.append(float(np.linalg.norm(pts[4] - pts[5]) / fh))
            Wd.append(float(np.linalg.norm(pts[0] - pts[1]) / fh)); FH.append(fh)
            cx, cy = L[13]; rr = int(max(40, float(np.linalg.norm(L[454] - L[234])) * 0.45))        # prof_qa.py mouth box
            c = f[max(0, int(cy - rr)):int(cy + rr), max(0, int(cx - rr)):int(cx + rr)]
            MS.append(float(cv2.Laplacian(cv2.resize(cv2.cvtColor(c, cv2.COLOR_BGR2GRAY), (256, 256)), cv2.CV_64F).var() / 100.0) if c.size else np.nan)
            x0, x1 = int(max(0, L[:, 0].min())), int(min(W, L[:, 0].max())); y0, y1 = int(max(0, L[:, 1].min())), int(min(H, L[:, 1].max()))
            fc = f[y0:y1, x0:x1]
            FS.append(float(cv2.Laplacian(cv2.cvtColor(fc, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()) if fc.size else np.nan)
            if keep_every and i % keep_every == 0 and c.size: crops.append((i, cv2.resize(c, (160, 160), interpolation=cv2.INTER_AREA)))
        else:
            P.append(np.full(32, np.nan)); G.append(np.nan); Wd.append(np.nan); FH.append(np.nan); MS.append(np.nan); FS.append(np.nan)
        i += 1
    n = i
    raw = subprocess.run(["ffmpeg", "-v", "error"] + (["-ss", str(ss)] if ss else []) + ["-i", path, "-t", f"{n / FPS:.3f}",
                          "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float64); hop = 16000 // FPS
    rms = np.array([np.sqrt((x[k * hop:(k + 1) * hop] ** 2).mean()) if (k + 1) * hop <= len(x) else 0.0 for k in range(n)])
    return dict(shape=np.array(P), gap=np.array(G), width=np.array(Wd), fh=np.array(FH), msharp=np.array(MS), fsharp=np.array(FS),
                dup=np.array(dup, bool), rms=rms, W=W, H=H, src_fps=src_fps, dur=dur, n=n, crops=crops, has_audio=len(x) > 0)


def runs(mask):
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]: j += 1
            out.append((i, j)); i = j
        else: i += 1
    return out


def xcorr(g, r, L):
    ok = np.isfinite(g); best = (float("nan"), 0)
    for s in range(-L, L + 1):
        if s >= 0: gg, rr, k = g[s:], r[:len(r) - s], ok[s:]
        else: gg, rr, k = g[:s], r[-s:], ok[:s]
        if k.sum() < 50 or np.nanstd(gg[k]) == 0 or np.std(rr[k]) == 0: continue
        c = float(np.corrcoef(gg[k], rr[k])[0, 1])
        if not np.isfinite(best[0]) or c > best[0]: best = (c, s)
    return best


def r_(v, k=3):
    return None if v is None or not np.isfinite(v) else round(float(v), k)


def judge(d, label):
    n = d["n"]; rms, gap, wd = d["rms"], d["gap"], d["width"]
    mv = np.concatenate([[np.nan], np.nanmean(np.abs(np.diff(d["shape"], axis=0)), axis=1) * 1000]) if n > 1 else np.full(n, np.nan)
    out = {"label": label, "frames_at_25fps": n, "seconds": round(n / FPS, 2), "delivered_wh": [d["W"], d["H"]],
           "file_fps": round(d["src_fps"], 2), "face_found_pct": round(float(np.isfinite(gap).mean()) * 100, 1) if n else 0.0,
           "face_px_p50": r_(np.nanmedian(d["fh"]), 0) if np.isfinite(d["fh"]).any() else None,
           "mouth_sharp256": r_(np.nanmean(d["msharp"]), 2) if np.isfinite(d["msharp"]).any() else None,
           "face_sharp_lapvar": r_(np.nanmean(d["fsharp"]), 1) if np.isfinite(d["fsharp"]).any() else None,
           "duplicate_pct": round(float(d["dup"].mean()) * 100, 1) if n else None,
           "longest_frozen_s": round(max([j - i for i, j in runs(d["dup"])], default=0) / FPS, 2)}
    lips = {}
    if d["has_audio"] and rms.max() > 0 and np.isfinite(gap).sum() >= 50:
        above = rms > 0.05 * rms.max(); lvl = float(np.percentile(rms[above], 60)) if above.sum() else 1.0
        voiced = rms >= 0.2 * lvl
        since = np.full(n, 10 ** 6); s_ = 10 ** 6
        for k in range(n):
            s_ = 0 if voiced[k] else s_ + 1; since[k] = s_
        until = np.full(n, 10 ** 6); u_ = 10 ** 6
        for k in range(n - 1, -1, -1):
            u_ = 0 if voiced[k] else u_ + 1; until[k] = u_
        sil = (~voiced) & (since >= 5) & (until >= 2)
        rest_w = float(np.nanmedian(wd[sil])) if np.isfinite(wd[sil]).sum() > 10 else float(np.nanmedian(wd))
        c8, l8 = xcorr(gap, rms, 8); c75, l75 = xcorr(gap, rms, 75)
        lips = {"voiced_s": round(float(voiced.sum()) / FPS, 1), "silent_s": round(float(sil.sum()) / FPS, 1),
                "lip_motion_speaking": r_(np.nanmean(mv[voiced]) if np.isfinite(mv[voiced]).any() else np.nan, 2),
                "lip_motion_silent": r_(np.nanmean(mv[sil]) if np.isfinite(mv[sil]).any() else np.nan, 2),
                "gap_speaking_p90": r_(np.nanpercentile(gap[voiced], 90) if np.isfinite(gap[voiced]).any() else np.nan, 4),
                "gap_silent_p90": r_(np.nanpercentile(gap[sil], 90) if np.isfinite(gap[sil]).any() else np.nan, 4),
                "open_in_silence_frames": int((sil & np.isfinite(gap) & (gap > 0.02)).sum()),
                "pucker_frames": int((sil & np.isfinite(wd) & (wd < 0.9 * rest_w)).sum()),
                "corr_best_lag8": r_(c8), "corr_lag8_frames": int(l8),
                "corr_best_lag75": r_(c75), "corr_lag75_frames": int(l75), "corr_lag75_ms": int(l75) * 40}
    out["lips"] = lips or None
    return out


def verdict(o, ref=None):
    """Honest PASS/FAIL per bar. A bar that could not be measured is 'NOT MEASURED', never a pass."""
    v = {}; L = o.get("lips")
    v["face_found>=95%"] = "PASS" if o["face_found_pct"] >= 95 else "FAIL"
    v["duplicates<=15%"] = "PASS" if o["duplicate_pct"] is not None and o["duplicate_pct"] <= 15 else "FAIL"
    v["no_frozen_stretch>2s"] = "PASS" if o["longest_frozen_s"] <= 2.0 else "FAIL"
    if L and L.get("corr_best_lag8") is not None:
        v["nova_corr>=0.35"] = "PASS" if L["corr_best_lag8"] >= 0.35 else "FAIL"
        v["in_sync(best lag within +-8 frames)"] = "PASS" if abs(L["corr_lag75_frames"]) <= 8 else "FAIL"
        mg = (L["corr_best_lag8"] >= 0.5 and L["lip_motion_silent"] is not None and L["lip_motion_silent"] <= 1.2
              and L["open_in_silence_frames"] == 0 and L["pucker_frames"] == 0)
        v["maya_gate(corr>=0.5, silent<=1.2, 0 open, 0 pucker)"] = "PASS" if mg else "FAIL"
    else:
        v["nova_corr>=0.35"] = "NOT MEASURED (no audio or no face)"
    if ref is not None and ref.get("mouth_sharp256") and o.get("mouth_sharp256"):
        ratio = o["mouth_sharp256"] / ref["mouth_sharp256"]; o["mouth_sharp_vs_body"] = round(ratio, 2)
        # maya-lips skill / REPORT-seyzar: a 720 cut of a 1080 source halves face sharpness -> anything <= 0.6 is that failure
        v["sharpness_kept(mouth >= 0.6 x body)"] = "PASS" if ratio >= 0.6 else "FAIL"
    commercial = [k for k in v if not k.startswith("maya_gate")]
    v["ALL_NOVA_BARS"] = "PASS" if all(v[k] == "PASS" for k in commercial) else "FAIL"
    return v


def strip(d, path, per_row=12):
    cr = d["crops"]
    if not cr: return False
    rows = []
    for a in range(0, len(cr), per_row):
        tiles = []
        for i, c in cr[a:a + per_row]:
            c = c.copy(); v = bool(d["rms"][i] >= 0.2 * (np.percentile(d["rms"][d["rms"] > 0.05 * d["rms"].max()], 60) if d["rms"].max() > 0 else 1e9))
            cv2.rectangle(c, (0, 0), (159, 159), (60, 200, 60) if v else (90, 90, 90), 3)
            cv2.putText(c, f"{i / FPS:.1f}s", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            tiles.append(c)
        while len(tiles) < per_row: tiles.append(np.zeros((160, 160, 3), np.uint8))
        rows.append(np.hstack(tiles))
    cv2.imwrite(path, np.vstack(rows[:8]), [cv2.IMWRITE_JPEG_QUALITY, 82]); return True


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("--ref", default=""); ap.add_argument("--ss", type=float, default=0)
    ap.add_argument("--to", type=float, default=0); ap.add_argument("--json", default=""); ap.add_argument("--strip", default="")
    ap.add_argument("--model", default=""); ap.add_argument("--label", default=""); ap.add_argument("--roi-top", type=float, default=0.0)
    ap.add_argument("--strip-every", type=int, default=5)
    a = ap.parse_args(); model = find_model(a.model)
    d = measure(a.video, model, a.ss, a.to, a.roi_top, keep_every=a.strip_every if a.strip else 0)
    o = judge(d, a.label or os.path.basename(a.video)); ref = None
    if a.ref:
        ref = judge(measure(a.ref, model, roi_top=a.roi_top), os.path.basename(a.ref))
        o["body_ref"] = {k: ref[k] for k in ("label", "delivered_wh", "face_px_p50", "mouth_sharp256", "face_sharp_lapvar")}
    o["verdict"] = verdict(o, ref)
    if a.strip: o["strip"] = os.path.basename(a.strip) if strip(d, a.strip) else None
    s = json.dumps(o, indent=1)
    if a.json: open(a.json, "w").write(s + "\n")
    print(s)


if __name__ == "__main__":
    main()
