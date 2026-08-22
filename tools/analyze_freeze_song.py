#!/usr/bin/env python3
"""FREEZE SONG ANALYZER — any song file in, a freeze-map out (one command).

Detects every MUSIC STOP (the moment the track cuts to silence so kids freeze) via
RMS-energy gating off the song clock, plus BPM and the groove sections between stops.

Usage:
    python analyze_freeze_song.py <audio-file> [out.json]
    # optional tuning: --floor-db -38  --min-stop-ms 250  --min-groove-ms 800

Output freeze-map.json:
{
  "song": "songA.mp3", "duration_ms": 123456, "bpm": 128.0,
  "stops":   [{"stop_start_ms":..., "stop_end_ms":..., "duration_ms":...}, ...],
  "grooves": [{"start_ms":..., "end_ms":..., "duration_ms":...}, ...]
}
"""
import sys, json, argparse
import numpy as np
import librosa

HOP = 512  # ~23 ms/frame @ 22050

def analyze(path, floor_db=-40.0, min_stop_ms=220, min_groove_ms=600, merge_gap_ms=500):
    y, sr = librosa.load(path, sr=22050, mono=True)
    dur_ms = int(len(y) / sr * 1000)

    # RMS energy per frame -> dB relative to the track's loud peak.
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=HOP)[0]
    ref = np.percentile(rms, 95) or rms.max() or 1e-9   # "how loud the music gets"
    db = 20.0 * np.log10(np.maximum(rms, 1e-9) / ref)
    times_ms = (np.arange(len(rms)) * HOP / sr * 1000.0)

    # A frame is SILENT (music stopped) when it drops well below the loud level.
    silent = db < floor_db

    # Group consecutive silent frames into candidate stops.
    stops = []
    i, n = 0, len(silent)
    while i < n:
        if silent[i]:
            j = i
            while j < n and silent[j]:
                j += 1
            s_ms = int(times_ms[i])
            e_ms = int(times_ms[j - 1] + HOP / sr * 1000.0)
            if e_ms - s_ms >= min_stop_ms:
                stops.append({"stop_start_ms": s_ms, "stop_end_ms": e_ms,
                              "duration_ms": e_ms - s_ms})
            i = j
        else:
            i += 1

    # Merge sub-stops separated by a tiny gap (beat-gaps inside ONE drop) into a single freeze.
    merged = []
    for s in stops:
        if merged and s["stop_start_ms"] - merged[-1]["stop_end_ms"] <= merge_gap_ms:
            merged[-1]["stop_end_ms"] = s["stop_end_ms"]
            merged[-1]["duration_ms"] = merged[-1]["stop_end_ms"] - merged[-1]["stop_start_ms"]
        else:
            merged.append(dict(s))
    stops = merged

    # Drop a leading/trailing silence that is just the file's head/tail, not a musical stop.
    stops = [s for s in stops if s["stop_start_ms"] > 300 and s["stop_end_ms"] < dur_ms - 300]

    # Groove sections = everything between the stops (the parts kids dance to).
    grooves, cursor = [], 0
    for s in stops:
        if s["stop_start_ms"] - cursor >= min_groove_ms:
            grooves.append({"start_ms": cursor, "end_ms": s["stop_start_ms"],
                            "duration_ms": s["stop_start_ms"] - cursor})
        cursor = s["stop_end_ms"]
    if dur_ms - cursor >= min_groove_ms:
        grooves.append({"start_ms": cursor, "end_ms": dur_ms, "duration_ms": dur_ms - cursor})

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = round(float(np.atleast_1d(tempo)[0]), 1)

    return {"song": path.replace("\\", "/").split("/")[-1], "duration_ms": dur_ms,
            "bpm": bpm, "stops": stops, "grooves": grooves}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("out", nargs="?", default=None)
    ap.add_argument("--floor-db", type=float, default=-40.0)
    ap.add_argument("--min-stop-ms", type=int, default=220)
    ap.add_argument("--min-groove-ms", type=int, default=600)
    ap.add_argument("--merge-gap-ms", type=int, default=500)
    a = ap.parse_args()

    m = analyze(a.audio, a.floor_db, a.min_stop_ms, a.min_groove_ms, a.merge_gap_ms)
    out = a.out or (a.audio.rsplit(".", 1)[0] + ".freeze-map.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2)

    print(f"{m['song']}: {m['duration_ms']/1000:.1f}s  BPM {m['bpm']}  "
          f"STOPS {len(m['stops'])}  grooves {len(m['grooves'])}")
    for k, s in enumerate(m["stops"], 1):
        print(f"  stop {k:2d}: {s['stop_start_ms']/1000:6.2f}s -> {s['stop_end_ms']/1000:6.2f}s "
              f"({s['duration_ms']} ms)")
    print("wrote", out)

if __name__ == "__main__":
    main()
