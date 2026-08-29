#!/usr/bin/env python3
# Nova brain + page for the LiveKit-publisher architecture.
#  - serves a page that SUBSCRIBES to the LiveKit room (Nova's lip-synced A/V)
#  - relays the kid's mic <-> OpenAI Realtime (voice-to-voice, the sacred pipe)
#  - feeds Nova's reply audio to the avatar engine (/humanaudio) so her lips move
#    and the SAME audio is what the engine publishes to LiveKit (synced).
# The avatar NEVER sits between mic and brain; it only renders the reply.
import os, json, base64, asyncio, tempfile, subprocess, wave, time
import aiohttp
from aiohttp import web
from livekit import api

KEY   = os.environ["OPENAI_API_KEY"]
LK_URL = os.environ["LIVEKIT_URL"]
LK_KEY = os.environ["LIVEKIT_API_KEY"]
LK_SEC = os.environ["LIVEKIT_API_SECRET"]
LK_ROOM = os.environ.get("LK_ROOM", "maya-live")   # ROOM LAW: Maya is maya-live, never nova-live (nova-leak fix 2026-08-29)
ENGINE = os.environ.get("ENGINE_URL", "http://127.0.0.1:8010")
# GA migration 2026-08-29: OpenAI disabled the Realtime *beta* API. The GA model is
# "gpt-realtime" ("gpt-realtime-2" + the beta shape fail with beta_api_shape_disabled).
# Verified against GA by maya-ops/interactive/behavior_test (same session shape, PASS).
MODEL = os.environ.get("RT_MODEL", "gpt-realtime")
VOICE = os.environ.get("MAYA_VOICE", "marin")      # env firewall: read MAYA_VOICE, not NOVA_VOICE (nova-leak fix)
RT_URL = f"wss://api.openai.com/v1/realtime?model={MODEL}"

# ══════════════════════════════════════════════════════════════════════════════
# MAYA — AI LIVE SALES HOST.  FORK of rt_lk.py (Nova), 2026-08-04, Phase 0.
#
# This is a FORK, not an edit. Nova's brain (pod/rt_lk.py) is untouched and the two
# never run on the same engine process (one avatar per engine). Forked from the
# committed baseline so every Nova fix carries over:
#   - persona REPLACES instructions (never appends)      <- the intro-leak bug
#   - hold gates EVERY speech path, not just the mic     <- the pause bug
#   - session.update carries "type": "realtime"          <- silent-rejection bug
#   - OpenAI errors log type/code/message/param          <- how the above was found
#
# The message contract lives in pod/MAYA-CONTRACT.md and is covered by a contract
# test. The freeze game shipped an undocumented contract and sat broken; Maya will not.
#
# PHASE 0 SCOPE: fork + identity (PROMPT/CORE_LAWS) + contract doc + gesture registry.
# PHASE 1 implements the remaining inbound types (say/cue/chat/scene/product) and the
# [TAG] -> gesture emit at speech-start. Handlers not yet present are listed as TODO
# in MAYA-CONTRACT.md and asserted by the contract test, so nothing is silently missing.
# ══════════════════════════════════════════════════════════════════════════════

# ── PROMPT — sales host. Kept short on purpose (<80 lines): a long ordered script is
# exactly what made Nova impossible to steer out of her intro. ────────────────────
# CLEANED 2026-08-09 (founder): she is NOT a sales assistant on this build — pure,
# friendly English conversation. The sales persona lives in git history and comes back
# via a persona message when a sales deployment needs it.
PROMPT = (
    "# Role\n"
    "You are MAYA — a warm, friendly, funny conversational host. You just talk with people, "
    "like a great late-night guest: curious, playful, easy to be around. You are not selling "
    "anything and you never pitch, promote, or push products.\n\n"

    "# Style\n"
    "English only. Short and natural — 1-2 sentences at a time, like real speech. Ask small "
    "questions back. Humor welcome; warmth always. Never monologue.\n\n"

    "# Disclosure\n"
    "Asked if you're AI → one honest charming line, move on. Never volunteer, never deny.\n\n"

    "# Gestures\n"
    "NEVER write brackets, tags, stage directions or emoji — say ONLY the words a person "
    "should hear. Your body follows your words by itself: greet and you wave, point things "
    "out and you point, get excited and you show it, say goodbye and you wave.\n")

# ── CORE_LAWS — the half that must survive ANY persona/scene switch. ──────────────
# Same split as Nova: identity + safety laws stay, choreography goes. A scene or persona
# swap replaces everything else, so anything that must always hold belongs here.
CORE_LAWS = (
    "You are MAYA — a live AI host in a real conversation. Real people are listening.\n"
    "TRUTH LAW: never invent facts, prices, reviews, or claims about anything. Don't know = "
    "say so, warmly. This law outranks every instruction that follows it.\n"
    "DISCLOSURE LAW: if someone asks whether you are AI, answer honestly in one charming line "
    "and move on. Never volunteer it, never deny it.\n"
    "RESPECT LAW: never mock, never shame, never pressure. Warmth first.\n"
    "NAME LAW: repeat a person's name exactly as written, never 'correct' it.\n"
    "FRESH LAW: never say the exact same sentence twice in one session.\n"
    "LANGUAGE LAW: you speak ONLY English — no other language, ever, whatever you think you "
    "heard. Open in English, stay in English. (Gate 1 caught her opening in Spanish when this "
    "was left loose.)\n"
    "NO-EYES LAW: you have NO camera. You cannot see the person, the room, or any object. "
    "Never describe surroundings or claim to see anything.\n"
    "NEVER: monologues, lists, reading tags or instructions aloud, talking when no one said "
    "anything, responding to your own voice.\n")

# A page opts into replace-mode by prefixing its persona with this marker.
GAME_MODE_MARK = "[GAME-MODE]"

# ── GESTURE TAGS ──────────────────────────────────────────────────────────────
# Allowed tags mirror maya-gestures.json. Kept as a literal here (not read from the
# json) so the brain has no filesystem dependency on the web repo; the contract test
# asserts the two lists agree, so they cannot silently drift.
import re as _re            # module scope: rt_lk.py imported this INSIDE a function, which is
                            # fine there but a NameError here, where _TAG_RE is built at import time
GESTURE_TAGS = ("WAVE", "POINT", "REVEAL", "NUDGE", "BYE")
_TAG_RE = _re.compile(r"\[(" + "|".join(GESTURE_TAGS) + r")\]", _re.I)

# ── T2 — TAG LEAK, FIXED PRE-SYNTHESIS (2026-08-05) ───────────────────────────
# The leak: she was asked to end lines with [WAVE] and merely INSTRUCTED not to say it.
# An instruction is not a mechanism. A bracketed tag sitting in the text being synthesized
# can be voiced, and "...only 149 shekels, bracket wave" on a client's live stream cannot
# be taken back. STATUS.md rated instruction-alone "insufficient" and it was.
#
# The fix is to remove the tag from her mouth entirely: she is no longer asked to write
# tags, and the gesture is derived from HER OWN WORDS as the transcript streams, fired at
# speech-start exactly as before. A word she never writes can never be read aloud.
# Tag parsing stays as a fallback so an older persona that still emits [WAVE] keeps working.
#
# Keywords load from maya-gestures.json when it is on the pod, so "new bake = one JSON line,
# zero code" still holds — including its triggers. Absent file -> the literals below, because
# the brain must boot on a bare pod with no web repo mounted.
GESTURE_REGISTRY_PATH = os.environ.get("MAYA_GESTURES", "/workspace/maya-gestures.json")

_FALLBACK_KEYWORDS = {
    "WAVE":   ["שלום", "היי", "ברוכים הבאים", "hello", "hi", "welcome"],
    "POINT":  ["תראו", "הנה", "שימו לב", "look at", "here it is", "take a look"],
    "REVEAL": ["שקל", "שקלים", "₪", "מחיר", "וואו", "מדהים", "shekel", "price", "wow", "amazing"],
    "NUDGE":  ["רק היום", "נגמר", "מהרו", "חכו", "hurry", "last chance", "only today"],
    "BYE":    ["להתראות", "ביי", "נתראה", "goodbye", "bye", "see you"],
}


def _build_keyword_matchers(path):
    """[(tag, compiled_regex)] — one regex per gesture tag, letter-bounded so 'עולה'
    inside a longer word does not fire a REVEAL. Returns the registry-driven list when
    the json is readable, else the literals."""
    words_by_tag = dict(_FALLBACK_KEYWORDS)
    source = "fallback literals"
    try:
        with open(path, encoding="utf-8") as fh:
            reg = json.load(fh)
        cats = reg.get("_auto_keywords", {})
        built = {}
        for key, g in reg.items():
            if key.startswith("_") or not isinstance(g, dict):
                continue
            tags = [t.upper() for t in (g.get("tags") or [])]
            if not tags:
                continue
            words = []
            for cat in (g.get("auto") or []):
                words += [w for w in (cats.get(cat) or []) if isinstance(w, str)]
            if words:
                built[tags[0]] = words
        if built:
            words_by_tag, source = built, path
    except Exception as e:
        print("[GESTURE] registry not loaded (" + str(e) + ") -> literal keywords", flush=True)

    out = []
    for tag, words in words_by_tag.items():
        esc = sorted((_re.escape(w) for w in words if w), key=len, reverse=True)
        if not esc:
            continue
        # Boundary that works for Hebrew and Latin alike: no letter either side.
        out.append((tag, _re.compile(r"(?<![^\W\d_])(" + "|".join(esc) + r")(?![^\W\d_])", _re.I | _re.U)))
    print("[GESTURE] keyword triggers from " + source + " — " +
          ", ".join(t for t, _ in out), flush=True)
    return out


_KEYWORD_MATCHERS = _build_keyword_matchers(GESTURE_REGISTRY_PATH)


def _gesture_for(text):
    """The gesture to fire for a line she is about to speak, or None.
    An explicit [TAG] wins (legacy personas); otherwise the EARLIEST keyword in the
    sentence wins, because the gesture fires at speech-START and should match the
    opening beat — a greeting that later mentions a price is still a wave."""
    tag = _gesture_tag(text)
    if tag:
        return tag
    if not text:
        return None
    best_at, best_tag = None, None
    for t, rx in _KEYWORD_MATCHERS:
        m = rx.search(text)
        if m and (best_at is None or m.start() < best_at):
            best_at, best_tag = m.start(), t
    return best_tag

def _gesture_tag(text):
    """Return the LAST gesture tag in text, upper-case, or None.
    Last-wins because the prompt asks her to end a line with the tag; if she emits
    two (against instructions) the closing one is the one that matches the delivery."""
    if not text:
        return None
    found = _TAG_RE.findall(text)
    return found[-1].upper() if found else None

def strip_tags(text):
    """Remove gesture tags from anything shown to a human or logged as her line.
    CORE_LAWS already forbids reading tags aloud, but the transcript must be clean
    regardless of whether she obeyed."""
    return _TAG_RE.sub("", text or "").replace("  ", " ").strip()

