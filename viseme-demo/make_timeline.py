# VISEME-DEMO: offline audio -> viseme timeline (Rhubarb-style, simplified).
# 20ms analysis frames: RMS energy + spectral centroid + rolloff decide the mouth.
# Output: timeline.json [{"t": sec, "v": sprite}] with >=80ms holds (no strobing).
import json
import os
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
w = wave.open(os.path.join(HERE, "nova-voice.wav"), "rb")
sr = w.getframerate()
pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
w.close()

HOP = int(sr * 0.02)
frames = []
for i in range(0, len(pcm) - HOP, HOP):
    seg = pcm[i:i + HOP]
    rms = float(np.sqrt(np.mean(seg ** 2)))
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    freqs = np.fft.rfftfreq(len(seg), 1 / sr)
    centroid = float((spec * freqs).sum() / (spec.sum() + 1e-9))
    frames.append((i / sr, rms, centroid))

peak = max(r for _, r, _ in frames)
rng = np.random.default_rng(7)

raw = []
for t, rms, cen in frames:
    e = rms / (peak + 1e-9)
    if e < 0.06:
        v = "rest"
    elif e < 0.16:
        v = "mbp" if cen < 900 else "small"
    elif e < 0.38:
        if cen > 3400:
            v = "I" if rng.random() < 0.6 else "E"
        elif cen > 1800:
            v = "E" if rng.random() < 0.5 else "smile"
        elif cen < 900:
            v = "U" if rng.random() < 0.5 else "O"
        else:
            v = "small" if rng.random() < 0.4 else "A"
    else:
        if cen < 1100:
            v = "O"
        elif cen > 3200:
            v = "E"
        else:
            v = "A" if rng.random() < 0.65 else "wide"
    raw.append((round(t, 3), v))

# merge to >=80ms holds; occasional L/fv seasoning on transitions for life
timeline = []
last_v, last_t = None, 0.0
for t, v in raw:
    if v != last_v and (t - last_t >= 0.08 or last_v is None):
        if last_v and last_v not in ("rest", "mbp") and v not in ("rest", "mbp") and rng.random() < 0.07:
            timeline.append({"t": round(t, 3), "v": "L" if rng.random() < 0.5 else "fv"})
            last_t = t + 0.06
            timeline.append({"t": round(t + 0.06, 3), "v": v})
        else:
            timeline.append({"t": t, "v": v})
            last_t = t
        last_v = v

json.dump(timeline, open(os.path.join(HERE, "timeline.json"), "w"))
dur = len(pcm) / sr
counts = {}
for e in timeline:
    counts[e["v"]] = counts.get(e["v"], 0) + 1
print(f"duration {dur:.1f}s, {len(timeline)} viseme events, mix: {counts}")
