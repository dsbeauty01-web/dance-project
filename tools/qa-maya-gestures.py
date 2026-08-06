#!/usr/bin/env python3
"""tools/qa-maya-gestures.py — T2 regression test: the tag leak stays shut.

Run on the pod (it imports the brain):
    MAYA_GESTURES=/workspace/maya-gestures.json python3 tools/qa-maya-gestures.py

Why this file exists: the leak was never a parsing bug. She was ASKED to write [WAVE]
and merely INSTRUCTED not to say it, and on a live stream she said it. The fix removes
the tag from her mouth and derives the gesture from her own words, so the things worth
asserting are: (a) no prompt anywhere still asks for a tag, (b) real Hebrew and English
sales lines fire the RIGHT gesture, (c) ordinary sentences fire nothing, and (d) a word
sitting inside a longer word fires nothing.
"""
import os, sys, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Dummy creds: the module reads them at import time, and nothing here touches a network.
for k, v in (("OPENAI_API_KEY", "test"), ("LIVEKIT_URL", "wss://test"),
             ("LIVEKIT_API_KEY", "test"), ("LIVEKIT_API_SECRET", "test")):
    os.environ.setdefault(k, v)
os.environ.setdefault("MAYA_GESTURES", str(ROOT / "maya-gestures.json"))

spec = importlib.util.spec_from_file_location("maya_rt", ROOT / "pod" / "maya_rt.py")
maya = importlib.util.module_from_spec(spec)
spec.loader.exec_module(maya)

passed = failed = 0


def ok(name, cond, extra=""):
    global passed, failed
    if cond:
        passed += 1
        print("  PASS  " + name)
    else:
        failed += 1
        print("  FAIL  " + name + (" — " + str(extra) if extra else ""))


print("MAYA GESTURE / TAG-LEAK TEST")

# (a) nothing asks her for a tag any more
ok("PROMPT asks for no tags", not any(t in maya.PROMPT for t in ("[WAVE]", "[POINT]", "[REVEAL]", "[NUDGE]", "[BYE]")))
ok("CORE_LAWS asks for no tags", "[WAVE]" not in maya.CORE_LAWS)

# registry actually loaded (not silently running on the fallback literals)
tags_loaded = [t for t, _ in maya._KEYWORD_MATCHERS]
ok("all five gestures have triggers", sorted(tags_loaded) == sorted(list(maya.GESTURE_TAGS)), tags_loaded)

# (b) real lines fire the right gesture
CASES = [
    ("שלום לכולם, ברוכים הבאים ללייב!",                    "WAVE"),
    ("Hi everyone, welcome to the live!",                    "WAVE"),
    ("תראו את הסרום הזה, שימו לב למרקם",                    "POINT"),
    ("Take a look at this serum",                            "POINT"),
    ("המחיר היום רק 149 שקל במקום 249",                     "REVEAL"),
    ("wow, that price is amazing",                           "REVEAL"),
    ("רק היום, המלאי נגמר, תזדרזו",                          "NUDGE"),
    ("hurry, this is your last chance",                      "NUDGE"),
    ("להתראות, נתראה בלייב הבא",                             "BYE"),
    ("bye everyone, see you next time",                      "BYE"),
]
for line, want in CASES:
    got = maya._gesture_for(line)
    ok('"' + line[:32] + '" -> ' + want, got == want, "got " + str(got))

# earliest match wins: a greeting that later names a price is still a wave, because the
# gesture fires at speech-START and must match the opening beat.
ok("earliest keyword wins over a later one",
   maya._gesture_for("שלום לכולם! המחיר היום 149 שקל") == "WAVE",
   maya._gesture_for("שלום לכולם! המחיר היום 149 שקל"))

# (c) an ordinary line gestures not at all — sparse gestures look intentional (03 rule 4)
for quiet in ("אני כאן איתכם היום", "let me tell you about the texture", ""):
    ok('no gesture for "' + quiet[:26] + '"', maya._gesture_for(quiet) is None,
       maya._gesture_for(quiet))

# (d) letter boundaries: a trigger inside a longer word must not fire
ok("'מחירון' does not fire REVEAL", maya._gesture_for("יש לנו מחירון מלא באתר") is None,
   maya._gesture_for("יש לנו מחירון מלא באתר"))
ok("'shipping' does not fire on 'hi'", maya._gesture_for("shipping is included") is None,
   maya._gesture_for("shipping is included"))

# legacy: an old persona that still emits a bracket keeps working, and the transcript is clean
ok("explicit [POINT] still wins", maya._gesture_for("הנה המוצר [POINT]") == "POINT")
ok("strip_tags cleans the transcript", maya.strip_tags("שלום [WAVE]") == "שלום")

print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
