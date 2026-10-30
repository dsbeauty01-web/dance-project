#!/usr/bin/env python3
"""ditto_body_prep.py -- prepare and GATE a body video for Ditto. CPU only: no GPU, no pod,
no money. Run it before you ever rent a pod.

What it does
  1. Measures where her face is in the source (MediaPipe FaceLandmarker, on a head-region crop
     so a small face is still found) and works out the 9:16 knees-up crop that puts her face
     inside Ditto's 200-470 px band in a 1080x1920 frame.
  2. Cuts that crop with ffmpeg: crop -> scale 1080x1920 (lanczos) -> `-r 25`.
     `-r 25` RESAMPLES FRAMES ONLY. It never changes her speed. (A speed change is what
     `setpts`/`atempo` do, and this tool never emits either.)
  3. Runs maya-lt's tools/prebake_gate.py on the result and prints the verdict, the face_px
     p5/p50/p95 and EVERY non-PASS check.
  4. Exits non-zero on REJECT. A rejected body is not shipped.

  python3 ditto_body_prep.py SRC.mp4 -o nova_body.mp4 --gate /path/to/maya-lt/tools/prebake_gate.py
         [--crop W:H:X:Y]   use this exact crop instead of measuring one
         [--face-target 280] aim the delivered face height here (default 280 px)
         [--models DIR]     where face_landmarker.task / hand_landmarker.task live (downloaded
                            if missing, same URLs ditto_up.sh uses)
         [--allow-soften]   exit 0 on SOFTEN (the default already does; use --strict for PASS only)
         [--strict]         exit non-zero on anything but PASS
         [--gate-out F]     also write the <src>.gate.json ditto_server.py reads

Why the crop is not optional (measured, docs/DITTO-TRY.md 2026-10-29)
  At Nova's full-body framing her face is ~158 px tall in a 1920-high frame. MediaPipe finds it
  in 0.0 % of frames, and ditto_server.py takes its FIRST-FRAME CROP from MediaPipe
  (ditto_wide.patch_first_frame_crop) -- so Ditto cannot even start on an unreframed body.
  A 9:16 knees-up crop at zoom ~1.72x puts her at ~298 px and finds her on 100 % of frames.

What the gate usually objects to AFTER the crop is not face size. It is
  * mouth_p95 -- her resting mouth sits OPEN (the Kling idles smile with teeth). Bound 0.025.
  * disp_p95 / rot_v / smo_res -- her head moves too fast between frames.
  Both are properties of the generated clip, so they are fixed by generating a better clip
  (closed-mouth smile, gentle sway, static camera), not by any flag here.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import urllib.request

MODEL_URLS = {
    # the same files ditto_up.sh pulls
    "face_landmarker.task":
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
    "hand_landmarker.task":
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
}
DITTO_FACE_LO, DITTO_FACE_HI = 200, 470          # prebake_gate TH["face_px_lo"/"face_px_hi"] PASS band
OUT_W, OUT_H, OUT_FPS = 1080, 1920, 25


def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def ensure_models(d):
    os.makedirs(d, exist_ok=True)
    out = {}
    for name, url in MODEL_URLS.items():
        p = os.path.join(d, name)
        if not os.path.exists(p) or os.path.getsize(p) < 10000:
            print(f"   fetching {name} ...")
            urllib.request.urlretrieve(url, p)
        out[name] = p
    return out


def probe(path):
    r = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
            "stream=width,height,r_frame_rate,nb_frames", "-of", "json", path])
    s = json.loads(r.stdout)["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(num) / float(den), int(s.get("nb_frames") or 0)


def measure_face(path, face_task, every=4):
    """Face height in the SOURCE, measured on a head-region crop so a ~158 px face is still
    found. Returns (median face px in a 1920-high delivered frame, median nose x, median nose y)."""
    import numpy as np, cv2
    import mediapipe as mp
    from mediapipe.tasks.python import vision, BaseOptions
    fl = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=face_task), num_faces=1))
    cap = cv2.VideoCapture(path)
    fh, nx, ny = [], [], []
    i = -1
    while True:
        ok, f = cap.read()
        if not ok:
            break
        i += 1
        if i % every:
            continue
        H, W = f.shape[:2]
        # look in the top 45 % of the frame, upscaled 3x -- a standing figure's head lives there
        band = f[0:int(H * 0.45), :]
        up = cv2.resize(band, (band.shape[1] * 3, band.shape[0] * 3), interpolation=cv2.INTER_CUBIC)
        img = mp.Image(image_format=mp.ImageFormat.SRGB,
                       data=np.ascontiguousarray(cv2.cvtColor(up, cv2.COLOR_BGR2RGB)))
        r = fl.detect(img)
        if not r.face_landmarks:
            continue
        p = np.array([[q.x * up.shape[1] / 3.0, q.y * up.shape[0] / 3.0] for q in r.face_landmarks[0]])
        fh.append(float(np.linalg.norm(p[152] - p[10])))
        nx.append(float(p[1][0]))
        ny.append(float(p[1][1]))
    cap.release()
    try:
        fl.close()          # else mediapipe's __del__ fires during interpreter shutdown and shouts
    except Exception:
        pass
    if not fh:
        return None
    import statistics as st
    sh_ = 1920.0 / H
    return st.median(fh) * sh_, st.median(nx), st.median(ny), len(fh)


def plan_crop(src_w, src_h, face_px_delivered, nose_x, nose_y, target):
    """A 9:16 box of src/Z, placed so her face sits where it does in the DITTO-TRY crop that
    worked (docs/ditto-try/reframe_plan.jsonl: nose about 23 % down the box, centred in x)."""
    Z = target / face_px_delivered
    cw = int(round(src_w / Z / 2) * 2)
    ch = int(round(cw * OUT_H / OUT_W / 2) * 2)
    if ch > src_h:                      # cannot zoom less than the frame allows
        ch = src_h - (src_h % 2)
        cw = int(round(ch * OUT_W / OUT_H / 2) * 2)
        Z = src_w / cw
    x = int(round(nose_x - cw / 2.0))
    y = int(round(nose_y - 0.23 * ch))
    x = max(0, min(x, src_w - cw))
    y = max(0, min(y, src_h - ch))
    return cw, ch, x, y, Z


def run_gate(gate_py, clip, models, gate_out=None):
    cmd = [sys.executable, gate_py, clip, "--face", models["face_landmarker.task"],
           "--hand", models["hand_landmarker.task"]]
    if gate_out:
        cmd += ["--gate-out", gate_out]
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as t:
        jp = t.name
    cmd += ["--json", jp]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr[-3000:], file=sys.stderr)
        raise SystemExit(f"prebake_gate.py failed (rc {r.returncode})")
    d = json.load(open(jp))
    os.unlink(jp)
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--gate", required=True, help="path to maya-lt tools/prebake_gate.py")
    ap.add_argument("--crop", help="W:H:X:Y -- skip measuring and use this box")
    ap.add_argument("--face-target", type=float, default=280.0)
    ap.add_argument("--models", default=os.path.expanduser("~/.nova/models"))
    ap.add_argument("--gate-out")
    ap.add_argument("--strict", action="store_true", help="only PASS is good enough")
    ap.add_argument("--keep-fps", action="store_true",
                    help="do NOT resample to 25 fps (only for clips already at 25)")
    a = ap.parse_args()

    if not os.path.exists(a.gate):
        raise SystemExit(f"--gate {a.gate} not found. It is tools/prebake_gate.py in "
                         f"dsbeauty01-web/maya-lt @ lane/motion-transfer.")
    print(f"== source {a.src}")
    w, h, fps, n = probe(a.src)
    print(f"   {w}x{h} @ {fps:.3f} fps, {n} frames")
    models = ensure_models(a.models)

    if a.crop:
        cw, ch, cx, cy = (int(v) for v in a.crop.split(":"))
        Z = w / cw
        print(f"   crop given: {cw}:{ch}:{cx}:{cy}  (zoom {Z:.3f}x)")
    else:
        print("== measuring her face")
        m = measure_face(a.src, models["face_landmarker.task"])
        if m is None:
            raise SystemExit("no face found anywhere in the source — this is not a usable body")
        fpx, nx, ny, seen = m
        print(f"   face {fpx:.1f} px delivered (needs {DITTO_FACE_LO}-{DITTO_FACE_HI}), "
              f"nose at ({nx:.0f},{ny:.0f}), found on {seen} sampled frames")
        if DITTO_FACE_LO <= fpx <= DITTO_FACE_HI:
            print("   NOTE: the face is already in band — the crop will only re-centre it")
        cw, ch, cx, cy, Z = plan_crop(w, h, fpx, nx, ny, a.face_target)
        print(f"   crop {cw}:{ch}:{cx}:{cy}  zoom {Z:.3f}x  -> face ~{fpx * Z:.0f} px")

    vf = f"crop={cw}:{ch}:{cx}:{cy},scale={OUT_W}:{OUT_H}:flags=lanczos"
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", a.src, "-vf", vf]
    if not a.keep_fps:
        cmd += ["-r", str(OUT_FPS)]          # FRAME RESAMPLE ONLY — never a speed change
    cmd += ["-an", "-crf", "16", "-pix_fmt", "yuv420p", a.out]
    print(f"== cutting\n   ffmpeg -vf \"{vf}\"" + ("" if a.keep_fps else f" -r {OUT_FPS}"))
    sh(cmd)
    ow, oh, ofps, on_ = probe(a.out)
    print(f"   {a.out}: {ow}x{oh} @ {ofps:.3f} fps, {on_} frames")
    # a speed change would alter the DURATION; a frame resample does not
    src_dur = n / fps if n and fps else 0
    out_dur = on_ / ofps if on_ and ofps else 0
    if src_dur and out_dur and abs(src_dur - out_dur) > 0.08:
        print(f"   !! duration moved {src_dur:.2f}s -> {out_dur:.2f}s — that is a SPEED CHANGE, "
              f"not a frame resample. Refusing.")
        return 4
    print(f"   duration {src_dur:.2f}s -> {out_dur:.2f}s (unchanged — frames resampled, not sped)")

    print(f"== gate ({a.gate})")
    d = run_gate(a.gate, a.out, models, a.gate_out)
    s, v = d["summary"], d["checks"]
    print(f"   VERDICT: {d['verdict']}")
    print(f"   face_px p5/p50/p95: {s['face_px_p5']} / {s['face_px_p50']} / {s['face_px_p95']}"
          f"   (Ditto band {DITTO_FACE_LO}-{DITTO_FACE_HI})")
    print(f"   face found: {s['face_found_pct']} %   mouth_p95: {s['mouth_p95']}   "
          f"disp_p95: {s['disp_p95_pct']}   rot_v_p95: {s['rot_v_p95_deg']}   "
          f"smo_res_p95: {s['smo_res_p95_deg']}")
    bad = {k: x for k, x in v.items() if x != "PASS"}
    if bad:
        print("   non-PASS checks:")
        for k, x in sorted(bad.items(), key=lambda kv: (kv[1] != "REJECT", kv[0])):
            print(f"     {x:<7s} {k} = {s.get(k, s.get(k.replace('_lo', '_p5').replace('_hi', '_p95'), '?'))}")
    else:
        print("   every check PASS")

    if d["verdict"] == "REJECT":
        print("\n   REJECTED — this body is not shipped. The usual causes, in order:")
        print("     mouth_p95 high  -> her resting mouth is open. Generate with a CLOSED-MOUTH smile.")
        print("     disp/rot_v/smo  -> her head moves too fast. Ask for a gentler sway, static camera.")
        print("     face_px low     -> zoom in more (raise --face-target).")
        return 5
    if a.strict and d["verdict"] != "PASS":
        print("\n   --strict: only PASS is accepted.")
        return 6
    print(f"\n   OK: {a.out} gates {d['verdict']} — usable as DITTO_SRC.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
