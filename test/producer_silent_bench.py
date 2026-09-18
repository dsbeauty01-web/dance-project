#!/usr/bin/env python3
"""PRODUCER-SILENT bench — the boundary machinery, run for real, no pod.

Scope, stated honestly: this exercises the THREE VERBS and the boundary rules as they
exist in pod/rt_lk.py — the block is SLICED OUT OF THE LIVE FILE and executed, not
re-typed here, so a change to the file changes what is tested. What it cannot cover is
the handler wiring (which message calls which verb); that is covered by the verb counts
in tools/laws/law-producersilent.js and by a live session.

Run: python test/producer_silent_bench.py
"""
import asyncio, os, re, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = open(os.path.join(ROOT, "pod", "rt_lk.py"), encoding="utf-8").read()

# ── slice the PRODUCER-SILENT block out of the real brain ────────────────────────────
start = SRC.index('    boundary = {"on": False')
end = SRC.index("    def _instr(en, he):")
BLOCK = SRC[start:end]
assert "async def remember" in BLOCK and "async def speak_now" in BLOCK, "block slice missed"
BLOCK = "\n".join(l[4:] if l.startswith("    ") else l for l in BLOCK.split("\n"))

sent = []            # every payload the block pushes at the socket


class FakeOAI:
    async def send_json(self, payload):
        sent.append(payload)


# the state the block closes over in rt_lk.py
ns = {
    "oai": FakeOAI(),
    "time": time,
    "ask_lock": {"on": False, "since": 0.0},
    "speaking": {"v": False, "last_chunk": 0.0, "resp_active": False},
    "resp": {"buf": "", "killed": False, "origin": None},
    "sayenf": {"line": None, "tried": set()},
    "spoken": set(),
    "say_resp": lambda line: {"conversation": "none",
                              "instructions": 'Say ONLY this exact line: "' + line + '"',
                              "input": [{"type": "message", "role": "user",
                                         "content": [{"type": "input_text", "text": line}]}]},
}
exec(compile(BLOCK, "rt_lk.py:PRODUCER-SILENT", "exec"), ns)

remember, speak_now, boundary_open = ns["remember"], ns["speak_now"], ns["boundary_open"]
speak_pump, cancel_speech, boundary = ns["speak_pump"], ns["cancel_speech"], ns["boundary"]
speak_q, speaking, ask_lock = ns["speak_q"], ns["speaking"], ns["ask_lock"]

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name)


def creates():
    return [p for p in sent if p.get("type") == "response.create"]


def items():
    return [p for p in sent if p.get("type") == "conversation.item.create"]


def reset(idle=True):
    sent.clear(); speak_q.clear()
    boundary["on"] = False; boundary["why"] = ""
    ask_lock["on"] = False
    speaking["resp_active"] = False; speaking["v"] = False
    speaking["last_chunk"] = 0.0 if idle else time.time()
    ns["sayenf"]["line"] = None; ns["spoken"].clear()


