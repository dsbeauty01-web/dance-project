#!/usr/bin/env python3
"""build_nova_fb_bank.py -- build a FULL-BODY Ditto motion bank for Nova out of material we
already have, in the shape maya-lt's maya-ops/lt/motion_bank.py loads (assets/live_motion/nova/
nova_bank.json was the template).

  idle    = the calm full-body body generated 2026-10-31 (gate SOFTEN on everything except face
            size, mouth_p95 0.0209). It was generated with image_url == tail_image_url, so it
            already begins and ends on the same rest pose.
  gesture = a window of beta/sources/groove-1080/round2/D-take2.mp4, the dance take whose HEAD
            motion passes the gate (yaw 5.2 deg, pitch 7.3 deg, rot_v 1.07); only its open
            resting mouth fails, which matters for an idle and not for a 3-4 s gesture.

THE LAW THIS HAS TO OBEY: every segment starts and ends on the same rest pose, or the junction
reads as a jump. The idle satisfies it by construction. For the gesture this script MEASURES it:
it scores every candidate window by the pixel distance between its first and last frame and
takes the best, and it prints that distance next to the idle's own so the two are comparable.
No window is accepted on faith -- the number is in the bank json as `loop_mae`.

  python3 build_nova_fb_bank.py --out <dir>            build nova_fb_bank.mp4 + .json
  python3 build_nova_fb_bank.py --out <dir> --measure  measure only, write nothing
"""
import argparse
import json
import os
import subprocess
import sys

import cv2
import numpy as np

IDLE = "docs/nova-ditto/fullbody/nova_fullbody_calm.mp4"
GEST = "beta/sources/groove-1080/round2/D-take2.mp4"
FPS = 25
# the explicit first-frame detection boxes the pod measured on 2026-10-31 (docs/DITTO-FULLBODY.md
# section 2); frame 0 of the bank video comes from the idle, so the idle's box is the one Ditto needs.
BOX_IDLE = [263, 215, 763, 715]
BOX_GEST = [288, 200, 798, 710]
# the reference bank trims the eased, edge-locked still frames off both ends of every segment
# (idle +5/-6, gesture +1/-5) because the junction stills read as a 0.4 s freeze. Same here.
IDLE_TRIM = (5, 6)
# ...but ONLY the Kling-generated idle has those eased still ends. D-take2 is a real camera take
# with none, so trimming it just moves the window off its measured best loop: with (1,5) the
# gesture's loop_mae measured 9.017 against 3.301 untrimmed. Measured, so: no trim.
GEST_TRIM = (0, 0)