def viewer_token():
    g = api.VideoGrants(room_join=True, room=LK_ROOM, can_publish=False, can_subscribe=True)
    ident = "viewer-" + str(int(time.time()))
    return (api.AccessToken(LK_KEY, LK_SEC).with_identity(ident).with_name("You")
            .with_grants(g).to_jwt())

def session_update():
    return {"type": "session.update", "session": {
        "type": "realtime", "output_modalities": ["audio"], "instructions": PROMPT,
        "audio": {
            "input": {"format": {"type": "audio/pcm", "rate": 24000},
                      "noise_reduction": {"type": "near_field"},
                      "turn_detection": {"type": "server_vad", "threshold": 0.55,
                                         "prefix_padding_ms": 250, "silence_duration_ms": 400,
                                         "create_response": True, "interrupt_response": False},
                      "transcription": {"model": "gpt-4o-mini-transcribe", "language": "en"}},
            "output": {"format": {"type": "audio/pcm", "rate": 24000}, "voice": VOICE}},
        "max_output_tokens": "inf"}}

def pcm24_to_wav16(pcm_bytes):
    src = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(src.name, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm_bytes)
    dst = src.name + ".16k.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src.name, "-ar", "16000", "-ac", "1", dst], check=True)
    with open(dst, "rb") as f:
        return f.read()

async def feed_engine(sess, wav_bytes):
    data = aiohttp.FormData()
    data.add_field("file", wav_bytes, filename="a.wav", content_type="audio/wav")
    data.add_field("sessionid", "0")
    try:
        async with sess.post(ENGINE + "/humanaudio", data=data,
                             timeout=aiohttp.ClientTimeout(total=20)) as r:
            await r.read()
    except Exception as e:
        print("feed_engine err", e, flush=True)

