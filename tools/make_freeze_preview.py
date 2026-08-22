#!/usr/bin/env python3
"""FINALFREEZE preview (GATE 1): render a CONTINUOUS ~40s window of OUR track with the new
freezes applied exactly as the game will sound — hard-mute (no fade) + vinyl-stop SFX +
slam-back (pause/resume). NOT a montage: one unbroken stretch of the real song.

Usage: make_freeze_preview.py <song.mp3> <out.wav> [win_start_s] [win_end_s]
"""
import sys
import numpy as np
import librosa
import soundfile as sf

SR = 44100
BPM = 129.2
BEAT = 60.0 / BPM

def snap(t):
    """Snap a time to the 129-BPM beat grid."""
    return round(round(t / BEAT) * BEAT, 3)

# NEW LEVEL — 8 freezes on our 132.3s track. holds 2.5s (final 4.5), gaps varied 8-30s,
# ONE double-stab fake-out mid-song (65 & 68 = ~3s apart), final = star + biggest points.
# Intro clear (first ~11s). Gaps VARIED/unpredictable (7-12s, avg ~10, non-monotonic).
# ONE double-stab (61/64 = ~3s pair, one event). Final = star, 4.5s, biggest pts.
FREEZES = [
    {"at": snap(11.0),  "hold": 2.5, "clip": "frog",     "pts": 100},   # gap  -
    {"at": snap(23.0),  "hold": 2.5, "clip": "bear",     "pts": 150},   # gap 12
    {"at": snap(30.0),  "hold": 2.5, "clip": "flamingo", "pts": 200},   # gap  7
    {"at": snap(41.0),  "hold": 2.5, "clip": "star",     "pts": 250},   # gap 11
    {"at": snap(49.0),  "hold": 2.5, "clip": "frog",     "pts": 300},   # gap  8
    {"at": snap(61.0),  "hold": 2.5, "clip": "bear",     "pts": 350},   # gap 12  double-stab A
    {"at": snap(64.0),  "hold": 2.5, "clip": "bear",     "pts": 350},   # +3      double-stab B
    {"at": snap(71.0),  "hold": 2.5, "clip": "flamingo", "pts": 450},   # gap  7 (from 64)
    {"at": snap(83.0),  "hold": 2.5, "clip": "frog",     "pts": 550},   # gap 12
    {"at": snap(91.0),  "hold": 2.5, "clip": "star",     "pts": 700},   # gap  8
    {"at": snap(102.0), "hold": 2.5, "clip": "bear",     "pts": 850},   # gap 11
    {"at": snap(114.0), "hold": 4.5, "clip": "star",     "pts": 1100, "final": True},  # gap 12
]

def vinyl_stop(sr=SR):
    """Record-stop: pitch chirps down ~360->28 Hz over 0.4s with a fast decay + a click transient."""
    d = 0.40
    t = np.arange(0, d, 1.0 / sr)
    f0, f1 = 360.0, 28.0
    phase = 2 * np.pi * (f0 * t + (f1 - f0) / (2 * d) * t * t)
    env = np.exp(-5.0 * t)
    body = 0.40 * np.sin(phase) * env
    body[:int(0.004 * sr)] += 0.5 * np.hanning(int(0.008 * sr))[:int(0.004 * sr)]  # snap transient
    return body.astype(np.float32)

def micro_edge(seg, ms=2):
    n = int(SR * ms / 1000)
    if len(seg) > 2 * n:
        seg[:n] *= np.linspace(0, 1, n); seg[-n:] *= np.linspace(1, 0, n)
    return seg

def main():
    song, out = sys.argv[1], sys.argv[2]
    win_a = float(sys.argv[3]) if len(sys.argv) > 3 else 49.0
    win_b = float(sys.argv[4]) if len(sys.argv) > 4 else 80.0
    nosfx = "nosfx" in sys.argv[5:]
    y, _ = librosa.load(song, sr=SR, mono=True)
    sfx = np.zeros(1, dtype=np.float32) if nosfx else vinyl_stop()

    fr = [f for f in FREEZES if win_a <= f["at"] < win_b]
    parts, cursor = [], win_a
    for f in fr:
        at, hold = f["at"], f["hold"]
        parts.append(micro_edge(y[int(cursor * SR):int(at * SR)].copy()))   # groove up to freeze
        gap = np.zeros(int(hold * SR), dtype=np.float32); gap[:len(sfx)] += sfx
        parts.append(gap)                                                    # HARD mute + vinyl-stop
        cursor = at                                                         # resume from pause point
    parts.append(micro_edge(y[int(cursor * SR):int(win_b * SR)].copy()))     # groove out
    mix = np.clip(np.concatenate(parts), -1.0, 1.0)
    sf.write(out, mix, SR)
    print(f"wrote {out}  ({len(mix)/SR:.1f}s)  freezes in window: "
          + ", ".join(f"{f['at']}s({f['clip']})" for f in fr))
    print("FULL ARRAY:", ", ".join(f"{f['at']}/{f['hold']}s/{f['pts']}" for f in FREEZES))

if __name__ == "__main__":
    main()
