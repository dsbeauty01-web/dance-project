#!/usr/bin/env python3
"""Nova reply speed, one clock (the pod's), from a run's logs.   usage: nova_speed.py RTLK.LOG [FACE.LOG]
Per reply to the child, ms after t0 = the brain's voice detector (the child's last word is ~450 ms earlier):
  t1 first text · t2 voice request · t3 her first sound made · t5 first voiced chunk rendered · t6 first voiced frame on air
  · t7 the browser played her voice (page her-voice start).  Every number is read from [T] lines; nothing is estimated."""
import re, sys

def ev(path):
    out = []
    for l in open(path, errors="ignore"):
        m = re.search(r"\[T\] (\d{13}) (\S+)(.*)", l)
        if m: out.append((int(m.group(1)), m.group(2), m.group(3).strip()))
    return sorted(out)

def main():
    b = ev(sys.argv[1]); f = ev(sys.argv[2]) if len(sys.argv) > 2 else []
    stops = [t for t, e, _ in b if e == "kid.speech_stopped"]
    print("%-6s %6s %6s %6s %6s %6s %6s  %s" % ("turn", "t1", "t2", "t3", "t5", "t6", "t7", "note"))
    rows = []
    for i, t0 in enumerate(stops):
        end = stops[i + 1] if i + 1 < len(stops) else t0 + 30000
        def first(name, src=b, after=t0, pred=None):
            for t, e, d in src:
                if after < t < end and e == name and (pred is None or pred(d)): return t, d
            return None, ""
        t1, _ = first("oai.first_text"); t2, _ = first("tts.req")
        t3, how = first("tts.first_audio")
        if t3 is None: continue
        t5, _ = first("face.render_voiced", f, t3 - 50); t6, _ = first("face.pub_voiced", f, t3 - 50)
        t7, _ = first("page.her-voice", b, t3, lambda d: d.endswith("start"))
        d = lambda t: ("%6d" % (t - t0)) if t else "     -"
        rows.append(t7 - t0 if t7 else None)
        print("%-6d %s %s %s %s %s %s  %s" % (i + 1, d(t1), d(t2), d(t3), d(t5), d(t6), d(t7), how))
    ok = sorted(r for r in rows if r and r < 8000)
    if ok: print("detector -> browser heard: median %d ms over %d replies (+~450 ms from the child's last word)" % (ok[len(ok) // 2], len(ok)))

if __name__ == "__main__":
    main()
