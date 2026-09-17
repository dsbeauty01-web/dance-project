#!/usr/bin/env python3
"""
maya_ot.py — Maya's COMMERCIAL host runtime on OpenTalking. One process = the whole host behavior.

  python maya_ot.py --minutes 20                      # live: FB comments → she answers (voice+face) + text reply
  python maya_ot.py --minutes 20 --planted planted.json   # unattended test: injects comments on a schedule (no FB reply for planted)
  python maya_ot.py --dry --planted planted.json      # no FB at all (mock/CPU QA): speak + metrics only

Needs: ot_live.py session running (state file) · brain_server module importable · ~/.maya/host.env
What it does (host-controller organs):
  ACK <1s        cached one-liner spoken the instant a comment lands ("Refael — one sec.")
  ANSWER         brain_server.answer() (instant layer / catalog / deflection / leads) → spoken sentence-by-sentence
  SPEAK QUEUE    OpenTalking only honors mode=replace → we pace sentences by estimated duration so nothing is cut
  PRESENTER      beats.json fires when chat is quiet (opener / product / interaction / price / re-entry)
  BUSY MODE      >= BUSY_PER_MIN comments → batch same-intent questions into one answer naming up to 3 people
  REACTIONS      first-ever comment → welcome by name · purchase → POINT + link · VIP keyword → priority 0
  GESTURES       best-effort avatar switch per intent via OpenTalking (disabled automatically if the API lacks it)
  METRICS        metrics.jsonl: t_in, t_ack, t_speak, latency per answer; summary at end
  END            ends the FB live (fb_tool), runs stream_report.py, prints summary
"""
import argparse, json, os, queue, re, subprocess, sys, threading, time
import requests

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
for p in (os.path.expanduser("~/.maya/host.env"),):
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1); os.environ.setdefault(k, v.strip().strip('"'))
E = os.environ.get
from maya_host import CFG, classify  # noqa: E402
import ot_live  # noqa: E402
from room_awareness import Room  # noqa: E402
from presence import Presence  # noqa: E402
from cocreate import CoCreate  # noqa: E402
from stage import Stage  # noqa: E402

OT = E("OT_BASE", "http://127.0.0.1:8210").rstrip("/")
G = f"https://graph.facebook.com/{E('FB_API_VERSION', 'v21.0')}"
TOK, PAGE = E("FB_PAGE_TOKEN", ""), E("FB_PAGE_ID", "")
VIDEO_ID = E("FB_VIDEO_ID", "")
WPS = float(E("MAYA_WORDS_PER_SEC", "2.3"))          # generous pacing: a small gap beats a cut-off word
SPEAK_MODE = E("MAYA_SPEAK_MODE", "whole")            # whole = one speak call per answer (flow) · sentences = chunked (faster first word, choppier)
BUSY_PER_MIN = int(E("MAYA_BUSY_PER_MIN", "6"))
FILL_AFTER = int(E("MAYA_FILL_AFTER_SEC", "60"))
REENTRY_MIN = int(E("MAYA_REENTRY_EVERY_MIN", "8"))
VIP = re.compile(r"\b(vip|maya!!|urgent)\b", re.I)
GESTURE_FOR = {"purchase": "POINT", "question": "SHOW", "greeting": "WAVE", "medical": "LISTEN", "other": "LISTEN"}
AVATAR_FOR = {"POINT": E("OT_AVATAR_POINT", ""), "SHOW": E("OT_AVATAR_SHOW", ""), "WAVE": E("OT_AVATAR_WAVE", ""),
              "LISTEN": E("OT_AVATAR_LISTEN", ""), "IDLE": E("OT_AVATAR_IDLE", "")}
DIRECTOR = E("DIRECTOR_URL", "http://127.0.0.1:8796").rstrip("/")
SCENE_FOR_INTENT = {"question": ("PIP", "apply"), "purchase": ("HOST", "hero"), "greeting": ("HOST", "apply"), "medical": ("HOST", "apply")}


def director(path: str, payload: dict):
    """Best-effort on-screen control (chat overlay, timer, product PiP/cutaway). Never blocks the host."""
    try:
        requests.post(DIRECTOR + path, json=payload, timeout=1.5)
    except Exception:
        pass