def thumbs(path, fps=None):
    """every frame as a small grayscale float array, for distance measuring only."""
    cmd = ["ffmpeg", "-v", "error", "-i", path]
    if fps:
        cmd += ["-r", str(fps)]
    cmd += ["-vf", "scale=96:172", "-pix_fmt", "gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, stdout=subprocess.PIPE, check=True).stdout
    n = len(raw) // (96 * 172)
    return np.frombuffer(raw[: n * 96 * 172], np.uint8).reshape(n, 172, 96).astype(np.float32)


def mae(a, b):
    return float(np.abs(a - b).mean())


def best_window(t, lo, hi):
    """the window of length lo..hi frames whose first and last frame are most alike."""
    best = None
    n = len(t)
    for ln in range(lo, hi + 1):
        for s in range(0, n - ln):
            d = mae(t[s], t[s + ln])
            if best is None or d < best[0]:
                best = (d, s, s + ln)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    ap.add_argument("--out", required=True)
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--gest-lo", type=int, default=80)   # 3.2 s at 25 fps
    ap.add_argument("--gest-hi", type=int, default=100)  # 4.0 s
    a = ap.parse_args()

    idle_p = os.path.join(a.repo, IDLE)
    gest_p = os.path.join(a.repo, GEST)
    for p in (idle_p, gest_p):
        if not os.path.exists(p):
            sys.exit(f"missing {p}")

    ti = thumbs(idle_p)
    tg = thumbs(gest_p, fps=FPS)          # 24 -> 25 fps, frames only
    print(f"idle  {len(ti)} frames   gesture {len(tg)} frames (resampled to {FPS} fps)")

    i0, i1 = IDLE_TRIM[0], len(ti) - IDLE_TRIM[1]
    idle_loop = mae(ti[i0], ti[i1 - 1])
    print(f"idle  segment [{i0},{i1})  loop_mae {idle_loop:.3f}   <- the reference the gesture is judged against")

    d, gs, ge = best_window(tg, a.gest_lo, a.gest_hi)
    g0, g1 = gs + GEST_TRIM[0], ge - GEST_TRIM[1]
    print(f"gesture best window [{gs},{ge}) len {ge-gs}f = {(ge-gs)/FPS:.2f}s  loop_mae {d:.3f}")
    print(f"gesture segment after trim [{g0},{g1})  loop_mae {mae(tg[g0], tg[g1-1]):.3f}")
    # the junction cost: how far the gesture's rest pose is from the idle's. The scheduler
    # crossfades DITTO_GESTURE_XFADE frames over this, so it is softened, not hidden.
    junction = mae(ti[i0], tg[g0])
    print(f"junction idle->gesture mae {junction:.3f}  (crossfaded over DITTO_GESTURE_XFADE frames)")

    if a.measure:
        return 0

    os.makedirs(a.out, exist_ok=True)
    vid = os.path.join(a.out, "nova_fb_bank.mp4")
    seg_i = os.path.join(a.out, "_seg_idle.mp4")
    seg_g = os.path.join(a.out, "_seg_gest.mp4")
    # both segments to the SAME 1076x1924 @ 25 fps, no scaling, so the concat is frame-exact and
    # Ditto's one max_size resize applies to the whole bank uniformly.
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", idle_p, "-r", str(FPS),
                    "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", "-an", seg_i], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", gest_p, "-r", str(FPS),
                    "-vf", f"select='between(n\\,{gs}\\,{ge-1})',setpts=N/{FPS}/TB",
                    "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", "-an", seg_g], check=True)
    lst = os.path.join(a.out, "_concat.txt")
    with open(lst, "w") as f:
        f.write(f"file '{os.path.abspath(seg_i)}'\nfile '{os.path.abspath(seg_g)}'\n")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-an", vid], check=True)

    cap = cv2.VideoCapture(vid)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w, h = int(cap.get(3)), int(cap.get(4))
    cap.release()
    n_idle = len(ti)
    n_gest = ge - gs
    if total != n_idle + n_gest:
        print(f"WARN: concat produced {total} frames, expected {n_idle + n_gest}")

    spec = {
        "video": os.path.basename(vid),
        "fps": FPS,
        "frames": total,
        "segments": [
            {"name": "nova_fb_idle", "kind": "idle", "start": i0, "end": i1,
             "secs": round((i1 - i0) / FPS, 2), "src": os.path.basename(idle_p),
             "raw": [0, n_idle], "loop_mae": round(idle_loop, 3), "no_paste": 0, "seam": 0.0},
            {"name": "nova_fb_groove", "kind": "gesture",
             "start": n_idle + GEST_TRIM[0], "end": n_idle + n_gest - GEST_TRIM[1],
             "secs": round((n_gest - sum(GEST_TRIM)) / FPS, 2), "src": os.path.basename(gest_p),
             "raw": [n_idle, n_idle + n_gest], "loop_mae": round(d, 3),
             "junction_mae": round(junction, 3), "no_paste": 0, "seam": 0.0},
        ],
        # honest aliases: this clip is a four-bar GROOVE, not a wave. There is no full-body wave
        # clip in either repo, so 'wave' is NOT aliased to it -- asking for a wave gets an honest
        # refusal rather than a groove pretending to be one.
        "aliases": {"groove": "nova_fb_groove", "greet": "nova_fb_groove",
                    "hello": "nova_fb_groove", "dance": "nova_fb_groove"},
        "built": "dance-project tools/pod/build_nova_fb_bank.py (branch nova-ditto, 2026-11-01)",
        "wh": [w, h],
        "boxes": {"nova_fb_idle": BOX_IDLE, "nova_fb_groove": BOX_GEST,
                  "note": "Ditto detects a face on frame 0 only (source2info._crop early-returns on "
                          "last_lmk); frame 0 of the bank is the idle, so DITTO_FB_BOX is the idle box."},
        "trim_note": "segments skip the eased still ends (idle +5/-6, gesture +1/-5); 'raw' is the full clip",
        "gesture_note": "no wave exists at full-body framing; this is D-take2's groove, mouth_p95 "
                        "0.0423 (over the idle gate) which is why it is a short gesture and not the idle",
    }
    with open(os.path.join(a.out, "nova_fb_bank.json"), "w") as f:
        json.dump(spec, f, indent=1)
    for p in (seg_i, seg_g, lst):
        os.remove(p)
    print(f"\nbank: {vid}  {total} frames {w}x{h} @ {FPS} fps")
    print(f"spec: {os.path.join(a.out, 'nova_fb_bank.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
