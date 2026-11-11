#!/usr/bin/env python3
"""tools/pod/freeze4_measure.py <results dir> — numbers from a FREEZE v4 pod run (tools/pod/freeze4_proof.py output).

Voice-to-face delay, from the page's own probes (A-page.json → probe), sampled every animation frame in the browser:
  v = her voice level (RMS of the audio actually playing),  m = mouth-area motion of the face video
  · onset delay: for every voice start (v > 0.01 after ≥ 400 ms below 0.008) the time until the mouth motion first rises
    above the silence threshold (95th percentile of m while she is silent, ×1.5), searched −500…+2000 ms
  · cross-correlation lag of the two envelopes (20 ms bins) over the run, −1000…+1000 ms; positive = face after voice
Sharpness = variance of the Laplacian on the centre 320x320 of a 512x512 face frame:
  published (face/published_speech_*.png, exactly what left the pod) vs received (A-face-received-*.png, the browser's frame).
Writes measure.json next to the inputs and prints it.
"""
import glob, json, os, sys
import numpy as np


def lap(path):
    import cv2
    g = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if g is None: return None
    g = cv2.resize(g, (512, 512), interpolation=cv2.INTER_AREA if g.shape[0] > 512 else cv2.INTER_CUBIC)
    return float(cv2.Laplacian(g[96:416, 96:416], cv2.CV_64F).var())


def main(d):
    A = json.load(open(os.path.join(d, "A-page.json")))
    P = A["probe"]; t = np.array(P["t"]); v = np.array(P["v"]); m = np.array(P["m"])
    res = {"samples": len(t), "probe_fps": round(len(t) / ((t[-1] - t[0]) / 1000), 1) if len(t) > 1 else 0}
    silent = v < 0.004
    base = float(np.percentile(m[silent], 95)) if silent.sum() > 50 else float(np.percentile(m, 50))
    thr = max(base * 1.5, 0.5)
    res["mouth_motion_silence_p95"] = round(base, 3); res["mouth_threshold"] = round(thr, 3)
    res["mouth_motion_speaking_p50"] = round(float(np.median(m[v > 0.01])), 3) if (v > 0.01).sum() else None
    # onsets
    onsets, last_sound = [], -1e9
    for i in range(len(t)):
        if v[i] > 0.01 and t[i] - last_sound >= 400: onsets.append(i)
        if v[i] > 0.008: last_sound = t[i]
    delays = []
    for i in onsets:
        w = (t >= t[i] - 500) & (t <= t[i] + 2000)
        idx = np.where(w & (m > thr))[0]
        if len(idx): delays.append(round(float(t[idx[0]] - t[i])))
    res["voice_onsets"] = len(onsets); res["onset_delay_ms"] = delays
    res["onset_delay_ms_median"] = float(np.median(delays)) if delays else None
    # cross-correlation on 20 ms bins
    if len(t) > 100:
        grid = np.arange(t[0], t[-1], 20.0)
        vi = np.interp(grid, t, v); mi = np.interp(grid, t, m)
        vi = (vi - vi.mean()) / (vi.std() or 1); mi = (mi - mi.mean()) / (mi.std() or 1)
        best, lag = -9, 0
        for L in range(-50, 51):
            c = float(np.mean(vi[max(0, -L):len(vi) - max(0, L)] * mi[max(0, L):len(mi) - max(0, -L)])) if abs(L) < len(vi) else -9
            if c > best: best, lag = c, L
        res["xcorr_lag_ms"] = lag * 20; res["xcorr_peak"] = round(best, 3)
    # talking time from the badge
    talk = sum(1 for b in P["badge"] if b == "talking"); res["badge_talking_share"] = round(talk / max(1, len(P["badge"])), 3)
    # her lines
    lg = A["log"]; res["lines_asked"] = [l["detail"] for l in lg if l["kind"] == "line"]
    res["lines_held_back"] = [l["detail"] for l in lg if l["kind"] == "line-held-back"]
    # staged line → her voice start (page clock)
    starts = [l["t"] for l in lg if l["kind"] == "her-voice" and l["detail"] == "start"]
    lat = []
    for l in lg:
        if l["kind"] == "line":
            nxt = [s for s in starts if s >= l["t"]]
            if nxt and nxt[0] - l["t"] < 10: lat.append(round((nxt[0] - l["t"]) * 1000))
    res["line_to_voice_ms"] = lat
    res["medal"] = next((e["detail"] for e in A["events"] if e.get("event") == "medal"), None)
    # sharpness
    pub = [x for x in (lap(p) for p in sorted(glob.glob(os.path.join(d, "face", "published_speech_*.png")))) if x is not None]
    rec = [x for x in (lap(p) for p in sorted(glob.glob(os.path.join(d, "A-face-received-*.png")))) if x is not None]
    res["sharpness_published"] = [round(x, 1) for x in pub]; res["sharpness_received"] = [round(x, 1) for x in rec]
    if pub and rec: res["sharpness_received_over_published"] = round(float(np.median(rec) / np.median(pub)), 3)
    json.dump(res, open(os.path.join(d, "measure.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