ACKS_NAMED = ["{n} — one sec.", "{n} — good question, one moment.", "{n} — let me check that."]
ACKS_RETURN = ["Welcome back, {n} — one sec.", "{n}, good to see you again — one moment."]
METRICS = open(os.path.join(HERE, "metrics.jsonl"), "a", encoding="utf-8")


def log(m):
    print(f"[maya_ot {time.strftime('%H:%M:%S')}] {m}", flush=True)


def est_seconds(text: str) -> float:
    return max(0.6, len(text.split()) / WPS + 0.25)


SENT = re.compile(r"(?<=[.!?…])\s+")

# ------------------------------------------------------------------ speak queue
class SpeakQueue:
    """Replace-only engine: send one sentence, wait its estimated duration, send the next. Priority 0 clears the queue."""

    def __init__(self, sid: str, tts: str, dry: bool):
        self.sid, self.tts, self.dry = sid, tts, dry
        self.q: "queue.PriorityQueue" = queue.PriorityQueue()
        self.seq = 0; self.lock = threading.Lock()
        self.busy_until = 0.0
        self.last_spoken_ts = time.time()
        threading.Thread(target=self._worker, daemon=True).start()

    BEAT_KINDS = ("beat", "opener", "reentry", "close")

    def say(self, text: str, prio: int = 5, kind: str = "answer", on_first=None, interrupt: bool = False, clear_beats: bool = False):
        """interrupt=True: first sentence is sent immediately (engine 'replace' cuts whatever is playing).
        clear_beats=True: drop queued presenter beats so a viewer never waits behind the sales script."""
        with self.lock:
            if clear_beats:
                keep = []
                while not self.q.empty():
                    try:
                        it = self.q.get_nowait()
                    except queue.Empty:
                        break
                    if it[3] not in self.BEAT_KINDS:
                        keep.append(it)
                for it in keep:
                    self.q.put(it)
            chunks = [text.strip()] if SPEAK_MODE == "whole" else [x.strip() for x in SENT.split(text.strip()) if x.strip()]
            for i, s in enumerate([c for c in chunks if c]):
                self.seq += 1
                self.q.put((prio, self.seq, s, kind, on_first if i == 0 else None, interrupt and i == 0))

    @property
    def current_kind(self):
        return getattr(self, "_current_kind", "idle")

    def _send(self, s: str):
        if self.dry:
            return 0.0
        return ot_live.speak(self.sid, s, mode="replace", tts=self.tts)

    def _worker(self):
        while True:
            prio, _, s, kind, cb, interrupt = self.q.get()
            wait = self.busy_until - time.time()
            if wait > 0 and not interrupt:
                time.sleep(wait)
            self._current_kind = kind
            t0 = time.time()
            sent, backoff = False, 1.0
            for attempt in range(6):
                try:
                    self._send(s); sent = True; break
                except BaseException as e:  # SystemExit from req(), connection errors, anything
                    log(f"speak failed (try {attempt + 1}): {str(e)[:120]} — retry in {backoff:.0f}s")
                    time.sleep(backoff); backoff = min(15.0, backoff * 2)
            if not sent:
                log(f"speak DROPPED after retries: {s[:60]}"); continue
            if cb:
                cb(t0)
            self.busy_until = t0 + est_seconds(s)
            self.last_spoken_ts = t0
            log(f"SPEAK[{kind} p{prio}] {s[:90]}")
            time.sleep(max(0.0, est_seconds(s) - 0.05))

    def idle_seconds(self) -> float:
        return time.time() - self.last_spoken_ts


