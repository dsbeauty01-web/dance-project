"""drive_gate.py -- DITTO_GATE=1 (Seyzar take 4, 2026-11-09, default OFF): clean the 16 kHz copy of a TTS line that DRIVES the
lips. The viewer never hears this array (the shim pushes the separate HQ copy), so nothing audible changes.

Why: ElevenLabs ends a phrase with a soft breath / hum (~0.1-0.3 s at 20-60 % of the line's speech level). Ditto reads it as
speech and keeps the mouth moving after the last word ("...tonight-mmm"), and the old vad_alpha (-45 dB floor) kept the lips
on for it too. Two steps, per line:
  1. tail trim: before every quiet gap (>= GAP_MS under 20 % of the line's speech level) and before the end of the line, the
     low-energy run (< TAIL_FRAC 60 % of speech, at most TAIL_MAX_MS) is zeroed -- the mouth stops on the last real syllable.
  2. noise gate: anything under GATE_FRAC (20 %) of the line's speech level -> 0, 10 ms attack, 40 ms release (per-sample gain).
Speech level = 60th percentile of the 10 ms frame RMS over frames above 5 % of the line's loudest frame.
Env: DITTO_GATE_FRAC 0.20 · DITTO_TAIL_FRAC 0.60 · DITTO_TAIL_MAX_MS 400 · DITTO_GAP_MS 100 · DITTO_GATE_ATTACK_MS 10 · DITTO_GATE_RELEASE_MS 40
"""
import os

import numpy as np

E = os.environ.get
HOP = 160   # 10 ms at 16 kHz


def frame_rms(x, hop=HOP):
    n = len(x) // hop
    if n == 0: return np.zeros(0)
    return np.sqrt((x[:n * hop].reshape(n, hop).astype(np.float64) ** 2).mean(1) + 1e-12)


def speech_level(r):
    if not len(r) or r.max() <= 0: return 0.0
    v = r[r > 0.05 * r.max()]
    return float(np.percentile(v, 60)) if len(v) else 0.0


def gate(x, sr=16000, stats=None):
    """x float32 mono (16 kHz) -> gated copy, same length."""
    x = np.asarray(x, np.float32)
    if len(x) < HOP * 3 or sr != 16000: return x
    gf = float(E("DITTO_GATE_FRAC", "0.20")); tf = float(E("DITTO_TAIL_FRAC", "0.60"))
    tmax = int(float(E("DITTO_TAIL_MAX_MS", "400")) / 10); gap = max(1, int(float(E("DITTO_GAP_MS", "100")) / 10))
    att = max(1, int(float(E("DITTO_GATE_ATTACK_MS", "10")) * sr / 1000)); rel = max(1, int(float(E("DITTO_GATE_RELEASE_MS", "40")) * sr / 1000))
    r = frame_rms(x); n = len(r); lvl = speech_level(r)
    if lvl <= 0: return x
    on = r >= gf * lvl
    # quiet gaps (>= gap frames under the gate) + the line end -> trim the low tail just before each
    trimmed = 0
    i = 0; starts = []
    while i < n:
        if not on[i]:
            j = i
            while j < n and not on[j]: j += 1
            if j - i >= gap or j == n: starts.append(i)
            i = j
        else: i += 1
    if on[-1]: starts.append(n)                     # the line ends mid-sound: still trim its tail
    for s in starts:
        k = s
        while k > 0 and s - k < tmax and r[k - 1] < tf * lvl: k -= 1
        if k < s and k > 0:                          # never trim a whole line
            on[k:s] = False; trimmed += s - k
    # per-sample gain: target 1 where on, 0 where off; attack/release as one-pole ramps
    tgt = np.repeat(on.astype(np.float32), HOP)
    tgt = np.concatenate([tgt, np.full(len(x) - len(tgt), tgt[-1] if len(tgt) else 0, np.float32)])
    g = np.empty_like(tgt); cur = 0.0; up = 1.0 / att; dn = 1.0 / rel
    edges = np.flatnonzero(np.diff(tgt)) + 1; bounds = np.concatenate([[0], edges, [len(tgt)]])
    for a, b in zip(bounds[:-1], bounds[1:]):
        t = tgt[a]; m = b - a
        if t >= 0.5:
            ramp = np.minimum(1.0, cur + up * np.arange(1, m + 1))
        else:
            ramp = np.maximum(0.0, cur - dn * np.arange(1, m + 1))
        g[a:b] = ramp; cur = float(ramp[-1])
    y = (x * g).astype(np.float32)
    if stats is not None:
        stats.update(level=round(lvl * 32768), trimmed_ms=trimmed * 10, gated_frac=round(float(1 - on.mean()), 3), dur_s=round(len(x) / sr, 2))
    return y
