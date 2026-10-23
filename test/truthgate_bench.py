#!/usr/bin/env python3
"""v1.0.9 bench — the TRUTH-GATE fourth path + the Hebrew name-beat fragment join.

Like the PRODUCER-SILENT bench, the code under test is SLICED OUT OF pod/rt_lk.py and
executed, so this tests the shipped file and not a copy of it.

Run: python test/truthgate_bench.py
"""
import os, re, sys, time

try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Hebrew in a cp1252 console
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = open(os.path.join(ROOT, "pod", "rt_lk.py"), encoding="utf-8").read()


def slice_between(start, end):
    a = SRC.index(start); b = SRC.index(end, a)
    block = SRC[a:b]
    return "\n".join(l[4:] if l.startswith("    ") else l for l in block.split("\n"))


def line_with(prefix):
    for l in SRC.split("\n"):
        if l.strip().startswith(prefix):
            return l.strip()
    raise AssertionError("not found: " + prefix)


ns = {"_re": re, "time": time}
# the gate's dependencies, taken verbatim from the file
exec(line_with("FACT_WINDOW ="), ns)
exec(line_with("PRAISE_RE ="), ns)
exec(line_with("INVITE_RE ="), ns)
# the block under test: both rulings of 2026-09-20
exec(slice_between("# ═══ TRUTH-GATE, THE FOURTH PATH", "SELFANSWER_RE = "), ns)

blocks = ns["truthgate_blocks"]
join_fragment = ns["join_fragment"]
name_candidate = ns["name_candidate"]

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name)


NO_FACT = 999.0     # no detection fact this session — the state of the 2026-09-20 run
JUST_TALKED = 1.0   # the child spoke one second ago: the exempt window


def main():
    print("\nv1.0.9 bench — truth-gate fourth path + Hebrew name join\n")

    # ── 1. THE LINE THAT STARTED THIS (2026-09-20, zero facts all session) ──────────
    heard = "איזה יופי של הרמה עם הכתף הזאת!"
    b, why = blocks(heard, NO_FACT, JUST_TALKED)
    check("1 the founder's false-praise line is BLOCKED even right after a kid turn", b)
    check("1 and it is blocked as a move-claim", "move-claim" in why)
    check("1 the old gate would have let it through (English-only PRAISE_RE)",
          not ns["PRAISE_RE"].search(heard[:40]))

    # ── 2. THREE NO-LIFT RUNS: zero move-praise survives ────────────────────────────
    runs = [
        ["היי! אני נובה, מורת הריקוד הקסומה שלך! איך קוראים לך?",
         "נעים להכיר, נועם!",
         "בוא ננסה הרמה קטנה של הכתף, מה אתה אומר?",
         "איזה יופי של הרמה עם הכתף הזאת!"],
        ["שלום! איך קוראים לך?",
         "מגניב, האור הקסום נדלק – תן לי לראות כתף קטנה!",
         "יופי, תחזיק רגע ככה.",
         "כל הכבוד, ראיתי את הכתף שלך עולה!"],
        ["Hi! I'm Nova. What's your name?",
         "Can you lift that shoulder for me?",
         "Perfect shoulder lift — you did it!",
         "That freeze was amazing, you nailed it!"],
    ]
    MOVE_PRAISE = ("הרמה עם הכתף", "ראיתי את הכתף", "shoulder lift", "That freeze was amazing")
    leaked = []
    for i, run in enumerate(runs, 1):
        for line in run:
            blocked, _ = blocks(line, NO_FACT, JUST_TALKED)
            if (not blocked) and any(m in line for m in MOVE_PRAISE):
                leaked.append((i, line))
    check("2 three no-lift runs: ZERO move-praise reaches the child", not leaked)
    if leaked:
        for i, l in leaked:
            print("        LEAK run %d: %s" % (i, l))

    # ── 3. What must STILL be sayable (the gate may not eat the game) ───────────────
    keep = [
        ("בוא ננסה הרמה קטנה של הכתף, מה אתה אומר?", "the Hebrew invite that armed the beat"),
        ("מגניב, האור הקסום נדלק – תן לי לראות כתף קטנה כזאת!", "the light invite"),
        ("כשהמוזיקה נעצרת – קופאים כמו פסל!", "the freeze RULE explanation"),
        ("Can you lift your shoulder for me?", "the English invite"),
        ("נעים להכיר, נועם! איזה שם יפה.", "an honest name-echo (torture-1)"),
        ("איזה כיף לפגוש אותך!", "plain warmth with no move in it"),
    ]
    for line, desc in keep:
        blocked, why = blocks(line, NO_FACT, JUST_TALKED)
        check("3 still sayable — %s" % desc, not blocked)

    # ── 4. With a REAL fact, the same praise is legal ───────────────────────────────
    blocked, _ = blocks(heard, 3.0, JUST_TALKED)
    check("4 a move-claim 3s after a real FACT is allowed", not blocked)
    blocked, _ = blocks(heard, 29.0, JUST_TALKED)
    check("4 still allowed at 29s (inside the 30s window)", not blocked)
    blocked, why = blocks(heard, 31.0, JUST_TALKED)
    check("4 blocked again at 31s (outside the window)", blocked and "move-claim" in why)

    # ── 5. The original gate is untouched: praise into silence still dies ───────────
    blocked, why = blocks("Perfect! You crushed it!", NO_FACT, 30.0)
    check("5 praise into silence still blocked", blocked)
    blocked, _ = blocks("Perfect! Amazing!", NO_FACT, JUST_TALKED)
    check("5 generic praise right after a kid turn is still exempt (no move named)", not blocked)

    # ── 6. THE NAME: "קוראים לי נועם" split in two ─────────────────────────────────
    now = 1000.0
    first, second = "קוראים לי", "נועם"
    joined = join_fragment(first, now, second, now + 0.8)
    check("6 two fragments 0.8s apart are joined", joined == "קוראים לי נועם")
    check("6 the joined answer is a name candidate", name_candidate(joined, True))
    check("6 the joined answer passes the >=2-word rule (it is a real turn)",
          len(re.findall(r"[א-ת][א-ת'\-]*", joined)) >= 2)

    late = join_fragment(first, now, second, now + 3.0)
    check("6 fragments 3.0s apart are NOT joined (only a real stutter counts)", late == second)
    check("6 the exact drop from the live log ('קוראים.') joins with the name",
          join_fragment("קוראים.", now, "רפי", now + 1.0) == "קוראים רפי")

    # ── 7. Name candidates: 1-2 Hebrew tokens, but never a game word ────────────────
    for good in ("נועם", "רפי", "שרה לי", "קוראים לי דני"):
        check("7 name candidate: %s" % good, name_candidate(good, True))
    for bad in ("דוב", "פסל", "כן", "נובה", "כתף", "משחק"):
        check("7 NOT a name: %s" % bad, not name_candidate(bad, True))
    check("7 a long sentence is not a bare name candidate",
          not name_candidate("אני רוצה לשחק במשחק הזה עכשיו", True))
    check("7 English mode never uses the Hebrew name path", not name_candidate("Noam", False))

    print("\n  %d passing · %d failing\n" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


sys.exit(main())