# ------------------------------------------------------------------ gestures (best effort)
class Gestures:
    def __init__(self, sid: str, dry: bool):
        self.sid, self.dry, self.enabled, self.current = sid, dry, True, "IDLE"

    def set(self, name: str):
        avatar = AVATAR_FOR.get(name, "")
        if not self.enabled or not avatar or avatar == AVATAR_FOR.get(self.current, ""):
            return
        if self.dry:
            log(f"[GESTURE-DRY] {name} → {avatar}"); self.current = name; return
        for path in (f"/sessions/{self.sid}/avatar", f"/sessions/{self.sid}/switch_avatar"):
            try:
                r = requests.post(OT + path, json={"avatar_id": avatar}, timeout=5)
                if r.status_code < 300:
                    self.current = name; log(f"GESTURE {name} → {avatar}"); return
                if r.status_code == 404:
                    continue
            except Exception as e:
                log(f"gesture error: {e}")
        self.enabled = False
        log("gesture switching not supported by this OpenTalking build — disabled (keep single template)")


# ------------------------------------------------------------------ facebook
class FB:
    def __init__(self, dry: bool):
        self.dry = dry
        self.since = int(time.time()) - 20
        self.seen = set()

    def poll(self):
        if self.dry or not (TOK and VIDEO_ID):
            return []
        r = requests.get(f"{G}/{VIDEO_ID}/comments", params={"fields": "id,from{name,id},message,created_time", "order": "chronological",
                         "filter": "stream", "since": self.since, "limit": 50, "access_token": TOK}, timeout=10).json()
        if "error" in r:
            raise RuntimeError(r["error"].get("message"))
        out = []
        for c in r.get("data", []):
            if c["id"] in self.seen or str((c.get("from") or {}).get("id")) == str(PAGE):
                continue
            self.seen.add(c["id"])
            out.append({"id": c["id"], "name": (c.get("from") or {}).get("name", "friend"), "uid": str((c.get("from") or {}).get("id", "")),
                        "text": c.get("message", ""), "ts": time.time(), "source": "fb"})
        self.since = int(time.time()) - 5
        return out

    def reply(self, text: str):
        if self.dry or not (TOK and VIDEO_ID):
            log(f"[FB-REPLY-DRY] {text[:120]}"); return
        requests.post(f"{G}/{VIDEO_ID}/comments", data={"message": text[:900], "access_token": TOK}, timeout=10)



def startup_report(dry: bool) -> None:
    """Print what she actually IS before a single word is spoken, and stop if she is half-configured.
    Env vars are read at import time — if fb_tool wrote FB_VIDEO_ID to host.env AFTER this process
    started, VIDEO_ID is empty here and BOTH comment polling and text replies go silently dry."""
    ot_env = os.path.join(E("OT_DIR", "/workspace/opentalking"), ".env")
    cfg = {}
    if os.path.exists(ot_env):
        for line in open(ot_env, encoding="utf-8"):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1); cfg[k.strip()] = v.strip().strip('"')
    rows = [
        ("avatar", ot_live.load_state().get("avatar", "(none)")),
        ("tts provider", cfg.get("OPENTALKING_TTS_DEFAULT_PROVIDER", "(unset)")),
        ("voice id", cfg.get("OPENTALKING_TTS_ELEVENLABS_VOICE_ID", "(unset)")),
        ("voice model", cfg.get("OPENTALKING_TTS_ELEVENLABS_MODEL_ID", "(unset)")),
        ("sample rate", cfg.get("OPENTALKING_TTS_SAMPLE_RATE", "(unset)")),
        ("speak mode", SPEAK_MODE),
        ("FB video id", VIDEO_ID or "(EMPTY — no polling, no replies)"),
        ("FB token", "set" if TOK else "(EMPTY)"),
        ("text replies", "ON" if (TOK and VIDEO_ID and not dry) else "OFF"),
        ("catalog", os.path.basename(CFG.catalog_path)),
    ]
    log("startup:")
    for k, v in rows:
        log(f"    {k:<14} {v}")
    if dry:
        return
    if not TOK and not VIDEO_ID:
        log("    (no Facebook credentials at all — local/mock run, replies disabled)")
        return
    hard = []
    # HALF-configured is the dangerous state: a token but no video id means she polls and replies
    # into the void while every dashboard looks healthy. That is the 20-minutes-of-silence bug.
    if TOK and not VIDEO_ID:
        hard.append("FB_PAGE_TOKEN is set but FB_VIDEO_ID is EMPTY — run `fb_tool.py live current`, RE-SOURCE host.env, then start this process")
    if VIDEO_ID and not TOK:
        hard.append("FB_VIDEO_ID is set but FB_PAGE_TOKEN is EMPTY")
    if cfg.get("OPENTALKING_TTS_SAMPLE_RATE") not in (None, "", "24000", "44100", "48000"):
        hard.append(f"sample rate {cfg.get('OPENTALKING_TTS_SAMPLE_RATE')} — 16000 publishes compressed/robotic audio")
    if hard:
        for h in hard:
            log("  BLOCKED: " + h)
        log("  run preflight_voice.py, fix, then start again — do not go live half-configured")
        sys.exit(2)


