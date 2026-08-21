#!/usr/bin/env python3
"""Judge a game-session transcript against the certified voice laws.
Input: JSONL, one object per spoken Nova line: {"t": <seconds>, "text": "..."}
       plus optional {"round_at": [..]} schedule file for station timing.
Usage: audit_transcript.py session.jsonl [schedule.json]
Exit 0 = PASS, 1 = FAIL. Prints every violation."""
import json, re, sys

GATE_S = 7.0          # speak-gate law
TOL_S  = 0.75         # timing tolerance for station lines
MAXW   = 12           # words per line ceiling (laws say 5-10; 12 = hard fail line)
NON_EN = re.compile(r"[áéíóúñ¿¡àèìòùâêîôûäëïöüßçãõ]|(\b(hola|vamos|bien|muy|ahora|sí|gracias)\b)", re.I)
BANNED = re.compile(r"\b(wrong|fail|bad|oops|incorrect)\b|\bhold still\b|\bstatue\b", re.I)

def main():
    lines = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    sched = json.load(open(sys.argv[2]))["round_at"] if len(sys.argv) > 2 else []
    fails = []
    prev_t = None
    for ln in lines:
        t, tx = float(ln["t"]), ln["text"].strip()
        if prev_t is not None and (t - prev_t) < GATE_S - 0.25:
            fails.append(f"GATE: line at {t:.1f}s only {t-prev_t:.1f}s after previous: {tx[:50]!r}")
        prev_t = t
        if len(tx.split()) > MAXW:
            fails.append(f"LENGTH: {len(tx.split())} words at {t:.1f}s: {tx[:60]!r}")
        if NON_EN.search(tx):
            fails.append(f"LANGUAGE: non-English at {t:.1f}s: {tx[:60]!r}")
        if BANNED.search(tx):
            fails.append(f"BANNED-WORD at {t:.1f}s: {tx[:60]!r}")
    for at in sched:
        hits = [l for l in lines if abs(float(l["t"]) - at) <= TOL_S]
        if not hits:
            fails.append(f"STATION: no line within ±{TOL_S}s of scheduled {at}s")
    print(f"lines={len(lines)} violations={len(fails)}")
    for f in fails: print("FAIL:", f)
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
