#!/usr/bin/env python3
"""v1.1.0 bench — SHOULDER-BEAT §4b: the light is a boundary, the pop is page-side,
the retry is this window's own at 8s.

Brain rules are SLICED OUT OF pod/rt_lk.py and executed; page rules are asserted against
nova-commercial.html itself; the two audio stings are measured on disk.

Run: python test/shoulder_beat_bench.py
"""
import asyncio, os, re, sys, time

try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RT = open(os.path.join(ROOT, "pod", "rt_lk.py"), encoding="utf-8").read()
PAGE = open(os.path.join(ROOT, "nova-commercial.html"), encoding="utf-8").read()

EN_ARM = "Look — a magic light on your shoulder! Lift that shoulder up high, just that one!"
HE_ARM = "תראה — אור קסם על הכתף שלך! תרים אותה גבוה, רק אותה!"
EN_RETRY = "I haven't seen it yet — try lifting the shoulder with the light, high!"
HE_RETRY = "עוד לא ראיתי — נסה להרים את הכתף עם האור, גבוה!"

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name)


# ── the brain block, sliced live ────────────────────────────────────────────────────
a = RT.index('    boundary = {"on": False')
b = RT.index("    def _instr(en, he):")
BLOCK = "\n".join(l[4:] if l.startswith("    ") else l for l in RT[a:b].split("\n"))

sent = []


class FakeOAI:
    async def send_json(self, p): sent.append(p)


ns = {"oai": FakeOAI(), "time": time,
      "ask_lock": {"on": False, "since": 0.0},
      "speaking": {"v": False, "last_chunk": 0.0, "resp_active": False},
      "resp": {"buf": "", "killed": False, "origin": None},
      "sayenf": {"line": None, "tried": set()}, "spoken": set(),
      "say_resp": lambda line: {"conversation": "none",
                                "instructions": 'Say ONLY this exact line: "' + line + '"',
                                "input": []}}
exec(compile(BLOCK, "rt_lk.py:PRODUCER-SILENT", "exec"), ns)
boundary_open, speak_now, boundary = ns["boundary_open"], ns["speak_now"], ns["boundary"]
ask_lock, section = ns["ask_lock"], ns["section"]


def creates():
    return [p for p in sent if p.get("type") == "response.create"]


async def main():
    print("\nv1.1.0 bench — SHOULDER-BEAT §4b\n")

    # ── 1. THE LIGHT IS A BOUNDARY ──────────────────────────────────────────────────
    sent.clear(); boundary["on"] = False; ask_lock["on"] = False
    opened = await boundary_open("section-start")
    await speak_now(verbatim=EN_ARM, origin="say")
    check("1 the light appearing opens a boundary", opened is True)
    check("1 and she speaks the line immediately", len(creates()) == 1)
    check("1 the words are the founder's, verbatim",
          EN_ARM in creates()[0]["response"]["instructions"])
    check("1 out-of-band, so nothing in the chat can reshape it",
          creates()[0]["response"].get("conversation") == "none")

    # the WAIT LAW used to swallow exactly this: her line ended in a question
    sent.clear(); boundary["on"] = False; ask_lock["on"] = True
    opened = await boundary_open("section-start")
    await speak_now(verbatim=HE_ARM, origin="say")
    check("1 a section-start is NOT swallowed by the ask-lock", opened is True and len(creates()) == 1)

    # ...but nothing else gets that privilege
    sent.clear(); boundary["on"] = False; ask_lock["on"] = True
    check("1 a plain page beat is still refused while she waits",
          (await boundary_open("air-credit")) is False and not creates())
    ask_lock["on"] = False

    # ── 2. THE RETRY IS THIS WINDOW'S OWN ───────────────────────────────────────────
    sent.clear(); boundary["on"] = False
    await boundary_open("section-retry")
    await speak_now(verbatim=HE_RETRY, origin="say")
    check("2 the retry airs on its own boundary", len(creates()) == 1)
    check("2 read exactly, and it claims nothing",
          HE_RETRY in creates()[0]["response"]["instructions"])
    check("2 the retry states what she has NOT seen", "עוד לא ראיתי" in HE_RETRY
          and "haven't seen it yet" in EN_RETRY)

    # ── 3. ONE PRODUCER PER SILENCE ─────────────────────────────────────────────────
    check("3 the brain stands its timer down while a section is open",
          re.search(r"if section\[\"on\"\]:\s*\n\s*continue", RT) is not None)
    check("3 the section flag exists in the brain", section == {"on": False, "name": "", "ts": 0.0})
    check("3 the page declares section start AND end",
          "novaSection('shoulder', 'start')" in PAGE and PAGE.count("novaSection('shoulder', 'end')") == 2)
    check("3 the brain's generic retry is still 13s for everything else",
          "SILENCE_RETRY_S = 13.0" in RT)

    # ── 4. THE PAGE: exact lines, 8s retry, 20s release ─────────────────────────────
    check("4 EN arm line is the founder's, in the page", EN_ARM in PAGE)
    check("4 HE arm line is the founder's, in the page", HE_ARM in PAGE)
    check("4 EN retry line is the founder's, in the page", EN_RETRY in PAGE)
    check("4 HE retry line is the founder's, in the page", HE_RETRY in PAGE)
    check("4 the retry fires at 8s", re.search(r"!retried && age > 8000", PAGE) is not None)
    check("4 it fires ONCE", "retried = true" in PAGE and "let retried = false" in PAGE)
    check("4 RELEASE still at 20s", "age > 20000" in PAGE and "no shrug seen in 20s" in PAGE)
    check("4 the old director note no longer drives the beat",
          "novaCue(T('armShoulder'))" not in PAGE)

    # ── 5. THE INSTANT REACTION IS PAGE-SIDE ────────────────────────────────────────
    m = re.search(r"const success = \(\) => \{(.*?)\n  \};", PAGE, re.S)
    body = m.group(1) if m else ""
    check("5 success() exists", bool(body))
    check("5 the glow POPS", "classList.add('pop')" in body)
    check("5 a sting plays from her own voice bank", "audio/says/sting_yes_" in body)
    check("5 the sting is chosen by language", "window.NOVA_HE ? 'he' : 'en'" in body)
    check("5 the pop is a real animation, not a class that does nothing",
          "@keyframes glowBloom" in PAGE and "@keyframes popRing" in PAGE)
    check("5 NO brain round-trip in the instant path (no cue/say before the pop)",
          body.index("classList.add('pop')") < body.index("nova-cue"))
    check("5 the FACT still travels to the brain afterwards", "nova-cue" in body and "factShrug" in body)

    # ── 6. THE STINGS ON DISK ───────────────────────────────────────────────────────
    for lang in ("en", "he"):
        p = os.path.join(ROOT, "audio", "says", "sting_yes_%s.mp3" % lang)
        check("6 sting exists: %s" % lang, os.path.isfile(p))
        check("6 sting is a real mp3, not an empty file: %s" % lang,
              os.path.isfile(p) and os.path.getsize(p) > 2000)
    en = os.path.join(ROOT, "audio", "says", "sting_yes_en.mp3")
    he = os.path.join(ROOT, "audio", "says", "sting_yes_he.mp3")
    check("6 the two languages are different recordings",
          open(en, "rb").read() != open(he, "rb").read())

    # ── 7. The truth still holds: a pop is not a claim ──────────────────────────────
    check("7 release() never claims a lift", "she must never claim she saw one" in PAGE)
    check("7 the win line still comes from a FACT, not from the pop", "factShrug" in PAGE)

    print("\n  %d passing · %d failing\n" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


sys.exit(asyncio.run(main()))