# ------------------------------------------------------------------ host
class Host:
    def __init__(self, a):
        st = ot_live.load_state()
        self.sid = st.get("sid", "dry-session")
        self.tts = st.get("tts", E("OT_TTS", "openai"))
        self.dry = a.dry
        if not a.dry and not st.get("sid"):
            sys.exit("no OpenTalking session — run ot_live.py up first")
        import brain_server  # loads brain, catalog, memory
        self.brain = brain_server
        self.speak = SpeakQueue(self.sid, self.tts, a.dry)
        self.gest = Gestures(self.sid, a.dry)
        self.fb = FB(a.dry)
        self.beats = json.load(open(os.path.join(HERE, a.beats), encoding="utf-8")) if os.path.exists(os.path.join(HERE, a.beats)) else []
        self.beat_i, self.last_beat, self.last_reentry = 0, time.time(), time.time()
        self.pending: list = []
        self.answers_min: list = []
        self.last_user: dict = {}
        self.seen_users: set = set()
        self.planted = json.load(open(a.planted, encoding="utf-8")) if a.planted else []
        self.room = Room(VIDEO_ID, TOK, dry=a.dry or not (VIDEO_ID and TOK))
        prod = self.brain.cat.product.get("name", "")
        self.presence = Presence(product_name=prod, edge=float(E("MAYA_EDGE", "0.35")))
        others = [p.strip() for p in E("MAYA_POLL_PRODUCTS", "").split(",") if p.strip()]
        self.cocreate = CoCreate(products=([prod] + others) if others else [])
        clips = set()
        cdir = E("CLIPS_DIR", "/workspace/maya-ops/bake/src1080")
        if os.path.isdir(cdir):
            import glob as _glob
            for f in _glob.glob(os.path.join(cdir, "*.mp4")):
                n = os.path.basename(f).lower()
                for key in ("hero", "apply", "examine"):
                    if key in n:
                        clips.add(key)
        self.stage = Stage(product=prod, has_clips=clips)
        log(f"stage clips available: {sorted(clips) or 'NONE (shot changes disabled, spoken answers only)'}")
        self.t_start = time.time()
        self.stats = {"comments": 0, "answered": 0, "acked": 0, "batched": 0, "beats": 0, "lat": []}

    # ---- discipline
    def _allowed(self, name: str) -> bool:
        now = time.time()
        self.answers_min = [t for t in self.answers_min if now - t < 60]
        if len(self.answers_min) >= CFG.max_answers_per_min:
            return False
        if now - self.last_user.get(name, 0) < CFG.per_user_cooldown_sec:
            return False
        return True

    # ---- one comment
    def _prior_topics(self, name: str):
        try:
            rows = self.brain.mem.db.execute("SELECT question FROM answers WHERE user_key LIKE ? ORDER BY ts DESC LIMIT 2",
                                             (f"%{name.split()[0].lower()}%",)).fetchall()
            words = []
            for (q,) in rows:
                for w in ("texture", "price", "shipping", "usage", "ingredients", "returns"):
                    if w in (q or "").lower():
                        words.append(w)
            return words[:1]
        except Exception:
            return []

    def handle(self, c: dict):
        name, text = c["name"], c["text"]
        first = name.split()[0]
        cc = self.cocreate.on_comment(name, text)
        if cc:
            self.gest.set("WAVE" if cc["kind"] in ("shoutout", "vip") else "POINT")
            self.speak.say(cc["say"], prio=cc["priority"], kind=cc["kind"], clear_beats=(cc["kind"] == "vip"),
                           interrupt=(cc["kind"] == "vip"))
            self.stats["cocreate"] = self.stats.get("cocreate", 0) + 1
            if cc["kind"] in ("shoutout", "poll_update"):
                return  # a vote is not a question
        cls = classify(type("T", (), {"text": text})())
        if cls.get("drop"):
            log(f"dropped ({cls['reason']}): {name}: {text[:50]}"); return
        intent = cls["intent"]
        vip = bool(VIP.search(text))
        prio = 0 if (vip or intent == "purchase") else (1 if intent == "medical" else 2)
        if not self._allowed(name) and prio > 0:
            self.pending.append(c); return
        t_in = c["ts"]; rec = {"name": name, "text": text[:80], "intent": intent, "vip": vip, "t_in": t_in, "source": c["source"]}
        # 1) ack ONLY if the answer needs the LLM (instant answers are already <1s — an ack would just interrupt her)
        returning = name in self.seen_users
        self.seen_users.add(name)
        director("/chat", {"name": first, "text": text[:60]})
        needs_llm = intent != "medical" and self.brain.INSTANT.match(text) is None
        speaking_beat = self.speak.current_kind in SpeakQueue.BEAT_KINDS
        if needs_llm:
            ack = (ACKS_RETURN if returning else ACKS_NAMED)[hash(name) % 2].format(n=first)
            self.gest.set("LISTEN")
            self.speak.say(ack, prio=1, kind="ack", on_first=lambda t0: rec.__setitem__("t_ack", t0), interrupt=speaking_beat, clear_beats=True)
            self.stats["acked"] += 1
        # 2) answer
        # GESTURE ON DEMAND: a viewer asking to SEE something gets a spoken yes, then the shot
        # changes while she keeps talking — what a real host does, without moving the avatar.
        cue = self.stage.read(text, can_cut=(self.speak.q.empty() or self.speak.current_kind in SpeakQueue.BEAT_KINDS))
        if cue:
            if cue.get("ack"):
                self.speak.say(cue["ack"], prio=1, kind="stage_ack", clear_beats=True,
                               interrupt=(self.speak.current_kind in SpeakQueue.BEAT_KINDS))
            self.gest.set(cue["gesture"])
            if cue.get("scene") == "BANNER":
                director("/banner", {"on": True})
            elif cue.get("scene"):
                director("/scene", {"scene": cue["scene"], "clip": cue["clip"]})
                threading.Timer(cue["seconds"], lambda: director("/scene", {"scene": "HOST"})).start()
            self.stats["stage"] = self.stats.get("stage", 0) + 1
            log(f"STAGE {cue['kind']} -> {cue.get('scene')}/{cue.get('clip')} {cue.get('seconds')}s")
        say = self.brain.answer(f"{name}: {text}", platform="facebook")
        shaped = self.presence.shape(say, name=first, intent=intent, returning=returning,
                                     prior_topics=self._prior_topics(name))
        say = shaped["say"]; rec["say"] = say; rec["gesture"] = shaped["gesture"]; rec["gaze"] = shaped["gaze"]
        self.gest.set(shaped["gesture"])
        scene, clip = SCENE_FOR_INTENT.get(intent, ("HOST", "apply"))
        if scene != "HOST" and not cue:
            director("/scene", {"scene": scene, "clip": clip}); threading.Timer(12, lambda: director("/scene", {"scene": "HOST"})).start()
        self.speak.say(say, prio=1, kind="answer", on_first=lambda t0: self._spoken(rec, t0), clear_beats=True,
                       interrupt=(self.speak.current_kind in SpeakQueue.BEAT_KINDS))
        # 3) text reply (real comments only)
        if c["source"] == "fb":
            lat_txt = ""
            if "t_ack" in rec:
                lat_txt = f"  ⏱ {rec['t_ack'] - t_in:.1f}s"
            self.fb.reply(f"@{first} — {say}{lat_txt}")
        self.answers_min.append(time.time()); self.last_user[name] = time.time()
        self.stats["comments"] += 1

    def _spoken(self, rec, t0):
        rec["t_speak"] = t0; rec["latency"] = round(t0 - rec["t_in"], 2); rec.setdefault("t_ack", t0)
        self.stats["answered"] += 1; self.stats["lat"].append(rec["latency"])
        METRICS.write(json.dumps(rec, ensure_ascii=False) + "\n"); METRICS.flush()
        director("/chat", {"name": rec["name"].split()[0], "text": rec["text"][:60], "reply": rec.get("say", "")[:70], "latency": rec["latency"]})
        log(f"ANSWER {rec['latency']}s {rec['name']}: {rec['text'][:40]!r}")

    # ---- burst handling: comments that arrive together with the same intent get ONE batched answer
    def handle_burst(self, comments: list):
        if len(comments) < 2:
            for c in comments:
                self.handle(c)
            return
        groups: dict = {}
        for c in comments:
            cls = classify(type("T", (), {"text": c["text"]})())
            if cls.get("drop"):
                log(f"dropped ({cls['reason']}): {c['name']}: {c['text'][:50]}"); continue
            groups.setdefault(cls["intent"], []).append(c)
        for intent, group in groups.items():
            if len(group) >= 2 and intent in ("purchase", "question"):
                names = ", ".join(sorted({g["name"].split()[0] for g in group})[:3])
                say = self.brain.answer(f"{names}: {group[0]['text']}", platform="facebook")
                # a "show me" inside a burst still deserves the shot change — cut once for the group
                cue = self.stage.read(group[0]["text"], can_cut=True)
                if cue and cue.get("scene"):
                    if cue.get("scene") == "BANNER":
                        director("/banner", {"on": True})
                    else:
                        director("/scene", {"scene": cue["scene"], "clip": cue["clip"]})
                        threading.Timer(cue["seconds"], lambda: director("/scene", {"scene": "HOST"})).start()
                    self.stats["stage"] = self.stats.get("stage", 0) + 1
                    log(f"STAGE {cue['kind']} (burst of {len(group)}) -> {cue.get('scene')}/{cue.get('clip')}")
                self.gest.set(cue["gesture"] if cue else GESTURE_FOR.get(intent, "SHOW"))
                # if the burst was a "show me", the spoken yes opens the line instead of "lots of you asking"
                line = f"{cue['ack']} {names} — {say}" if (cue and cue.get("ack")) else f"Lots of you asking — {names}: {say}"
                self.speak.say(line, prio=1, kind="batch", interrupt=True, clear_beats=True)
                self.stats["batched"] += len(group); self.stats["comments"] += len(group)
                for g in group:
                    self.seen_users.add(g["name"]); self.last_user[g["name"]] = time.time()
                    if g["source"] == "fb":
                        self.fb.reply(f"@{g['name'].split()[0]} — {say}")
                self.answers_min.append(time.time())
                log(f"BATCH x{len(group)} [{intent}] {names}")
            else:
                for c in group:
                    self.handle(c)

    # ---- busy mode: batch same-intent pending questions
    def drain_pending(self):
        if not self.pending:
            return
        now = time.time()
        self.pending = [c for c in self.pending if now - c["ts"] < 120]
        by_intent: dict = {}
        for c in self.pending:
            by_intent.setdefault(classify(type("T", (), {"text": c["text"]})()).get("intent", "other"), []).append(c)
        for intent, group in by_intent.items():
            if len(group) >= 2 and intent in ("purchase", "question"):
                names = ", ".join(sorted({g["name"].split()[0] for g in group})[:3])
                say = self.brain.answer(f"{names}: {group[0]['text']}", platform="facebook")
                self.speak.say(f"Lots of you asking — {names}: {say}", prio=2, kind="batch", clear_beats=True)
                self.stats["batched"] += len(group)
                for g in group:
                    if g["source"] == "fb":
                        self.fb.reply(f"@{g['name'].split()[0]} — {say}")
                self.pending = [c for c in self.pending if c not in group]
            elif self._allowed(group[0]["name"]):
                c = group[0]; self.pending.remove(c); self.handle(c)

    # ---- presenter beats when quiet
    def presenter(self):
        now = time.time()
        if not self.beats or self.pending or not self.speak.q.empty():
            return
        if self.speak.idle_seconds() < FILL_AFTER or now - self.last_beat < FILL_AFTER:
            return
        if now - self.last_reentry > REENTRY_MIN * 60:
            self.speak.say("Joined mid-way? Perfect timing — ask me anything in the chat.", prio=6, kind="reentry")
            self.last_reentry = now; self.last_beat = now; return
        b = self.beats[self.beat_i % len(self.beats)]; self.beat_i += 1
        self.gest.set(b.get("gesture", "SHOW"))
        if b.get("scene"):
            director("/scene", {"scene": b["scene"], "clip": b.get("clip", "apply")}); threading.Timer(b.get("scene_sec", 10), lambda: director("/scene", {"scene": "HOST"})).start()
        shaped = self.presence.shape(b["text"], intent="pitch")
        self.gest.set(shaped["gesture"])
        self.speak.say(shaped["say"], prio=6, kind="beat"); self.stats["beats"] += 1; self.last_beat = now

    # ---- planted comments (unattended test)
    def planted_due(self):
        out = []
        el = (time.time() - self.t_start) / 60
        for p in self.planted:
            if not p.get("_done") and el >= p["at_min"]:
                p["_done"] = True
                out.append({"id": f"pl-{p['at_min']}", "name": p["name"], "uid": p["name"], "text": p["text"], "ts": time.time(), "source": "planted"})
        return out

    def run(self, minutes: float):
        startup_report(self.dry)
        log(f"host up sid={self.sid} dry={self.dry} minutes={minutes} beats={len(self.beats)} planted={len(self.planted)}")
        if self.beats:
            self.speak.say(self.beats[0]["text"], prio=3, kind="opener"); self.beat_i = 1
        end = time.time() + minutes * 60
        while time.time() < end:
            try:
                self.handle_burst(self.fb.poll() + self.planted_due())
                self.drain_pending()
                if self.speak.q.empty() and not self.pending:
                    cc = self.cocreate.tick()
                    if cc:
                        self.gest.set("POINT"); self.speak.say(cc["say"], prio=cc["priority"], kind=cc["kind"])
                        self.stats["cocreate"] = self.stats.get("cocreate", 0) + 1
                        director("/chat", {"name": "POLL", "text": cc["say"][:60]})
                if self.speak.q.empty() and not self.pending and self.speak.idle_seconds() > 20:
                    line = self.room.tick()
                    if line:
                        self.gest.set("WAVE"); self.speak.say(line, prio=4, kind="room"); self.stats["room"] = self.stats.get("room", 0) + 1
                self.presenter()
            except Exception as e:
                log(f"loop error: {e}"); time.sleep(3)
            time.sleep(1.5)
        self.finish()

    def finish(self):
        lat = sorted(self.stats["lat"])
        summ = {**{k: v for k, v in self.stats.items() if k != "lat"}, **self.room.summary(), "stage_cues": self.stage.stats(),
                "latency_median_s": lat[len(lat) // 2] if lat else None, "latency_worst_s": lat[-1] if lat else None,
                "minutes": round((time.time() - self.t_start) / 60, 1)}
        log("SUMMARY " + json.dumps(summ))
        json.dump(summ, open(os.path.join(HERE, "last_session_summary.json"), "w"), indent=2)
        if not self.dry:
            self.speak.say("That's it for this round — thank you all. Link below, or type ME.", prio=3, kind="close")
            time.sleep(6)
            if E("FB_LIVE_VIDEO_ID"):
                subprocess.run([sys.executable, os.path.join(HERE, "fb_tool.py"), "live", "end", E("FB_LIVE_VIDEO_ID")], timeout=30)
            subprocess.run([sys.executable, os.path.join(HERE, "stream_report.py"), "--video-id", VIDEO_ID, "--cost", E("MAYA_SESSION_COST", "0")], timeout=60)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=20); ap.add_argument("--planted", default=""); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--beats", default="beats.json")
    a = ap.parse_args()
    Host(a).run(a.minutes)