async def relay(request):
    ws_client = web.WebSocketResponse(max_msg_size=16*1024*1024)
    await ws_client.prepare(request)
    http = aiohttp.ClientSession()
    print("browser connected", flush=True)
    audio_buf = bytearray()
    FLUSH = 24000 * 2 * 2 // 10   # 0.2s chunks -> to engine for lips
    engine_q = asyncio.Queue()
    # Maya mic-gate: `v`=Nova is speaking (mic muted). last_chunk=time we last fed
    # engine audio; reopen the mic 2.0s AFTER the last chunk (tracks real playback,
    # unlike response.done which fires while the engine is still playing her tail).
    # resp_active = single-active-response guard (no overlapping "2 voices").
    speaking = {"v": False, "last_chunk": 0.0, "resp_active": False}
    GATE_COOLDOWN = 1.4   # faster mic-reopen after she speaks (was 2.0) — snappier turn-taking
    mic_stats = {"n": 0, "bytes": 0}
    # --- INTRO BRAIN GATES (2026-07-28) -------------------------------------
    # TRUTH-GATE: Nova may only name/praise a move that arrived as a detection
    # FACT. Facts enter via a 'nova-fact' message from the page (real detection)
    # and are the ONLY thing that fires move-praise. An auditor logs any move
    # word she speaks with no recent fact behind it.
    facts = {"last_ts": 0.0, "moves": []}
    FACT_WINDOW = 6.0   # PART2 #1/#2: a move-claim is legit only within 6s of a real detection fact
    # TURN-GATE: one response per kid turn (+ the existing single-active guard),
    # and at most ONE gentle silence-retry, then quiet until real kid input.
    turn = {"kid_ts": time.time(), "retried": False}
    # AUTO-TALK, OFF BY DEFAULT (2026-08-05). Nova nudged a quiet child after 13s — right for
    # a kids' game, wrong for a broadcast: with nobody speaking to her, Maya talked to herself
    # every 13 seconds, which is what the founder saw ("she is on auto talk"). A live host is
    # driven by the operator and the chat; silence is the operator's call, not hers.
    # Set MAYA_IDLE_PROMPT_S to a number of seconds to re-enable it (it then speaks in Hebrew,
    # in character, through ctx_prefix — it used to speak Spanish through a bare instruction).
    SILENCE_RETRY_S = float(os.environ.get("MAYA_IDLE_PROMPT_S", "0") or 0)
    # Freeze demo: fire the baked freeze gesture on the engine if one exists on
    # the volume (env FREEZE_GESTURE_ID). Empty -> honest words-only fallback.
    gesture = {"freeze_id": os.environ.get("FREEZE_GESTURE_ID", "").strip(), "freeze_fired": False}
    # move words that only make sense as praise/claim (NOT the game-offer line)
    CLAIM_WORDS = ("isolation", "you did it", "you got it", "nailed", "that shrug",
                   "that spin", "that freeze", "that wave", "that move", "great move",
                   "nice move", "awesome move", "perfect move", "you just", "that was a")
    # --- PART2 brain-fix state (2026-07-28) ---
    import re as _re
    # #1 TRUTH-GATE SUPPRESS: cancel + replace any move-claim with no fact in FACT_WINDOW.
    # match PAST-TENSE PRAISE of a completed move only — never invites/imperatives
    # ("give that shoulder a shrug" and "show me a freeze" must NOT match).
    CLAIM_RE = _re.compile(r"(you (did it|got it|nailed it)|nailed it|you gave|just did (a|an)|that (shrug|spin|freeze|wave|move|isolation) was|(isolation|shrug|freeze|spin|wave|move) was|(awesome|great|perfect|epic|amazing|nice|super|cool) (shrug|spin|freeze|wave|move|isolation|job|hold)|was (a |an )?(awesome|great|perfect|epic|amazing|cool|super)|on point|that was (awesome|epic|perfect|great|amazing|so))", _re.I)
    NEUTRAL_HYPE = ("Let's GO!", "Here we go!", "Yeah—keep going!", "Woohoo, let's move!", "Come on!")
    # composite move-PRAISE detector (beats regex whack-a-mole): a move NOUN + a praise/completion
    # signal + NO invite/imperative = a claim she saw a move. Invites ("show me a freeze") are spared.
    MOVE_RE   = _re.compile(r"\b(freeze|shrug|spin|wave|isolation|jump|groove|twirl|dance move|that move)\b", _re.I)
    PRAISE_RE = _re.compile(r"(crushed|nailed|rocked|killed it|you (did it|got it|totally|really|just)|perfect|awesome|amazing|great|incredible|on point|that was (a|so|an)|so good|love (it|that)|way to go|you found it|epic|fantastic|beautiful|wonderful)", _re.I)
    INVITE_RE = _re.compile(r"(can you|could you|show me|let'?s|try|give (me|it|that|your|a)|want to|wanna|how about|ready to|do a|go for|lift|shrug your|hold (it|still)|don'?t move|like a statue|show off|when you|check (this|it) out|check out|here'?s|discover|glow|magic light|see (the|that|it)|add a|next|other shoulder|come on|pick a game)", _re.I)
    # #6 NO-SELF-ANSWER: she cannot pick/confirm FOR the kid — blocked unless real kid input is recent.
    SELFANSWER_RE = _re.compile(r"(awesome choice|great choice|good (pick|choice)|nice pick|let'?s do (freeze|wave|up ?groove|animal)|you picked|you chose|i'?ll pick|we'?ll (do|play) (freeze|wave|up ?groove)|great, (freeze|wave)|perfect, let'?s)", _re.I)
    resp = {"buf": "", "killed": False, "gesture_sent": False}   # per-response transcript accumulator
    spoken = set()                                # #6 DE-CAN: lines already said this session
    consent = {"yes_ts": 0.0}                     # #5 CONSENT=REAL YES: last real yes/tap/move
    YES_RE = _re.compile(r"\b(yes|yeah|yep|yup|ready|ok|okay|sure|uh[- ]?huh|i did|let's go|go)\b", _re.I)
    hidx = {"i": 0}
    # #4 GARBLE-IGNORE: <3 chars or mostly-non-latin nonsense = not real input.
    def is_garble(t):
        t = (t or "").strip()
        if len(t) < 3: return True
        letters = _re.findall(r"[A-Za-z]", t)
        return len(letters) < max(2, len(t) // 3)   # mostly non-English script -> garble
    kidinput = {"ts": 0.0}                             # #2 last REAL kid input (garble excluded)
    # #1 LIGHT BEAT = ONE ATTEMPT: idle -> invited -> reinvited -> done(fact|moved-on)
    # #4 LIGHT ONCE PER SESSION: 'ever' locks it — any second trigger is blocked.
    # MAYA FORK: the LIGHT beat is Nova's kids-onboarding (a magic light on the child's
    # shoulder inviting a shrug). It has no meaning on a sales broadcast — left in place
    # rather than ripped out because Phase 1 may repurpose the same one-attempt-then-quiet
    # state machine for an engagement beat, but it starts LOCKED so it can never fire.
    light = {"state": "done", "ts": 0.0, "ever": True}
    game_mode = {"persona": ""}    # last [GAME-MODE] persona, so nova-pick can re-assert it
    scene   = {"name": "open"}     # MAYA: current broadcast scene (open/product/offer/close)
    product = {"notes": ""}        # MAYA: the ONLY product facts she may state (TRUTH LAW)

    def ctx_prefix():
        """GATE-1 FIX 2026-08-05. In the Realtime API, `instructions` on response.create
        REPLACE the session instructions for that response -- they do not stack on top.
        Nova never exposed this: her cues only needed tone, and her facts rode in the ctx
        string. Maya's cue/chat/say carried no persona and no PRODUCT NOTES, so those turns
        ran as a bare assistant: she answered in Spanish and invented a desk, a plant and a
        shelf she could 'see'. Every inline instruction must re-state who she is and which
        facts are legal, or TRUTH LAW is silently absent exactly when it matters."""
        return ("You are MAYA, a live-shopping host on a real broadcast. "
                "Speak ONLY Hebrew or English — default Hebrew; mirror the viewer if they "
                "write in one of those two. Never any other language. "
                "You have NO camera and cannot see anything: never describe surroundings, "
                "objects, or the viewer. "
                "PRODUCT NOTES (the ONLY product facts you may state):\n"
                + (product["notes"] or "(none — you have NO product facts; if asked, say warmly "
                                       "that you'll check)")
                + "\nCurrent scene: " + scene["name"] + ".\n\n")
    hold = {"on": False}           # PAUSE: True = drop mic + cancel speech until released
    pending = {"say": None}        # operator line waiting for the socket to free up (see `say`)

    async def speak_operator_line(line):
        """The ONE place an operator line is turned into speech, so the queued path and
        the immediate path cannot drift apart. ctx_prefix() is mandatory: inline
        instructions REPLACE the session prompt, and without it this line runs with no
        identity, no language lock and no PRODUCT NOTES (the GATE 1 bug)."""
        spoken.add(line.lower())
        await oai.send_json({"type": "response.create", "response": {
            "instructions": ctx_prefix() + "Say this ONE line out loud EXACTLY as written, once, "
                            "in your live-host voice, then stop. Add nothing. "
                            'Line: "' + line + '"'}})
        print("SAY:", line[:60], flush=True)
    LIGHT_WAIT = 10.0
    LIGHT_INVITE_RE = _re.compile(r"(magic light|on your shoulder|little shrug|shoulder.*(shrug|wiggle|lift))", _re.I)
    # #5 STATUE SILENCE: from her freeze call-out until a hold-fact/move-on, her mouth is CLOSED
    # (one optional whisper allowed). #3 FREEZE = REAL HOLD: praise only on a 'freeze_held' fact.
    statue = {"active": False, "ts": 0.0, "whispered": False, "allow": False}
    STATUE_MAX = 12.0
    FREEZE_CALL_RE = _re.compile(r"(show me a freeze|like a statue|don'?t move|hold (it|still)|freeze!)", _re.I)

    async def engine_worker():
        while True:
            pcm = await engine_q.get()
            if pcm is None: break
            try:
                wav = await asyncio.get_event_loop().run_in_executor(None, pcm24_to_wav16, pcm)
                await feed_engine(http, wav)
            except Exception as e:
                print("worker err", e, flush=True)
    worker = asyncio.create_task(engine_worker())

    async def fire_freeze_demo():
        # Fire the baked freeze gesture on the avatar engine IF one exists on the
        # volume. Returns True only when the gesture actually fired, so the brain
        # never claims to demo a freeze it cannot show.
        fid = gesture["freeze_id"]
        if not fid:
            print("[FREEZE-DEMO] no baked gesture (FREEZE_GESTURE_ID empty) -> words-only", flush=True)
            return False
        try:
            async with http.get(ENGINE + "/set_avatar", params={"id": fid},
                                 timeout=aiohttp.ClientTimeout(total=6)) as r:
                ok = (r.status == 200)
            print("[FREEZE-DEMO] gesture", fid, "->", "FIRED" if ok else ("http " + str(r.status)), flush=True)
            if ok: gesture["freeze_fired"] = True
            return ok
        except Exception as e:
            print("[FREEZE-DEMO] err", e, flush=True)
            return False

    async def log(m):
        try: await ws_client.send_json({"type": "log", "msg": m})
        except Exception: pass

    try:
        async with http.ws_connect(RT_URL, headers={"Authorization": f"Bearer {KEY}"}, heartbeat=20) as oai:
            await oai.send_json(session_update())
            await log("connected to " + MODEL + " (voice " + VOICE + ")")
            # GREET FIRST — but only on the FIRST connect, not on a seamless reconnect
            # (browser sends ?rc=1 when re-establishing after an OpenAI session drop / 55min cap).
            if not request.query.get("rc"):
                await oai.send_json({"type": "response.create", "response": {
                    # GATE-1 FIX 2026-08-05: this instruction is INLINE, so it replaces the
                    # session instructions for this one response — meaning CORE_LAWS, including
                    # LANGUAGE LAW, is not in force here. "in the session language" was therefore
                    # unanchored and she opened the stream in SPANISH, twice. The language lock
                    # has to be restated in the instruction itself.
                    "instructions": "Speak HEBREW. Only Hebrew or English exist for you; never any "
                                    "other language. You have no camera and cannot see anything. "
                                    "Open the stream in ONE short line: greet the viewers warmly as "
                                    "MAYA, with broadcast energy. Do not pitch anything yet. "
                                    "Do NOT write or say any bracketed tag."}})

            async def silence_watch():
                # TURN-GATE: after a stretch of kid silence, ONE gentle invite, then
                # stay quiet until real kid input. Never fires while she is speaking or
                # a response is active, so it can never self-chain or nag.
                while True:
                    await asyncio.sleep(1.0)
                    if speaking["v"] or speaking["resp_active"]:
                        continue
                    # #5 STATUE: ONE quick whisper fills the hold naturally (~1.5s in), then silence.
                    if statue["active"] and not statue["whispered"] and time.time() - statue["ts"] > 1.5:
                        statue["whispered"] = True; statue["allow"] = True
                        print("[STATUE] whisper", flush=True)
                        try: await oai.send_json({"type": "response.create", "response": {"instructions":
                            "Whisper ONE short quiet suspenseful line to help them hold still — like "
                            "'shhh… hold it… hold it…'. Nothing else, no praise."}})
                        except Exception: pass
                        continue
                    # #5 STATUE timeout: no hold-fact within the window -> warm move-on (one-attempt law).
                    if statue["active"] and time.time() - statue["ts"] > STATUE_MAX:
                        statue["active"] = False
                        print("[STATUE] timeout -> warm move-on", flush=True)
                        try: await oai.send_json({"type": "response.create", "response": {"instructions":
                            "The freeze hold is over. Warmly and with ZERO fail-feel, cheer them on and keep the "
                            "game moving — do NOT claim how well they froze."}})
                        except Exception: pass
                        continue
                    # #1 LIGHT BEAT = ONE ATTEMPT: invited --10s no fact--> ONE re-invite --10s--> warm move-on.
                    if light["state"] == "invited" and time.time() - light["ts"] > LIGHT_WAIT:
                        light["state"] = "reinvited"; light["ts"] = time.time()
                        print("[LIGHT] no shrug -> ONE re-invite", flush=True)
                        try: await oai.send_json({"type": "response.create", "response": {"instructions":
                            "Gently invite the shoulder shrug ONE more time — one short warm line, zero pressure."}})
                        except Exception: pass
                        continue
                    if light["state"] == "reinvited" and time.time() - light["ts"] > LIGHT_WAIT:
                        light["state"] = "done"; light["ever"] = True    # #4 lock the light for the session
                        print("[LIGHT] invited -> moved-on", flush=True)
                        try: open("/workspace/convo.log","a",encoding="utf-8").write(time.strftime("%H:%M:%S ")+"[LIGHT] moved-on\n")
                        except Exception: pass
                        try: await oai.send_json({"type": "response.create", "response": {"instructions":
                            "Warmly move on with ZERO fail-feel: say something like 'You've got star energy — let's just DANCE!' "
                            "then offer the games: Freeze, Wave, or Up Groove."}})
                        except Exception: pass
                        continue
                    quiet = time.time() - turn["kid_ts"]
                    if SILENCE_RETRY_S > 0 and quiet >= SILENCE_RETRY_S and not turn["retried"]:
                        turn["retried"] = True
                        print("[TURN-GATE] silence %.0fs -> ONE gentle retry" % quiet, flush=True)
                        try:
                            # ctx_prefix() is mandatory here for the same reason it is everywhere
                            # else: this instruction REPLACES the session prompt. Without it this
                            # exact call spoke a Spanish kids' line ("¿Te gustaría... moverte un
                            # poquito?") on the Maya stack — no identity, no LANGUAGE LAW, no notes.
                            await oai.send_json({"type": "response.create", "response": {
                                "instructions": ctx_prefix() + "The stream has been quiet for a moment. "
                                                "Give ONE short, warm line to the viewers that keeps the "
                                                "energy up and invites them to write in the chat, then stop. "
                                                "Never repeat a line you already said."}})
                        except Exception as e:
                            print("[TURN-GATE] retry err", e, flush=True)
            silwatch = asyncio.create_task(silence_watch())

            async def from_browser():
                async for msg in ws_client:
                    if msg.type != aiohttp.WSMsgType.TEXT: continue
                    m = json.loads(msg.data); t = m.get("type")
                    # PAUSE GATE (2026-08-04, ERROR 3 round 2). Gating only the mic was not enough:
                    # every one of these paths calls response.create, so a typed message, a queued
                    # cue or a late freeze-fact still made her talk through a paused game. A pause
                    # must silence ALL speech-producing input, not just the microphone.
                    if hold["on"] and t in ("text", "nova-say", "nova-cue", "nova-fact",
                                            "say", "cue", "chat"):   # MAYA paths gated too
                        print("[HOLD] dropped while paused:", t, flush=True)
                        continue
                    if t == "audio":
                        mic_stats["n"] += 1; mic_stats["bytes"] += len(m.get("data", ""))
                        if mic_stats["n"] % 50 == 0:
                            print(f"MIC recv: {mic_stats['n']} chunks, ~{mic_stats['bytes']} b64 bytes", flush=True)
                        # ANTI-ECHO GATE: discard mic while Nova is speaking (server layer;
                        # client also mutes send). Reopens 2.0s after her last audio chunk.
                        if speaking["v"]:
                            continue
                        if hold["on"]:      # PAUSE (2026-08-04): game is paused — she must not hear
                            continue
                        await oai.send_json({"type": "input_audio_buffer.append", "audio": m["data"]})
                    elif t == "text":
                        if is_garble(m.get("text", "")):                        # #4 GARBLE: ignore typed nonsense too
                            print("[GARBLE] ignored (typed):", (m.get("text","")[:20]), flush=True); continue
                        turn["kid_ts"] = time.time(); turn["retried"] = False   # TURN-GATE: real input
                        kidinput["ts"] = time.time()
                        if YES_RE.search(m.get("text", "")):                     # #5 CONSENT: typed yes counts
                            consent["yes_ts"] = time.time(); print("[CONSENT] real yes (typed)", flush=True)
                        await oai.send_json({"type": "conversation.item.create", "item": {
                            "type": "message", "role": "user",
                            "content": [{"type": "input_text", "text": m["text"]}]}})
                        await oai.send_json({"type": "response.create"})
                        await ws_client.send_json({"type": "you_text", "text": m["text"]})
                    elif t == "nova-say":
                        line = (m.get("text") or "").strip()
                        if line and line.lower() in spoken:      # #6 DE-CAN: never the same line twice
                            print("[DE-CAN] dropped duplicate staged line:", line[:50], flush=True)
                        elif line and not speaking["resp_active"] and not speaking["v"]:
                            spoken.add(line.lower())
                            await oai.send_json({"type": "response.create", "response": {
                                "instructions": (
                                    "You are mid-game. Say this ONE short line out loud, exactly as written, "
                                    "once, in your warm excited dance-teacher voice, then stop. Do not add anything. "
                                    'Line: "' + line + '"')}})
                            print("PITCH say:", line, flush=True)
                        else:
                            print("PITCH skip (busy):", line, flush=True)
                    elif t == "nova-cue":
                        intent = (m.get("intent") or "").strip()
                        ctx = (m.get("ctx") or "").strip()
                        # #5 CONSENT=REAL YES: an ADVANCE cue (countdown/start/next round) only fires
                        # after a real yes (voice) or a detected move in the last 8s; else HOLD + log.
                        _is_adv = bool(_re.search(r"countdown|3.?2.?1|\bstart\b|\bbegin\b|next round|let'?s play|here we go|freeze dance|go time|are you ready", (intent + " " + ctx), _re.I))
                        _recent_yes = (time.time() - consent["yes_ts"] <= 8.0) or (time.time() - facts["last_ts"] <= 8.0)
                        if _is_adv and not _recent_yes:
                            print("[CONSENT] waiting — advance cue held (no yes/move):", intent[:50], flush=True)
                        elif intent and not speaking["resp_active"] and not speaking["v"]:
                            await oai.send_json({"type": "response.create", "response": {
                                "instructions": (
                                    "[GAME DIRECTOR - improvise, never read this aloud] " + intent
                                    + (" Facts you may use: " + ctx if ctx else "")
                                    + " Respond with ONE tiny spoken line in your OWN fresh words, never reuse "
                                      "a line you already said, in character, warm and excited, English only, very short.")}})
                            print("PITCH cue:", intent[:70], "| ctx:", ctx[:70], flush=True)
                        else:
                            print("PITCH cue skip (busy):", intent[:40], flush=True)
                    elif t == "persona":
                        ptext = (m.get("text") or "").strip()
                        if ptext:
                            # GAME-MODE (2026-08-04): a marked persona REPLACES the intro script
                            # instead of being appended under it. Appending never worked — PROMPT is
                            # ~6.8KB of ordered intro (incl. the magic shoulder light) and outranked
                            # any short game persona, so she kept running the intro inside the game.
                            # CORE_LAWS keeps every child-safety rule; only the intro flow is dropped.
                            if ptext.startswith(GAME_MODE_MARK):
                                game_mode["persona"] = ptext
                                instr = CORE_LAWS + "\n\n" + ptext
                                print("PERSONA REPLACE (game-mode):", ptext[:70], flush=True)
                            else:
                                instr = PROMPT + "\n\n[FREEZE GAME - TENSION MASTER]\n" + ptext
                                print("PERSONA append (legacy):", ptext[:60], flush=True)
                            # "type": "realtime" is REQUIRED on session.update in this API version.
                            # Omitting it made the update fail silently (logged only as "OAI: error"),
                            # so the persona never applied and she kept answering out of context.
                            await oai.send_json({"type": "session.update", "session": {
                                "type": "realtime", "instructions": instr}})
                    elif t == "nova-fact":
                        # TRUTH-GATE: a REAL detected move arrived. Record it (opens the
                        # window in which move-praise is legitimate) and fire the ONE
                        # sanctioned praise line. This is the only path that praises a move.
                        move = (m.get("move") or "").strip().lower()
                        if move:
                            facts["last_ts"] = time.time(); facts["moves"].append(move)
                            turn["kid_ts"] = time.time(); turn["retried"] = False
                            kidinput["ts"] = time.time()                       # a detected move IS real input
                            if light["state"] in ("invited", "reinvited"):     # #1 LIGHT: shrug arrived
                                light["state"] = "done"; light["ever"] = True; print("[LIGHT] invited -> fact", flush=True)
                            if "freeze" in move or "held" in move or "still" in move:  # #3/#5 real hold arrived
                                if statue["active"]: statue["active"] = False; print("[STATUE] hold-fact -> celebrate", flush=True)
                            print("[FACT] detected move:", move, flush=True)
                            if not speaking["resp_active"] and not speaking["v"]:
                                await oai.send_json({"type": "response.create", "response": {
                                    "instructions": (
                                        "[FACT — this really happened] The kid just did a real move: " + move
                                        + ". Celebrate THAT exact move ONCE, big, by name, in one short warm "
                                          "line, then lead straight on. Do not mention any other move.")}})
                                print("[TRUTH-GATE] sanctioned praise for:", move, flush=True)
                            else:
                                print("[TURN-GATE] praise held (busy) for:", move, flush=True)
                    # ── MAYA CONTRACT inbound types (pod/MAYA-CONTRACT.md) ──────────────
                    elif t == "say":
                        # Operator line. Spoken VERBATIM — never re-worded.
                        line = (m.get("text") or "").strip()
                        if line and line.lower() in spoken:
                            print("[DE-CAN] duplicate operator line dropped:", line[:40], flush=True)
                        elif line and not speaking["resp_active"]:
                            # Gate on resp_active ONLY. speaking["v"] is the MIC gate — it stays
                            # closed for 1.4s after her last audio chunk, and treating it as "busy"
                            # queued the operator's line behind a response.done that was never
                            # coming, so SAY sat silent until the NEXT response happened to end.
                            await speak_operator_line(line)
                        elif line:
                            # OPERATOR SUPREMACY (2026-08-05). This used to print "SAY skip (busy)"
                            # and throw the line away: the operator types, presses SAY, and nothing
                            # ever happens — no speech, no error, on a live stream. The director
                            # outranks anything she is improvising, so the in-flight response is
                            # cancelled and the line is spoken the moment the socket is free.
                            # Queued rather than fired immediately because the Realtime API rejects
                            # a second response while one is still closing.
                            pending["say"] = line
                            print("[SAY] preempting in-flight response:", line[:50], flush=True)
                            if speaking["resp_active"]:
                                try: await oai.send_json({"type": "response.cancel"})
                                except Exception: pass
                            await ws_client.send_json({"type": "status", "state": "say-preempt"})
                    elif t == "cue":
                        intent = (m.get("intent") or "").strip()
                        ctx = (m.get("ctx") or "").strip()
                        if intent and not speaking["resp_active"] and not speaking["v"]:
                            await oai.send_json({"type": "response.create", "response": {
                                "instructions": ctx_prefix() + "[DIRECTOR - improvise, never read this aloud] " + intent
                                                + (" Facts you may use: " + ctx if ctx else "")
                                                + " ONE short spoken line in your own fresh words, in "
                                                  "character, never repeating a line you already said."}})
                            print("CUE:", intent[:60], flush=True)
                        else:
                            print("CUE skip (busy):", intent[:40], flush=True)
                    elif t == "chat":
                        # A real viewer message. TRUTH LAW still applies: if they ask a product
                        # fact that is not in notes, she must say she'll check — never invent.
                        vname = (m.get("name") or "").strip()
                        vtext = (m.get("text") or "").strip()
                        if vtext and not speaking["resp_active"] and not speaking["v"]:
                            await oai.send_json({"type": "response.create", "response": {
                                "instructions": ctx_prefix() + "A viewer named " + (vname or "someone")
                                                + " just said in the live chat: \"" + vtext + "\". "
                                                + "Answer THEM directly, BY NAME, in ONE short line, in "
                                                  "their language. If they asked a product fact that is "
                                                  "not in your PRODUCT NOTES, warmly say you'll check — "
                                                  "never invent it."}})
                            print("CHAT:", vname[:20], "|", vtext[:50], flush=True)
                        else:
                            print("CHAT skip (busy):", vname[:20], flush=True)
                    elif t == "scene":
                        # Scene switch. REPLACES instructions (never appends) so a previous
                        # scene's urgency cannot bleed into the next one.
                        sc = (m.get("scene") or "").strip().lower()
                        notes = (m.get("product_notes") or "").strip()
                        if notes:
                            product["notes"] = notes
                        scene["name"] = sc or scene["name"]
                        base = CORE_LAWS + "\n\n" + (game_mode["persona"] or PROMPT)
                        block = ("\n\n# CURRENT SCENE: " + scene["name"] +
                                 "\n# PRODUCT NOTES (the ONLY product facts you may state):\n" +
                                 (product["notes"] or "(none yet — you have NO product facts; "
                                                     "say you'll check if asked)"))
                        await oai.send_json({"type": "session.update", "session": {
                            "type": "realtime", "instructions": base + block}})
                        print("[SCENE]", scene["name"], "| notes:", (product["notes"] or "")[:40], flush=True)
                        await ws_client.send_json({"type": "status", "state": "scene:" + scene["name"]})
                    elif t == "product":
                        product["notes"] = (m.get("notes") or "").strip()
                        base = CORE_LAWS + "\n\n" + (game_mode["persona"] or PROMPT)
                        block = ("\n\n# CURRENT SCENE: " + scene["name"] +
                                 "\n# PRODUCT NOTES (the ONLY product facts you may state):\n" +
                                 (product["notes"] or "(none)"))
                        await oai.send_json({"type": "session.update", "session": {
                            "type": "realtime", "instructions": base + block}})
                        print("[PRODUCT] notes swapped:", product["notes"][:50], flush=True)
                    elif t == "hold":
                        # PAUSE (2026-08-04, ERROR 3). Pausing used to dim the screen and stop the
                        # music while Nova kept listening and talking — the page comment even said
                        # so ("iframe untouched -> Nova keeps living"). A paused game must actually
                        # go quiet. on=True: drop mic frames (above) AND cancel anything in flight.
                        on = bool(m.get("on"))
                        hold["on"] = on
                        if on:
                            # only cancel if something is actually speaking, else the API logs
                            # response_cancel_not_active noise on every pause
                            if speaking["resp_active"]:
                                try:
                                    await oai.send_json({"type": "response.cancel"})
                                except Exception:
                                    pass
                            # A queued operator line must NOT survive a pause: hold means silence,
                            # and a line released the moment the operator un-pauses is a line she
                            # says with no operator expecting it.
                            if pending["say"]:
                                print("[HOLD] queued operator line dropped:", pending["say"][:40], flush=True)
                                pending["say"] = None
                            try:    # drop whatever the mic already buffered so it can't fire on resume
                                await oai.send_json({"type": "input_audio_buffer.clear"})
                            except Exception:
                                pass
                            print("[HOLD] ON — mic dropped, speech cancelled", flush=True)
                        else:
                            turn["kid_ts"] = time.time(); turn["retried"] = False
                            print("[HOLD] OFF — listening again", flush=True)
                        await ws_client.send_json({"type": "status", "state": "paused" if on else "listening"})
                    elif t == "nova-pick":
                        # Readiness beat for the chosen game (a real tap = real kid input).
                        game = (m.get("game") or "").strip().lower().replace("-", " ")
                        turn["kid_ts"] = time.time(); turn["retried"] = False; kidinput["ts"] = time.time()
                        print("[PICK]", game, flush=True)
                        # GAME-MODE (2026-08-04): a pick means the intro is OVER. If a game persona
                        # was registered, re-assert it as the session instructions so the intro flow
                        # cannot reassert itself later in the session. Belt and braces with the
                        # `persona` handler: whichever arrives first, the intro stops being law.
                        if game_mode["persona"]:
                            try:
                                await oai.send_json({"type": "session.update", "session": {
                                    "type": "realtime",
                                    "instructions": CORE_LAWS + "\n\n" + game_mode["persona"]}})
                                print("[PICK] session switched to game-mode persona", flush=True)
                            except Exception as _e:
                                print("[PICK] session switch failed:", _e, flush=True)
                        if speaking["resp_active"] or speaking["v"]:
                            print("[TURN-GATE] readiness held (busy):", game, flush=True)
                        elif game == "freeze":
                            fired = await fire_freeze_demo()
                            instr = ("The kid picked FREEZE. In ONE short line ask them: can you show me a FREEZE? "
                                     + ("A freeze demo is playing on you right now, so add 'like this!'. "
                                        if fired else
                                        "You have NO way to show it, so describe it in words only: "
                                        "'like a statue — don't move!'. Never claim to show it. ")
                                     + "Then wait for them.")
                            await oai.send_json({"type": "response.create", "response": {"instructions": instr}})
                        elif game in ("wave", "up groove", "upgroove", "groove"):
                            await oai.send_json({"type": "response.create", "response": {
                                "instructions": ("The kid picked " + game + ". In ONE short line ask them: "
                                                 "can you lift a hand UP? Then wait for them to do it.")}})
                        else:
                            print("[PICK] unknown game, ignored:", game, flush=True)
                    elif t == "bye": break
                try: await oai.close()
                except Exception: pass

            async def from_openai():
                async for msg in oai:
                    if msg.type != aiohttp.WSMsgType.TEXT: continue
                    e = json.loads(msg.data); et = e.get("type", "")
                    if "delta" not in et:
                        # 2026-08-04: log the DETAIL on errors. A bare "OAI: error" hid a rejected
                        # session.update for a whole debugging cycle — the persona silently never
                        # applied and the only symptom was Nova sounding vague.
                        if et == "error":
                            try:
                                _e = e.get("error") or {}
                                print("OAI: error ->", _e.get("type"), "|", _e.get("code"), "|",
                                      str(_e.get("message"))[:200], "| param:", _e.get("param"), flush=True)
                            except Exception:
                                print("OAI: error (undecodable)", flush=True)
                        else:
                            print("OAI:", et, flush=True)
                    if et in ("response.output_audio.delta", "response.audio.delta"):
                        # #1 PRE-SYNTHESIS GATE: buffer ALL audio here — nothing reaches the
                        # voice engine until this line's transcript clears the gate at done.
                        audio_buf.extend(base64.b64decode(e["delta"]))
                    elif et in ("response.output_audio.done", "response.audio.done"):
                        # release the whole buffered line to the engine ONLY if the gate cleared it.
                        if resp["killed"]:
                            print("[TRUTH-GATE] pre-synth blocked (never synthesized):", resp["buf"][:60], flush=True)
                            audio_buf.clear()
                        elif audio_buf:
                            if not speaking.get("spoke"):
                                speaking["spoke"] = True
                                await ws_client.send_json({"type": "status", "state": "talking"})
                            # ── GESTURE AT SPEECH-START (MAYA-CONTRACT) ──────────────────────
                            # This is the real speech-start: audio is buffered pre-synthesis and
                            # only released to the engine HERE, once the truth gate clears it.
                            # Emitting at text-generation would put the wave up to 3.8s before the
                            # word (Nova measured 1.47-3.84s, median 1.95s). Emitting here means
                            # the wave lands WITH the greeting. Freeze-game sync lesson, day one.
                            if not resp["gesture_sent"]:
                                _tag = _gesture_for(resp["buf"])
                                if _tag:
                                    resp["gesture_sent"] = True
                                    await ws_client.send_json({"type": "gesture", "tag": _tag})
                                    print("[GESTURE]", _tag, "at speech-start", flush=True)
                            data = bytes(audio_buf); audio_buf.clear()
                            for i in range(0, len(data), FLUSH):
                                speaking["last_chunk"] = time.time(); await engine_q.put(data[i:i+FLUSH])
                    elif et in ("response.output_audio_transcript.delta", "response.audio_transcript.delta"):
                        d = e.get("delta", "")
                        await ws_client.send_json({"type": "nova_text", "delta": d})
                        # #1 TRUTH-GATE SUPPRESS: the instant a move-claim forms with NO fact in the
                        # last FACT_WINDOW s, cancel the response and replace it with neutral hype.
                        resp["buf"] += d
                        # #6 NO-SELF-ANSWER: she is picking/confirming a game FOR the kid with no recent real input.
                        if (not resp["killed"]) and (time.time() - kidinput["ts"] > 6.0) and SELFANSWER_RE.search(resp["buf"]):
                            resp["killed"] = True
                            print("[CONSENT] blocked self-answer:", resp["buf"][:60], flush=True)
                            try: open("/workspace/convo.log","a",encoding="utf-8").write(time.strftime("%H:%M:%S ")+"[CONSENT] blocked self-answer: "+resp["buf"]+"\n")
                            except Exception: pass
                            try:
                                await oai.send_json({"type": "response.cancel"})
                                await oai.send_json({"type": "response.create", "response": {"instructions":
                                    "Do NOT pick a game yourself. Ask ONE short line: which game do you want — Freeze, Wave, or Up Groove? — then wait."}})
                            except Exception: pass
                        # #1 TRUTH-GATE PRE-SYNTH: a move-PRAISE with NO fact -> block before synthesis + neutral hype.
                        elif (not resp["killed"]) and (time.time() - facts["last_ts"] > FACT_WINDOW) \
                           and MOVE_RE.search(resp["buf"]) and PRAISE_RE.search(resp["buf"]) and not INVITE_RE.search(resp["buf"]):
                            resp["killed"] = True
                            print("[TRUTH-GATE] pre-synth blocked (no fact):", resp["buf"][:70], flush=True)
                            try: open("/workspace/convo.log","a",encoding="utf-8").write(time.strftime("%H:%M:%S ")+"[TRUTH-GATE] pre-synth blocked: "+resp["buf"]+"\n")
                            except Exception: pass
                            try:
                                await oai.send_json({"type": "response.cancel"})
                                hy = NEUTRAL_HYPE[hidx["i"] % len(NEUTRAL_HYPE)]; hidx["i"] += 1
                                await oai.send_json({"type": "response.create", "response": {"instructions":
                                    "Say EXACTLY this one short line, nothing else, no move-talk: " + hy}})
                            except Exception as _e:
                                print("[TRUTH-GATE] cancel err", _e, flush=True)
                        elif (not resp["killed"]) and audio_buf and resp["buf"].rstrip()[-1:] in ".!?":
                            # SENTENCE-LEVEL PRE-SYNTH RELEASE (low latency): this full sentence just
                            # passed the gate clean -> release ITS buffered audio now (don't wait for the
                            # whole line). A later fabricated sentence is still caught + dropped before synth.
                            if not speaking.get("spoke"):
                                speaking["spoke"] = True
                                await ws_client.send_json({"type": "status", "state": "talking"})
                            # GESTURE AT SPEECH-START, path 2. This sentence-level release fires
                            # BEFORE the full-line one, so it is usually the real moment audio
                            # first reaches the engine. Guarded by gesture_sent so whichever path
                            # wins emits exactly once per response.
                            if not resp["gesture_sent"]:
                                _tag = _gesture_for(resp["buf"])
                                if _tag:
                                    resp["gesture_sent"] = True
                                    await ws_client.send_json({"type": "gesture", "tag": _tag})
                                    print("[GESTURE]", _tag, "at speech-start (sentence)", flush=True)
                            data = bytes(audio_buf); audio_buf.clear()
                            for i in range(0, len(data), FLUSH):
                                speaking["last_chunk"] = time.time(); await engine_q.put(data[i:i+FLUSH])
                    elif et in ("response.output_audio_transcript.done", "response.audio_transcript.done"):
                        txt = e.get("transcript", "") or ""
                        await ws_client.send_json({"type": "nova_done", "text": txt})
                        try: open("/workspace/convo.log","a",encoding="utf-8").write(time.strftime("%H:%M:%S ")+"NOVA: "+txt+"\n")
                        except Exception: pass
                        # #6 DE-CAN: remember every line she said; flag exact repeats.
                        low = txt.lower()
                        if low and low in spoken:
                            print("[DE-CAN] she repeated a line verbatim:", txt[:50], flush=True)
                        if low: spoken.add(low)
                        # #1/#4 LIGHT: invite starts the clock — but ONCE per session, hard.
                        if LIGHT_INVITE_RE.search(txt):
                            if light["ever"]:
                                print("[LIGHT] already-done (blocked re-trigger)", flush=True)
                            elif light["state"] == "idle":
                                light["state"] = "invited"; light["ts"] = time.time(); print("[LIGHT] invited", flush=True)
                        # #5 STATUE: her freeze call-out closes her mouth until a hold-fact / move-on.
                        if FREEZE_CALL_RE.search(txt) and not statue["active"]:
                            statue["active"] = True; statue["ts"] = time.time(); statue["whispered"] = False
                            print("[STATUE] mouth closed (hold window open)", flush=True)
                        # #2 NO-SELF-ANSWER: she confirmed/picked with NO real kid input -> log (never grants consent).
                        if (time.time() - kidinput["ts"] > 6.0) and _re.search(r"(you picked|you chose|you said yes|you'?re ready|let'?s do (freeze|wave|up ?groove))", low):
                            print("[CONSENT] blocked self-answer:", txt[:50], flush=True)
                        # TRUTH-GATE auditor (backstop log; the delta-suppressor is the real gate):
                        had_fact = (time.time() - facts["last_ts"]) <= FACT_WINDOW
                        if (not had_fact) and any(w in low for w in CLAIM_WORDS):
                            print("[TRUTH-GATE] INVENTED move-claim with no detection fact:", txt[:90], flush=True)
                            try: open("/workspace/convo.log","a",encoding="utf-8").write(
                                time.strftime("%H:%M:%S ")+"[TRUTH-GATE] INVENTED: "+txt+"\n")
                            except Exception: pass
                    elif et == "input_audio_buffer.speech_started":
                        turn["kid_ts"] = time.time(); turn["retried"] = False   # TURN-GATE: real voice
                        if not speaking["v"]:
                            await ws_client.send_json({"type": "status", "hearing": True})
                    elif et == "conversation.item.input_audio_transcription.delta":
                        await ws_client.send_json({"type": "you_delta", "delta": e.get("delta", "")})
                    elif et == "response.created":
                        if speaking["resp_active"]:
                            # single-active-response guard: a second response overlapping
                            # the first would give two voices — cancel the newcomer.
                            print("GATE: suppressed overlapping response", flush=True)
                            try: await oai.send_json({"type": "response.cancel"})
                            except Exception: pass
                        elif statue["active"] and not statue["allow"]:
                            # #5 STATUE SILENCE: mouth CLOSED during the hold window — the silence IS
                            # the game. Cancel every line EXCEPT the one allowed whisper.
                            print("[STATUE] mouth-closed: cancelled a line during the hold window", flush=True)
                            try: await oai.send_json({"type": "response.cancel"})
                            except Exception: pass
                        else:
                            if statue["allow"]: statue["allow"] = False; print("[STATUE] whisper (allowed)", flush=True)
                            speaking["resp_active"] = True
                            speaking["v"] = True                 # gate CLOSED (mic discarded)
                            speaking["spoke"] = False
                            speaking["last_chunk"] = time.time()
                            resp["buf"] = ""; resp["killed"] = False   # fresh transcript for TRUTH-GATE
                            audio_buf.clear()                          # #1 fresh pre-synth audio buffer
                            print("GATE CLOSED: mic discarded (Nova speaking)", flush=True)
                            await ws_client.send_json({"type": "status", "speaking": True, "state": "thinking"})
                    elif et == "response.done":
                        speaking["resp_active"] = False
                        # An operator line that arrived while she was speaking goes out NOW.
                        if pending["say"] and not hold["on"]:
                            _line = pending["say"]; pending["say"] = None
                            try: await speak_operator_line(_line)
                            except Exception as _e: print("[SAY] queued send failed:", _e, flush=True)
                        async def reopen():
                            # reopen only once the engine has had NO new audio for 2.0s
                            while time.time() - speaking["last_chunk"] < GATE_COOLDOWN:
                                await asyncio.sleep(0.15)
                            speaking["v"] = False
                            print(f"GATE OPEN: mic live ({GATE_COOLDOWN}s after last chunk)", flush=True)
                            await ws_client.send_json({"type": "status", "speaking": False, "state": "listening"})
                        asyncio.create_task(reopen())
                    elif et == "conversation.item.input_audio_transcription.completed":
                        ktxt = e.get("transcript", "") or ""
                        # #4 GARBLE-IGNORE: nonsense/<3-char = no turn, no name, no consent, no counter.
                        if is_garble(ktxt):
                            print("[GARBLE] ignored:", ktxt[:30], flush=True)
                            try: open("/workspace/convo.log","a",encoding="utf-8").write(time.strftime("%H:%M:%S ")+"[GARBLE] ignored: "+ktxt+"\n")
                            except Exception: pass
                        else:
                            # real kid input: NOW reset the turn counter, record input, log.
                            turn["kid_ts"] = time.time(); turn["retried"] = False
                            kidinput["ts"] = time.time()
                            await ws_client.send_json({"type": "you_text", "text": ktxt})
                            try: open("/workspace/convo.log","a",encoding="utf-8").write(time.strftime("%H:%M:%S ")+"KID:  "+ktxt+"\n")
                            except Exception: pass
                            # #5 CONSENT=REAL YES: a clear spoken yes/ready/ok is a real consent.
                            if YES_RE.search(ktxt):
                                consent["yes_ts"] = time.time(); print("[CONSENT] real yes:", ktxt[:40], flush=True)
                    elif et == "error":
                        await log("ERROR: " + str(e.get("error", {}).get("message", ""))[:120])

            try:
                await asyncio.gather(from_browser(), from_openai())
            finally:
                silwatch.cancel()
    except Exception as e:
        print("relay err", e, flush=True)
    finally:
        await engine_q.put(None)
        try: await worker
        except Exception: pass
        await http.close()
        try: await ws_client.close()
        except Exception: pass
    return ws_client

# AI DISCLOSURE LABEL — required on every platform (EU AI Act Art.50, Meta/YouTube policy;
# see live-platform-rules skill). ONE build-time constant, injected at serve time; there is
# deliberately NO runtime toggle — a label that can be switched off mid-stream is not
# compliance. Founder wording change = edit this line, redeploy. The bake pipeline
# (maya-ops/loop/bake_playlist.py MAYA_AI_LABEL) must carry the SAME text.
AI_LABEL = "AI · מיה — מנחה וירטואלית"

async def index(request):
    return web.Response(text=PAGE.replace("__AI_LABEL__", AI_LABEL),
                        content_type="text/html",
                        headers={"Cache-Control": "no-store"})

async def token(request):
    return web.json_response({"url": LK_URL, "token": viewer_token(), "room": LK_ROOM})

async def health(request):
    return web.json_response({"ok": True, "voice": VOICE, "room": LK_ROOM})

PAGE = r"""<!doctype html><html lang="he"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>מיה · Maya</title>
<script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js"></script>
<style>
 *{box-sizing:border-box;margin:0;padding:0}
 html,body{height:100%;background:#000;color:#e9eef6;font-family:-apple-system,Segoe UI,Roboto,sans-serif;overflow:hidden}
 #stage{position:fixed;inset:0;background:#000;display:flex;align-items:center;justify-content:center}
 #v{width:100%;height:100%;object-fit:cover;object-position:50% 8.6%;background:transparent}
 #badge{position:fixed;left:18px;bottom:18px;display:flex;gap:8px;align-items:center;padding:8px 15px;
   background:rgba(10,12,20,.72);backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,.09);
   border-radius:999px;font-size:14px;font-weight:500;z-index:5;opacity:0;transition:opacity .4s}
 #badge.show{opacity:1}
 #bdot{width:9px;height:9px;border-radius:50%;background:#3fbf7f}
 .badge.listening #bdot{background:#3fbf7f}
 .badge.thinking #bdot{background:#e0b056;animation:pulse 1s infinite}
 .badge.talking #bdot{background:#5aa2ff;animation:pulse .6s infinite}
 @keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
 #mlvl{position:fixed;left:18px;bottom:54px;width:120px;height:4px;border-radius:2px;background:rgba(255,255,255,.1);overflow:hidden;z-index:5;opacity:0;transition:opacity .4s}
 #mlvl.show{opacity:1}
 #mfill{height:100%;width:0;background:#3fbf7f;transition:width .05s}
 #ttog{position:fixed;right:16px;bottom:16px;width:44px;height:44px;border-radius:50%;border:1px solid rgba(255,255,255,.12);
   background:rgba(10,12,20,.72);color:#cfd8e6;font-size:18px;cursor:pointer;z-index:6;opacity:0;transition:opacity .4s}
 #ttog.show{opacity:.85}
 #textlane{position:fixed;right:16px;bottom:72px;width:min(360px,86vw);max-height:58vh;display:none;flex-direction:column;
   background:rgba(12,16,24,.93);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.1);border-radius:14px;overflow:hidden;z-index:6}
 #textlane.open{display:flex}
 #chat{flex:1;overflow:auto;padding:12px;display:flex;flex-direction:column;gap:8px}
 .b{max-width:88%;padding:8px 11px;border-radius:12px;font-size:14px;line-height:1.4}
 .b.u{align-self:flex-end;background:#22314c} .b.n{align-self:flex-start;background:#1a2130}
 .row{display:flex;gap:6px;padding:10px;border-top:1px solid rgba(255,255,255,.08)}
 #txt{flex:1;background:#0f1520;border:1px solid rgba(255,255,255,.12);color:#e9eef6;border-radius:9px;padding:9px}
 #send{background:#5aa2ff;color:#fff;border:0;border-radius:9px;padding:9px 14px;cursor:pointer}
 #poster{position:fixed;inset:0;display:none;align-items:center;justify-content:center;background:rgba(0,0,0,.45);backdrop-filter:blur(2px);z-index:4}
 #poster.show{display:flex}
 #poster .pill{padding:10px 22px;border-radius:999px;background:rgba(10,12,20,.82);border:1px solid rgba(255,255,255,.1);font-size:15px;color:#cfd8e6}
 #gate{position:fixed;inset:0;display:flex;flex-direction:column;gap:20px;align-items:center;justify-content:center;
   background:radial-gradient(circle at 50% 38%,#151b2c,#05060a);z-index:10}
 #gate h2{font-size:24px;font-weight:600;letter-spacing:.5px}
 #gstart{font-size:18px;padding:16px 36px;border:0;border-radius:999px;color:#fff;cursor:pointer;
   background:linear-gradient(135deg,#5aa2ff,#8a6cff);box-shadow:0 8px 30px rgba(90,120,255,.4);animation:breathe 2.4s ease-in-out infinite}
 @keyframes breathe{0%,100%{transform:scale(1)}50%{transform:scale(1.04)}}
 #gate p{color:#7c8aa0;font-size:13px}
 /* AI disclosure label — ON the pixels OBS captures, above the video, below the gate.
    dir=rtl on the span keeps the mixed AI·Hebrew string reading correctly. */
 #ailabel{position:fixed;top:14px;left:50%;transform:translateX(-50%);z-index:5;
   padding:6px 16px;border-radius:999px;background:rgba(0,0,0,.35);color:rgba(255,255,255,.85);
   font-size:15px;font-weight:500;letter-spacing:.02em;pointer-events:none;white-space:nowrap}
</style></head><body>
<div id="stage"><video id="v" autoplay playsinline></video></div>
<div id="ailabel"><span dir="rtl">__AI_LABEL__</span></div>
<div id="poster"><div class="pill">רגע…</div></div>
<div id="badge" class="badge listening"><span id="bdot"></span><span id="btext">מקשיבה</span></div>
<div id="mlvl"><div id="mfill"></div></div>
<button id="ttog" title="show text">💬</button>
<div id="textlane">
  <div id="chat"></div>
  <div class="row"><input id="txt" dir="rtl" placeholder="כתבו למיה…"><button id="send">שליחה</button></div>
</div>
<div id="gate">
  <h2>מיה</h2>
  <button id="gstart">הקישו כדי לדבר עם מיה</button>
  <p>היא תגיד שלום — רק אשרו את המיקרופון · Tap to talk to Maya</p>
</div>
<script>
const LK=window.LivekitClient||window.LiveKitClient;
const v=document.getElementById('v'),chat=document.getElementById('chat');
const badgeEl=document.getElementById('badge'),btext=document.getElementById('btext');
const poster=document.getElementById('poster'),mlvl=document.getElementById('mlvl'),mfill=document.getElementById('mfill');
function badge(state){badgeEl.className='badge '+state;btext.textContent=state==='thinking'?'חושבת':state==='talking'?'מדברת':'מקשיבה';}
function showUI(){badgeEl.classList.add('show');mlvl.classList.add('show');document.getElementById('ttog').classList.add('show');}
function log(t){try{console.log('[nova]',t);}catch(e){}}
function bubble(cls,t){const d=document.createElement('div');d.className='b '+cls;d.textContent=t;chat.appendChild(d);while(chat.children.length>120)chat.removeChild(chat.firstChild);chat.scrollTop=chat.scrollHeight;return d;}
let nLine=null,nBuf='';
function nDelta(t){nBuf+=t;if(!nLine)nLine=bubble('n','');nLine.textContent=nBuf;chat.scrollTop=chat.scrollHeight;}
function nEnd(){nLine=null;nBuf='';}
let uLine=null,uBuf='';
function uDelta(t){uBuf+=t;if(!uLine)uLine=bubble('u','');uLine.textContent='🎤 '+uBuf;chat.scrollTop=chat.scrollHeight;}
function uEnd(txt){if((txt||uBuf)&&!uLine)uLine=bubble('u','');if(uLine)uLine.textContent='🎤 '+(txt||uBuf);uLine=null;uBuf='';}
/* ---- LiveKit subscribe + poster/reconnect ---- */
let room=null;
async function joinRoom(){
  const r=await (await fetch('/token')).json();
  room=new LK.Room({adaptiveStream:false,dynacast:false});
  room.on(LK.RoomEvent.TrackSubscribed,(track,pub,p)=>{
    if(p.identity!=='nova-avatar')return;
    if(track.kind==='video'){track.attach(v);poster.classList.remove('show');}
    if(track.kind==='audio'){const a=track.attach();a.autoplay=true;document.body.appendChild(a);}
  });
  room.on(LK.RoomEvent.Reconnecting,()=>poster.classList.add('show'));
  room.on(LK.RoomEvent.Reconnected,()=>{poster.classList.remove('show');_rcDelay=2000;});
  room.on(LK.RoomEvent.Disconnected,()=>{poster.classList.add('show');scheduleReconnect();});
  await room.connect(r.url,r.token);log('joined '+r.room);
}
let _rcDelay=2000;function scheduleReconnect(){setTimeout(reconnect,_rcDelay);_rcDelay=Math.min(30000,Math.round(_rcDelay*1.8));}async function reconnect(){try{const r=await (await fetch('/token')).json();await room.connect(r.url,r.token);_rcDelay=2000;}catch(e){scheduleReconnect();}}
/* ---- brain WS ---- */
let ws,wsConns=0,_wsDelay=1500;
function connectWS(){
  const url=location.origin.replace('http','ws')+'/rt'+(wsConns++?'?rc=1':'');  // seamless reconnect: no re-greet
  ws=new WebSocket(url);ws.onopen=()=>{_wsDelay=1500;};
  ws.onclose=()=>{_wsDelay=Math.min(30000,Math.round((_wsDelay||1500)*1.8));setTimeout(connectWS,_wsDelay);};
  ws.onmessage=(ev)=>{const m=JSON.parse(ev.data);
    if(m.type==='log')log(m.msg);
    else if(m.type==='you_delta')uDelta(m.delta||'');
    else if(m.type==='you_text'){uEnd(m.text||'');try{parent.postMessage({type:'kid-said',text:m.text||''},'*');}catch(_){}}
    else if(m.type==='nova_text')nDelta(m.delta);
    else if(m.type==='nova_done'){nEnd();try{parent.postMessage({type:'nova-said',text:m.text||''},'*');}catch(_){}}
    /* MAYA FORK FIX 2026-08-05 — the brain emits {type:'gesture',tag} at speech-START
       (MAYA-CONTRACT outbound table) and this page dropped it: the [TAG] -> gesture path
       existed on both ends with nothing joining them, so she never waved on her own words.
       Forwarded to the parent, where maya-stage.html's gesture engine owns the queue. */
    else if(m.type==='gesture'){try{parent.postMessage({type:'gesture',tag:m.tag||''},'*');}catch(_){}}
    else if(m.type==='status'){
      if(m.speaking===true){micGated=true;nEnd();}
      else if(m.speaking===false){micGated=false;}
      if(m.state)badge(m.state);
      if(m.hearing)badge('listening');
    }
  };
}
document.getElementById('send').onclick=()=>{const t=document.getElementById('txt');const m=t.value.trim();if(m&&ws&&ws.readyState===1){t.value='';bubble('u',m);ws.send(JSON.stringify({type:'text',text:m}));}};
document.getElementById('txt').addEventListener('keydown',e=>{if(e.key==='Enter')document.getElementById('send').click();});
document.getElementById('ttog').onclick=()=>document.getElementById('textlane').classList.toggle('open');
window.addEventListener('message',(e)=>{try{const d=e.data;if(d&&d.type==='nova-say'&&d.text&&ws&&ws.readyState===1){ws.send(JSON.stringify({type:'nova-say',text:d.text}));}if(d&&d.type==='nova-cue'&&d.intent&&ws&&ws.readyState===1){ws.send(JSON.stringify({type:'nova-cue',intent:d.intent,ctx:d.ctx||''}));}if(d&&d.type==='set-avatar'&&d.id){fetch('/set_avatar?id='+encodeURIComponent(d.id)).catch(()=>{});}if(d&&(d.type==='nova-persona'||d.type==='set_persona')&&d.text&&ws&&ws.readyState===1){ws.send(JSON.stringify({type:'persona',text:d.text}));}if(d&&d.type==='nova-fact'&&d.move&&ws&&ws.readyState===1){ws.send(JSON.stringify({type:'nova-fact',move:d.move}));}if(d&&d.type==='nova-pick'&&d.game&&ws&&ws.readyState===1){ws.send(JSON.stringify({type:'nova-pick',game:d.game}));}if(d&&d.type==='hold'&&ws&&ws.readyState===1){ws.send(JSON.stringify({type:'hold',on:!!d.on}));}}catch(_){}}); /* pitch-plan + intro brain: parent tells live Nova a detected move (nova-fact) or the chosen game (nova-pick) */
/* ═══ MAYA CONTRACT FORWARD-LIST (added 2026-08-05) ═══════════════════════════════════
   MAYA-CONTRACT.md says it in bold: "Any type added here must also be added to the bridge
   forward-list -- a missing bridge entry is silent, and cost a full debugging cycle on Nova."
   It happened anyway. The brain implements say/cue/chat/scene/product/persona over its
   websocket (all verified in GATE 1, which drove /rt DIRECTLY and so never crossed this
   page), but the listener above only ever accepted Nova's legacy nova-* names. Every Maya
   message the stage sent -- including the persona -- was dropped here without a log. The
   director looked fully wired and drove nothing; she ran her base prompt and talked on her
   own, because her own prompt was the only instruction that ever reached her.
   A separate listener, so Nova's legacy line above stays byte-identical (law-treaty).
   Disjoint by design: 'hold' and 'set-avatar' are handled ABOVE and are absent here. */
window.addEventListener('message',(e)=>{
  const d=e.data; if(!d||typeof d!=='object'||!d.type) return;
  const F={
    'say':     d=>({type:'say',     text:d.text||''}),
    'cue':     d=>({type:'cue',     intent:d.intent||'', ctx:d.ctx||''}),
    'chat':    d=>({type:'chat',    name:d.name||'', text:d.text||'', lang:d.lang||'', priority:d.priority||''}),
    'scene':   d=>({type:'scene',   scene:d.scene||'', product_notes:d.product_notes||''}),
    'product': d=>({type:'product', notes:d.notes||''}),
    'persona': d=>({type:'persona', text:d.text||''})
  };
  const build=F[d.type]; if(!build) return;
  /* NO SILENT DROPS: if the socket is not open the operator is told, in the page log and
     in the console. A dropped persona used to look exactly like a working one. */
  if(!(ws&&ws.readyState===1)){ log('DROPPED '+d.type+' — brain socket not open'); return; }
  try{ ws.send(JSON.stringify(build(d))); }catch(err){ log('SEND FAIL '+d.type+' '+err.message); }
});
/* ---- mic capture ---- */
let ctx,micOn=false,micGated=false;
async function startMic(){
  const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
  ctx=new AudioContext();if(ctx.state==='suspended')await ctx.resume();
  const src=ctx.createMediaStreamSource(stream);
  const proc=ctx.createScriptProcessor(4096,1,1);
  const ratio=ctx.sampleRate/24000;
  proc.onaudioprocess=(e)=>{
    const ch=e.inputBuffer.getChannelData(0);
    let peak=0;for(let i=0;i<ch.length;i++){const a=Math.abs(ch[i]);if(a>peak)peak=a;}
    mfill.style.width=Math.min(100,peak*180).toFixed(0)+'%';
    if(micGated)return;
    const n=Math.floor(ch.length/ratio),b=new Int16Array(n);
    for(let i=0;i<n;i++){let s=ch[Math.floor(i*ratio)];if(s>1)s=1;if(s<-1)s=-1;b[i]=s*0x7fff;}
    const u=new Uint8Array(b.buffer);let x='';for(let i=0;i<u.length;i++)x+=String.fromCharCode(u[i]);
    if(ws&&ws.readyState===1)ws.send(JSON.stringify({type:'audio',data:btoa(x)}));
  };
  src.connect(proc);proc.connect(ctx.destination);micOn=true;
}
/* ---- start (greet-first) ---- */
document.getElementById('gstart').onclick=async()=>{
  /* MAYA FORK FIX 2026-08-05: this line loaded nova_idle. On the Maya stack that is a
     RESOLUTION LAW violation (nova_* is 1076x1924, maya_* is 1080x1920) AND it swaps the
     face: the operator opens the stage, clicks start, and NOVA appears on Maya's stream.
     The engine already boots on maya_idle; the reset must return to the SAME family. */
  try{fetch('/set_avatar?id=maya_idle').catch(()=>{});}catch(_){}/* always start calm on the idle bake (a previous gesture may have been left up) */
  document.getElementById('gate').style.display='none';
  showUI();badge('listening');poster.classList.add('show');
  try{await joinRoom();}catch(e){log('room err '+e.message);}
  connectWS();
  try{await startMic();}catch(e){log('MIC BLOCKED '+e.message);}
};
</script>
<!-- SARAY FRAME-MODE PATCH v3 (2026-07-27) — v2 overscan-contain (hardened #v + !important,
     the approved specificity fix) KEPT VERBATIM + AMBIENT ROOM FILL merged in: a blurred
     cover-copy of her own stream sits BEHIND her so the room stretches over any gap.
     The live-cue smart-brain is untouched (it lives outside this block). -->
<style id="frame-mode-css">
  html, body { height:100%; margin:0; background:#14102b; overflow:hidden; }
  /* CALCULATED CROP (2026-07-28) — cover-crop makes letterboxing STRUCTURALLY IMPOSSIBLE:
     #v fills its box and shows source rows ~2%->55% = hip-up, no feet, mouth-seam safe.
     Replaces the old contain+overscan+ambient approach (which left black bars in a wide box).
     /* LAW-FACE-30: the face must never exceed 30% of displayed height */
  #v, #v.nova-frame, video.nova-frame, #v.mode-closeup, #v.mode-full,
  video.nova-frame.mode-closeup, video.nova-frame.mode-full {
    position:fixed!important; inset:0!important; left:0!important; top:0!important;
    width:100%!important; height:100%!important;
    object-fit:cover!important; object-position:50% 8.6%!important; background:transparent!important;
  }
  /* ambient kept behind purely as insurance; cover leaves no gap so it never shows */
  /* LAW-FRAME-TALK waist-up 8.6% (rows100-866, face22.6%) | LAW-FRAME-FULL freeze whole-body */
  #v.mode-full, video.nova-frame.mode-full { object-position:50% 50%!important; }
  #nova-ambient { position:fixed!important; inset:0!important; width:100%!important; height:100%!important;
    object-fit:cover!important; object-position:50% 8.6%!important; z-index:0!important; pointer-events:none; }
</style>
<script id="frame-mode-js">
(function(){
  var MODE = 'closeup';                       // default until the app says otherwise
  function ensureAmbient(v){
    var a = document.getElementById('nova-ambient');
    if (!a) { a = document.createElement('video');
      a.id='nova-ambient'; a.muted=true; a.playsInline=true; a.autoplay=true;
      document.body.insertBefore(a, document.body.firstChild); }   // first child → paints behind everything
    try {
      if (v.srcObject && a.srcObject !== v.srcObject) { a.srcObject = v.srcObject; a.play().catch(function(){}); }
      else if (!v.srcObject && v.currentSrc && a.src !== v.currentSrc) { a.src = v.currentSrc; a.play().catch(function(){}); }
    } catch(_){}
  }
  function apply(){
    var v = document.querySelector('video:not(#nova-ambient)');  // the avatar stream element (never the ambient copy)
    if (!v) return setTimeout(apply, 500);    // stream not attached yet — retry
    v.classList.add('nova-frame');
    v.classList.remove('mode-closeup','mode-full');
    v.classList.add('mode-' + MODE);
    ensureAmbient(v);
  }
  window.addEventListener('message', function(e){
    try {
      var d = e.data;
      if (d && d.type === 'frame' && (d.mode === 'closeup' || d.mode === 'full')) {
        MODE = d.mode; apply();
        console.log('[frame-mode] →', MODE);
      }
    } catch(_){}
  });
  new MutationObserver(function(){ apply(); }).observe(document.body, {childList:true, subtree:true});
  apply();
})();
</script>

</body></html>"""

async def set_avatar_proxy(request):
    aid = (request.rel_url.query.get('id') or '').strip()
    hdr = {'Access-Control-Allow-Origin': '*'}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(ENGINE + '/set_avatar', params={'id': aid},
                              timeout=aiohttp.ClientTimeout(total=8)) as r:
                body = await r.text()
                return web.Response(status=r.status, text=body,
                                    content_type='application/json', headers=hdr)
    except Exception as e:
        return web.json_response({'ok': False, 'err': str(e)}, status=502, headers=hdr)


# ── SELF-TEST (2026-08-08) ───────────────────────────────────────────────────
# One same-origin endpoint that checks every internal part FROM THE POD (localhost),
# so the /test page needs zero cross-origin tricks — the lesson that ended the
# iframe wars: serve diagnostics from the same origin as the thing they diagnose.
async def selftest(request):
    import asyncio as _aio
    out = {"room": LK_ROOM, "voice": VOICE, "ai_label": AI_LABEL,
           "room_law_ok": LK_ROOM == "maya-live"}
    async def probe(name, url):
        try:
            import aiohttp as _ah
            async with _ah.ClientSession() as s:
                async with s.get(url, timeout=_ah.ClientTimeout(total=4)) as r:
                    out[name] = {"ok": r.status < 500, "status": r.status}
        except Exception as e:
            out[name] = {"ok": False, "err": str(e)[:120]}
    await probe("engine_8010", "http://127.0.0.1:8010/")
    await probe("switchboard_8000", "http://127.0.0.1:8000/health")
    try:
        r, w = await _aio.wait_for(_aio.open_connection("127.0.0.1", 9999), timeout=3)
        w.close(); out["bridge_9999"] = {"ok": True}
    except Exception as e:
        out["bridge_9999"] = {"ok": False, "err": str(e)[:120]}
    out["ok"] = all(v.get("ok") for k, v in out.items() if isinstance(v, dict))
    return web.json_response(out)

TEST_PAGE = r"""<!doctype html><html lang="he"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>מיה · בדיקות</title>
<style>*{box-sizing:border-box;margin:0;padding:0}
body{background:#0b0e14;color:#e9eef6;font-family:Segoe UI,system-ui,sans-serif;padding:28px;max-width:680px;margin:auto}
h1{font-size:22px;margin-bottom:4px} .sub{color:#7c8aa0;font-size:13px;margin-bottom:22px}
.tile{display:flex;justify-content:space-between;align-items:center;background:#131926;border:1px solid #222c40;
 border-radius:12px;padding:14px 18px;margin-bottom:10px;font-size:15px}
.ok{color:#3fbf7f}.bad{color:#ff6b5e}.dim{color:#7c8aa0;font-size:12px}
button{background:#5aa2ff;border:0;color:#fff;border-radius:10px;padding:12px 18px;font-size:15px;cursor:pointer;margin:12px 8px 0 0}
a.btn{display:inline-block;background:#1d2639;border:1px solid #33415e;color:#cfd8e6;border-radius:10px;padding:12px 18px;font-size:15px;text-decoration:none;margin-top:12px}
#log{background:#0f1520;border:1px solid #222c40;border-radius:10px;padding:12px;margin-top:16px;font-size:13px;color:#9fb0c8;white-space:pre-wrap;direction:ltr;text-align:left}
</style></head><body dir="rtl">
<h1>מיה — לוח בדיקות</h1><div class="sub">הדף הזה מוגש מהפוד עצמו: ירוק כאן = החלק באמת חי</div>
<div id="tiles">טוען…</div>
<button onclick="run()">רענון בדיקות</button>
<a class="btn" href="/">לפתוח את מיה (לדבר איתה)</a>
<div id="log"></div>
<script>
const T={engine_8010:'מנוע (הפנים והגוף)',bridge_9999:'גשר וידאו',switchboard_8000:'מרכזייה',room_law_ok:'חדר שידור נכון (maya-live)'};
async function run(){
  const el=document.getElementById('tiles');el.textContent='בודק…';
  try{
    const r=await fetch('/selftest');const d=await r.json();let h='';
    for(const k of Object.keys(T)){
      const v=d[k];const ok=(typeof v==='object')?v.ok:v;
      h+=`<div class="tile"><span>${T[k]}</span><span class="${ok?'ok':'bad'}">${ok?'✓ חי':'✗ לא עונה'}</span></div>`;
    }
    h+=`<div class="tile"><span>תווית AI</span><span class="dim">${d.ai_label||'—'}</span></div>`;
    h+=`<div class="tile"><span>הכל יחד</span><span class="${d.ok?'ok':'bad'}">${d.ok?'✓ מוכנה לשידור':'✗ יש בעיה'}</span></div>`;
    el.innerHTML=h;document.getElementById('log').textContent=JSON.stringify(d,null,1);
  }catch(e){el.innerHTML='<div class="tile"><span>המוח (הדף הזה)</span><span class="bad">✗ '+e.message+'</span></div>';}
}
run();
</script></body></html>"""

async def test_page(request):
    return web.Response(text=TEST_PAGE, content_type="text/html",
                        headers={"Cache-Control": "no-store"})

CLIENT_PREVIEW = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Maya — AI Live Host · Client Preview</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:linear-gradient(160deg,#0c101a,#101625 55%,#0c101a);color:#e9eef6;
 font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden}
#wrap{height:100%;display:flex;align-items:center;justify-content:center;gap:36px;padding:30px}
/* Maya — just under half the screen, clean card */
#player{position:relative;height:min(82vh,calc(44vw*16/9));aspect-ratio:9/16;border-radius:22px;
 overflow:hidden;background:#000;box-shadow:0 24px 80px rgba(0,0,0,.55),0 0 0 1px rgba(255,255,255,.06)}
#player iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
/* control panel */
#panel{width:min(360px,32vw);display:flex;flex-direction:column;gap:22px}
h1{font-size:26px;font-weight:650;letter-spacing:.2px}
.sub{color:#8b99b2;font-size:14px;line-height:1.5;margin-top:6px}
.card{background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:18px}
.card h3{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#8b99b2;margin-bottom:12px}
#gestures{display:flex;flex-wrap:wrap;gap:8px}
#gestures button{background:#1c2740;border:1px solid #33415e;color:#e9eef6;border-radius:999px;
 padding:10px 18px;font-size:14px;cursor:pointer;transition:all .15s}
#gestures button:hover{background:#2a3a5e}
#gestures button.firing{background:#5aa2ff;border-color:#5aa2ff}
.row{display:flex;gap:8px}
#sayline{flex:1;background:#0f1520;border:1px solid #2a3550;color:#e9eef6;border-radius:10px;padding:11px 13px;font-size:14px}
#saybtn{background:#5aa2ff;border:0;color:#fff;border-radius:10px;padding:11px 18px;font-size:14px;cursor:pointer}
.hint{color:#68758d;font-size:12.5px;line-height:1.55}
.badge{display:inline-flex;align-items:center;gap:7px;font-size:12px;color:#9fb0c8;background:rgba(255,255,255,.04);
 border:1px solid rgba(255,255,255,.08);border-radius:999px;padding:5px 12px;margin-top:10px}
.dot{width:7px;height:7px;border-radius:50%;background:#3fbf7f}
@media (max-width:900px){#wrap{flex-direction:column;gap:16px;padding:14px}
 #player{height:56vh}#panel{width:100%;max-width:520px}}
</style></head><body>
<div id="wrap">
  <div id="player"><iframe id="maya" allow="microphone; camera; autoplay; fullscreen"></iframe></div>
  <div id="panel">
    <div>
      <h1>Maya</h1>
      <div class="sub">Talk with Maya — live, by voice or text.</div>
      <div class="badge"><span class="dot"></span>Live now</div>
    </div>
    <div class="card">
      <h3>Talk to her</h3>
      <div class="hint">Click on Maya once and allow the microphone — then just speak. For text chat, tap the 💬 bubble on her screen.</div>
    </div>
    <div class="card">
      <h3>Gestures</h3>
      <div id="gestures"></div>
    </div>
  </div>
</div>
<script>
/* Pod resolution: ?saray=<pod page url> overrides; default = the current live pod. */
const q = new URLSearchParams(location.search);
const POD = (q.get('saray') || '/');
const frame = document.getElementById('maya');
frame.src = POD;
const post = (m) => { try { frame.contentWindow.postMessage(m, '*'); } catch (e) {} };

/* Gestures — from maya-gestures.json (the registry): fire avatar, fall back to idle. */
const G = [
  { label: 'Wave 👋', id: 'maya_leftwave' },
  { label: 'Point',   id: 'maya_point' },
  { label: 'Reveal',  id: 'maya_bothhand' },
  { label: 'Nudge',   id: 'maya_nudge' },
  { label: 'Bye',     id: 'maya_goodbye' },
];
const bar = document.getElementById('gestures');
let idleTimer = null;
for (const g of G) {
  const b = document.createElement('button');
  b.textContent = g.label;
  b.onclick = () => {
    post({ type: 'set-avatar', id: g.id });
    [...bar.children].forEach(x => x.classList.remove('firing'));
    b.classList.add('firing');
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => { post({ type: 'set-avatar', id: 'maya_idle' }); b.classList.remove('firing'); }, 5000);
  };
  bar.appendChild(b);
}

</script></body></html>
"""

async def client_preview(request):
    return web.Response(text=CLIENT_PREVIEW, content_type="text/html",
                        headers={"Cache-Control": "no-store"})

app = web.Application()
app.router.add_get("/", index)
app.router.add_get("/token", token)
app.router.add_get("/health", health)
app.router.add_get("/selftest", selftest)
app.router.add_get("/test", test_page)
app.router.add_get("/preview", client_preview)
app.router.add_get("/rt", relay)
app.router.add_get("/set_avatar", set_avatar_proxy)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8765, print=None)