async def main():
    print("\nPRODUCER-SILENT bench — boundary machinery sliced from pod/rt_lk.py\n")

    # 1. A note NEVER speaks, and never waits for anything.
    reset()
    await remember("[director] the light is on his right shoulder")
    check("1 a producer note reaches the socket as conversation.item.create", len(items()) == 1)
    check("1 a producer note creates NO response", len(creates()) == 0)
    check("1 the note is a system message with input_text",
          items()[0]["item"]["role"] == "system"
          and items()[0]["item"]["content"][0]["type"] == "input_text")

    # 2. Speech with no boundary is QUEUED, never spoken.
    reset()
    await speak_now(instructions="celebrate the shrug")
    check("2 speech outside a boundary is queued, not spoken", len(creates()) == 0 and len(speak_q) == 1)

    # 3. The kid's turn is HER answer's boundary — a queued producer line may not jump it.
    await boundary_open("kid-turn", pump=False)
    await speak_now(bare=True, origin="kid")
    check("3 the kid-turn boundary produced exactly one response", len(creates()) == 1)
    check("3 that response is the BARE one (her own answer, from context)",
          creates()[0].get("response") in (None, {}) or not creates()[0].get("response"))
    check("3 the earlier producer line is still waiting", len(speak_q) == 1)

    # 4. One send per boundary — the chain is structurally impossible.
    reset()
    await speak_now(instructions="line A"); await speak_now(instructions="line B")
    await boundary_open("hold-end")
    check("4 a hold-end boundary airs exactly ONE of two queued lines", len(creates()) == 1)
    await speak_pump()
    check("4 pumping again does not chain a second line", len(creates()) == 1)
    check("4 the second line is still queued, not dropped", len(speak_q) == 1)

    # 5. The ending is the one section allowed to drain its whole staged group (en-4).
    reset()
    for line in ("You scored 2144!", "Which animal was your favourite?", "See you next time!"):
        await speak_now(verbatim=line, origin="say")
    await boundary_open("phase-end")
    for _ in range(5):
        await speak_pump()
    check("5 phase-end drains the whole ending group", len(creates()) == 3 and not speak_q)

    # 6. WAIT LAW outranks a boundary: she asked, so only the child (or the 13s
    #    re-invite) may open her mouth.
    reset()
    ask_lock["on"] = True
    ok_air = await boundary_open("air-credit")
    check("6 a page boundary is REFUSED while she is waiting for an answer", ok_air is False)
    ok_sil = await boundary_open("13s-silence")
    check("6 the 13s re-invite boundary is still allowed", ok_sil is True)
    ok_kid = await boundary_open("kid-turn")
    check("6 the child answering is always a boundary", ok_kid is True)

    # 7. A busy channel defers — it never lands on top of her own voice.
    reset()
    speaking["resp_active"] = True
    await boundary_open("hold-end")
    await speak_now(instructions="warm move-on")
    check("7 nothing is sent while she is mid-line", len(creates()) == 0 and len(speak_q) == 1)
    check("7 the boundary stays open for it", boundary["on"] is True)
    speaking["resp_active"] = False
    await speak_pump()
    check("7 the line airs the moment she goes idle", len(creates()) == 1 and not speak_q)

    # 8. The engine-drain guard (0.8s) still holds after her audio stops.
    reset(idle=False)
    await boundary_open("hold-end")
    await speak_now(instructions="too soon")
    check("8 a line waits while the engine is still draining", len(creates()) == 0)
    speaking["last_chunk"] = 0.0
    await speak_pump()
    check("8 and airs once the engine is quiet", len(creates()) == 1)

    # 9. The verbatim path: exact line, out-of-band, with the producer's ban appended.
    reset()
    await boundary_open("13s-silence")
    await speak_now(verbatim="I'm right here, no rush at all.", origin="reinvite",
                    extra="You have NOT seen the child do anything: never praise.")
    r = creates()[0]["response"]
    check("9 a verbatim line goes out-of-band (conversation: none)", r.get("conversation") == "none")
    check("9 the exact words are carried", "no rush at all" in r["instructions"])
    check("9 the producer's ban rides with it", "never praise" in r["instructions"])
    check("9 a re-invite is NOT treated as a staged line (no SAY-ENFORCE requeue)",
          ns["sayenf"]["line"] is None)

    # 10. A staged line IS say-enforced, and marked spoken so DE-CAN can see it.
    reset()
    await boundary_open("phase-end")
    await speak_now(verbatim="You scored 2144!", origin="say")
    check("10 a staged exact line arms SAY-ENFORCE", ns["sayenf"]["line"] == "You scored 2144!")
    check("10 and is recorded as spoken (DE-CAN)", "you scored 2144!" in ns["spoken"])

    # 11. A token cap rides with a mid-game line.
    reset()
    await boundary_open("air-credit")
    await speak_now(instructions="one tiny line", cap=40)
    check("11 the mid-game token cap is carried", creates()[0]["response"].get("max_output_tokens") == 40)

    # 12. The only cancel.
    reset()
    await cancel_speech("barge-in (the child started speaking)")
    check("12 cancel_speech emits exactly one response.cancel",
          len(sent) == 1 and sent[0]["type"] == "response.cancel")

    # 13. Nothing in the block ever writes a verb by hand.
    body = BLOCK.split("async def cancel_speech")[0]
    check("13 response.create appears only inside _speak_send",
          len(re.findall(r'"type": "response\.create"', BLOCK)) == 2
          and BLOCK.index('"type": "response.create"') > BLOCK.index("async def _speak_send"))
    check("13 conversation.item.create appears only inside remember",
          len(re.findall(r'"type": "conversation\.item\.create"', body)) == 1)

    # 14. THE SHOULDER BEAT, as the founder designed it — and as it failed on
    #     2026-09-17, replayed end to end. The bug: on the 13s re-invite she said
    #     "יופי, תחזיק רגע ככה" ("Great, hold it like that") to a child who had not
    #     moved, and the page had to correct her.
    reset()
    await remember("The light is on his right shoulder. When you next speak, invite him "
                   "to lift THAT shoulder, once, then wait.")           # page arms the beat
    ask_lock["on"] = True                                                # she asked, now waits
    await remember("[director] he has not answered yet")                 # a cue lands mid-wait
    check("14 notes land while she waits, and NONE of them speaks", len(creates()) == 0 and len(items()) == 2)

    refused = await boundary_open("air-credit")                          # any page beat tries
    check("14 nothing else may open her mouth while she waits", refused is False and len(creates()) == 0)

    await boundary_open("13s-silence")                                   # 13s of silence
    await speak_now(verbatim="I'm right here, no rush at all.", origin="reinvite",
                    extra="You have NOT seen the child do anything: never praise, never say "
                          "you saw or noticed something, never say to hold or keep going.")
    said = creates()[0]["response"]["instructions"]
    check("14 the re-invite is the producer's words, verbatim", "no rush at all" in said)
    check("14 she cannot claim a move she never saw",
          "never praise" in said and creates()[0]["response"].get("conversation") == "none")
    check("14 exactly ONE line came out of the whole silent beat", len(creates()) == 1)

    reset()
    await remember("[FACT — this really happened, you were told, you did not guess] "
                   "The child just did a real move: shoulder_lift.")     # the shrug arrives
    check("14 a real move enters her memory, it does not order a speech",
          len(items()) == 1 and len(creates()) == 0)
    await boundary_open("kid-turn", pump=False)                          # he speaks next
    await speak_now(bare=True, origin="kid")
    check("14 her reply comes at HIS turn, carrying the fact she was told",
          len(creates()) == 1 and not creates()[0].get("response"))

    print("\n  %d passing · %d failing\n" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


sys.exit(asyncio.run(main()))
