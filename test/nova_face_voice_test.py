#!/usr/bin/env python3
"""test/nova_face_voice_test.py — the voice-hole fix in tools/pod/nova_face.py (FACE_VOICE_PREBUF_MS), offline, simulated time.
Her line arrives as 0.2 s pieces at speaking speed (pod/rt_lk.py FLUSH) with arrival jitter; the Ditto renderer takes a 0.4 s
chunk every 0.4 s. Counts the holes (zero-padded takes in the MIDDLE of the line) with the flag off (today) and on.
Run: python3 -I test/nova_face_voice_test.py   (needs numpy + aiohttp; no GPU, no network)"""
import importlib.util, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))

def load(prebuf):
    os.environ["FACE_VOICE_PREBUF_MS"] = str(prebuf); os.environ["FACE_OUT"] = os.path.join("/tmp", "nf_voice_test")
    spec = importlib.util.spec_from_file_location("nova_face_%d" % prebuf, os.path.join(HERE, "..", "tools", "pod", "nova_face.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def run(prebuf, seed, line_s=8.0, jitter=0.06, take_phase=None, rate=1.0):
    m = load(prebuf); rnd = random.Random(seed); np = m.np
    piece = int(0.2 * m.SR); n = 6400                          # Ditto chunk_samples (docs: chunk 10 frames = 0.4 s)
    arrivals = sorted(0.2 / rate * i + max(0, rnd.gauss(0, jitter)) for i in range(int(line_s / 0.2)))
    t_take = take_phase if take_phase is not None else rnd.uniform(0, 0.4)
    ai, takes, first_voice = 0, [], None
    while t_take < line_s + 3:
        while ai < len(arrivals) and arrivals[ai] <= t_take:          # /humanaudio between takes
            with m.lock: m.voice_arrived(arrivals[ai], piece); m.pending.append([np.full(piece, 0.1, np.float32), arrivals[ai]])
            ai += 1
        a, _ = m.pending_take(n, now=t_take)
        if a is not None:
            voiced = int((a != 0).sum()); takes.append((round(t_take, 2), voiced))
            if first_voice is None: first_voice = t_take
        t_take += 0.4
    voiced_takes = [v for _, v in takes]
    mid = voiced_takes[:-1]                                   # every take but the last one of the line should be full
    holes = sum(1 for v in mid if v < n)
    return {"holes_mid_line": holes, "holes_counter": m.S["voice_holes"], "first_voice_s": round(first_voice, 2), "takes": len(takes)}

fail = 0
res = {}
for jit, rate in ((0.06, 1.0), (0.15, 1.0), (0.06, 0.9)):
    for prebuf in (0, 400):
        rows = [run(prebuf, s_, jitter=jit, rate=rate) for s_ in range(40)]
        tot = sum(r["holes_mid_line"] for r in rows); cnt = sum(r["holes_counter"] for r in rows); lat = sum(r["first_voice_s"] for r in rows) / 40
        res[(jit, rate, prebuf)] = (tot / 40, lat)
        print(f"arrival jitter {jit:.2f} s, speed x{rate}: FACE_VOICE_PREBUF_MS={prebuf:3d} -> {tot/40:.2f} mid-line holes per 8 s line (counter {cnt/40:.2f}), first voice {lat:.2f} s")
        if cnt != tot: print("FAIL: S['voice_holes'] does not count the holes"); fail += 1
ok = lambda c, m: print(("PASS " if c else "FAIL ") + m) or (0 if c else 1)
fail += ok(res[(0.15, 1.0, 400)][0] < 0.1 * max(0.01, res[(0.15, 1.0, 0)][0]) or res[(0.15, 1.0, 400)][0] < 0.05, "jittery real-time voice: the cushion removes the holes")
fail += ok(res[(0.06, 1.0, 400)][0] <= res[(0.06, 1.0, 0)][0], "never more holes than today")
fail += ok(res[(0.06, 1.0, 400)][1] - res[(0.06, 1.0, 0)][1] < 0.7, "start latency cost < 0.7 s")
print("NOTE: a voice that ARRIVES slower than real time (x0.9 row) cannot be made whole by any cushion this size; the pod's S['voice_lines'] measures the real arrival speed.")
print("ALL PASS" if not fail else f"{fail} FAILED"); sys.exit(1 if fail else 0)
