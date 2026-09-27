#!/usr/bin/env python3
"""prune_slow_takes.py — keep only the takes a FAST game can afford.

[CLI-FILL 2026-09-27] The capture tool WARNS about slow lines but still ships them, and the
page picks a take at random — so one 2.3s take in the manifest means the child eventually
waits 2.3s for a command in a game whose whole premise is ~2.8s per command.

Take-to-take variance from the model is large (measured: cmd.armsOut.real 2.23s and 1.20s on
two takes of the SAME text), so the fix is not better wording alone — it is recording extra
takes and keeping the ones inside budget. This deletes over-limit takes and rewrites
manifest.json. A line always keeps at least its fastest take, even if that take is over: a
missing clip is a broken game, a slow clip is only a slow line, and it is reported loudly.

  python3 tools/prune_slow_takes.py audio/nsfast/en
"""
import json, os, sys

LIMIT = {"real": 1.4, "bare": 0.8}          # same budget as capture_realtime_lines.py


def kind_of(line_id):
    return "real" if line_id.endswith(".real") else "bare" if line_id.endswith(".bare") else None


def main(out_dir):
    man = json.load(open(os.path.join(out_dir, "manifest.json"), encoding="utf-8"))
    durs = json.load(open(os.path.join(out_dir, "durations.json"), encoding="utf-8"))
    kept_over, dropped = [], 0

    for lid, files in man.items():
        limit = LIMIT.get(kind_of(lid))
        if not limit or not files:
            continue
        timed = [(f, durs.get(f)) for f in files if durs.get(f) is not None]
        if not timed:
            continue
        good = [f for f, d in timed if d <= limit]
        if good:
            keep = good
        else:                                   # nothing in budget — keep the fastest, say so
            fastest = min(timed, key=lambda x: x[1])
            keep = [fastest[0]]
            kept_over.append("%s %.2fs > %.1fs" % (fastest[0], fastest[1], limit))
        for f, _ in timed:
            if f not in keep:
                p = os.path.join(out_dir, f)
                if os.path.isfile(p):
                    os.remove(p)
                dropped += 1
        man[lid] = keep

    json.dump(man, open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    total = sum(len(v) for v in man.values())
    print("%s: kept %d clips, dropped %d slow takes" % (out_dir, total, dropped))
    for lid, files in man.items():
        if not files:
            print("  MISSING", lid)
    if kept_over:
        print("  STILL OVER BUDGET (no take made it — shorten the wording):")
        for s in kept_over:
            print("   ", s)
    return 1 if any(not v for v in man.values()) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
