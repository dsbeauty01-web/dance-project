#!/usr/bin/env python3
"""
maya_lt.py — Maya on LiveTalking. The commercial host behavior, re-timed for the free edition's rules.

  python maya_lt.py --minutes 15                       # Facebook live (FB_VIDEO_ID + token in ~/.maya/host.env)
  python maya_lt.py --minutes 3 --planted planted.json  # unattended test with scheduled comments
  python maya_lt.py --dry --planted planted.json        # no engine, no FB — logic only

PER COMMENT (what a viewer sees):
  "hi maya"  → she WAVES (clip) → "Rafael — hi and welcome! Ask me anything about the serum."   (name-first, live voice)
  "how much" → she POINTS down → "Rafael — it's one-forty-nine, 149 shekels live right now…"  → text reply carries the link
  "show me"  → both hands open ("here it is") → the answer
  LLM question → she NODS (listening) while the brain thinks → gesture → answer
  medical    → no gesture, still, honest deflection
  join burst / hearts → room lines · quiet → presenter beats · polls/VIP → cocreate
GESTURE TIMING (free edition): clip is visible only while silent → we wait for silence, fire the clip, lead 0.6 s,
then speak; the silent state goes back to idle right after speech is sent. Never a gesture on a medical answer.
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, threading, time
import requests

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
for p in (os.path.expanduser("~/.maya/host.env"),):
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1); os.environ.setdefault(k, v.strip().strip('"'))
E = os.environ.get
from maya_host import CFG, classify            # noqa: E402  (filters, intents, config)
from presence import Presence                  # noqa: E402  (edge, noise, speakable numbers, gesture cue)
from cocreate import CoCreate                  # noqa: E402  (polls, VIP, shout-outs)
from room_awareness import Room                # noqa: E402  (joins, hearts)
from lt_client import LiveTalking              # noqa: E402

G = f"https://graph.facebook.com/{E('FB_API_VERSION', 'v21.0')}"
TOK, PAGE, VIDEO_ID = E("FB_PAGE_TOKEN", ""), E("FB_PAGE_ID", ""), E("FB_VIDEO_ID", "")
FILL_AFTER = int(E("MAYA_FILL_AFTER_SEC", "45")); REENTRY_MIN = int(E("MAYA_REENTRY_EVERY_MIN", "8"))
GESTURE_AT = {k: int(E(f"LT_AT_{k}", d)) for k, d in (("WAVE", "2"), ("POINT", "3"), ("SHOW", "4"), ("NOD", "5"), ("GOODBYE", "6"))}
VIP = re.compile(r"\b(vip|!ask|priority)\b", re.I)
SHOW_RX = re.compile(r"\b(show|see|look at|closer|close ?up|zoom|open the bag|open it)\b", re.I)
GREET_RX = re.compile(r"^\s*(hi|hello|hey|shalom|היי|שלום)\b", re.I)
METRICS = open(os.path.join(HERE, "metrics_lt.jsonl"), "a", encoding="utf-8")


def log(m):
    print(f"[maya_lt {time.strftime('%H:%M:%S')}] {m}", flush=True)


class FB:
    def __init__(self, dry): self.dry = dry; self.since = int(time.time()) - 20; self.seen = set()
    def poll(self):
        if self.dry or not (TOK and VIDEO_ID): return []
        r = requests.get(f"{G}/{VIDEO_ID}/comments", params={"fields": "id,from{name,id},message,created_time", "order": "chronological",
                         "filter": "stream", "since": self.since, "limit": 50, "access_token": TOK}, timeout=10).json()
        if "error" in r: raise RuntimeError(r["error"].get("message"))
        out = []
        for c in r.get("data", []):
            if c["id"] in self.seen or str((c.get("from") or {}).get("id")) == str(PAGE): continue
            self.seen.add(c["id"]); frm = c.get("from") or {}
            out.append({"id": c["id"], "name": frm.get("name") or "", "text": c.get("message", ""), "ts": time.time(), "source": "fb"})
        self.since = int(time.time()) - 5
        return out
    def reply(self, text):
        if self.dry or not (TOK and VIDEO_ID): log(f"[FB-REPLY-DRY] {text[:120]}"); return
        requests.post(f"{G}/{VIDEO_ID}/comments", data={"message": text[:900], "access_token": TOK}, timeout=10)


class Host:
    def __init__(self, a):
        self.dry = a.dry
        import brain_server; self.brain = brain_server
        self.lt = LiveTalking(dry=a.dry)
        self.fb = FB(a.dry)
        prod = self.brain.cat.product
        self.presence = Presence(product_name=prod.get("name", ""), edge=float(E("MAYA_EDGE", "0.35")))
        others = [p.strip() for p in E("MAYA_POLL_PRODUCTS", "").split(",") if p.strip()]
        self.cocreate = CoCreate(products=([prod.get("name", "")] + others) if others else [])
        self.room = Room(VIDEO_ID, TOK, dry=a.dry or not (VIDEO_ID and TOK))
        self.beats = json.load(open(os.path.join(HERE, a.beats), encoding="utf-8")) if os.path.exists(os.path.join(HERE, a.beats)) else []
        self.planted = json.load(open(a.planted, encoding="utf-8")) if a.planted else []
        self.buy_url = (prod.get("buy_url") or "").strip()
        self.t0 = time.time(); self.last_spoke = time.time(); self.last_beat = time.time(); self.beat_i = 0; self.last_reentry = time.time()
        self.seen_users = set(); self.last_user = {}; self.answers_min = []
        self.speaking_kind = "idle"   # what she is saying right now: answer | beat | opener | reentry | room | close
        self.stats = {"comments": 0, "answered": 0, "gestures": 0, "beats": 0, "room": 0, "cocreate": 0, "lat": []}
        self.lock = threading.Lock()

    # ---------- helpers ----------
    def say(self, text: str, gesture: str | None = None, kind: str = "answer"):
        """Wait for silence (so a gesture is visible), fire gesture, lead, speak, idle."""
        SCRIPT = ("beat", "opener", "reentry", "room", "poll_open", "poll_nudge", "type1")
        with self.lock:
            if kind in ("answer", "vip", "shoutout", "poll_update") and self.speaking_kind in SCRIPT and self.lt.is_speaking():
                self.lt.interrupt()            # a viewer never waits behind the sales script
            else:
                self.lt.wait_silent(max_sec=20)  # but one viewer never cuts another
            at = GESTURE_AT.get(gesture) if gesture else None
            self.lt.gesture_then_speak(at, text)
            if at: self.stats["gestures"] += 1
            self.speaking_kind = kind; self.last_spoke = time.time()
            log(f"SPEAK[{kind}{'+' + gesture if gesture else ''}] {text[:90]}")

    def gesture_for(self, text: str, intent: str, needs_llm: bool) -> str | None:
        if intent == "medical": return None
        if GREET_RX.search(text) or intent == "greeting": return "WAVE"
        if SHOW_RX.search(text): return "SHOW"
        if intent == "purchase" or re.search(r"\b(price|how much|link|buy|send me|order)\b", text, re.I): return "POINT"
        return "SHOW" if not needs_llm else None

    def _allowed(self, name):
        now = time.time(); self.answers_min = [t for t in self.answers_min if now - t < 60]
        return len(self.answers_min) < CFG.max_answers_per_min and now - self.last_user.get(name, 0) >= CFG.per_user_cooldown_sec

    def link_for(self, intent, text):
        if (intent == "purchase" or re.search(r"\b(link|buy|order|send me|dm me|checkout|me)\b", text or "", re.I)) and self.buy_url and not self.buy_url.upper().startswith("PLACEHOLDER"):
            return f"  👉 {self.buy_url}"
        return ""

    # ---------- one comment ----------
    def handle(self, c):
        name, text = (c.get("name") or "").strip(), (c.get("text") or "").strip()
        first = name.split()[0] if name else ""
        cls = classify(type("T", (), {"text": text})())
        if cls.get("drop"): log(f"dropped ({cls['reason']}): {name}: {text[:50]}"); return
        cc = self.cocreate.on_comment(name or "friend", text)
        if cc:
            self.say(cc["say"], "WAVE" if cc["kind"] in ("shoutout", "vip") else "POINT", kind=cc["kind"]); self.stats["cocreate"] += 1
            if cc["kind"] in ("shoutout", "poll_update"): return
        intent = cls["intent"]
        if not self._allowed(name) and intent != "purchase" and not VIP.search(text): log(f"rate-hold {name}"); return
        t_in = c["ts"]; needs_llm = intent != "medical" and self.brain.INSTANT.match(text) is None
        returning = name in self.seen_users; self.seen_users.add(name)
        if needs_llm and not self.dry:                       # listening beat while the brain thinks (she is silent → clip is visible)
            self.lt.wait_silent(10); self.lt.audiotype(GESTURE_AT["NOD"])
        say = self.brain.answer(f"{name}: {text}" if name else text, platform="facebook")
        shaped = self.presence.shape(say, name=first, intent=intent, returning=returning)
        say = shaped["say"]
        gesture = self.gesture_for(text, intent, needs_llm)
        self.say(say, gesture, kind="answer")
        lat = time.time() - t_in
        self.stats["answered"] += 1; self.stats["lat"].append(lat); self.stats["comments"] += 1
        self.answers_min.append(time.time()); self.last_user[name] = time.time()
        METRICS.write(json.dumps({"name": name, "text": text[:80], "intent": intent, "gesture": gesture, "latency": round(lat, 2), "say": say[:120]}, ensure_ascii=False) + "\n"); METRICS.flush()
        if c.get("source") == "fb":
            self.fb.reply(f"@{first} — {say}{self.link_for(intent, text)}" if first else f"{say}{self.link_for(intent, text)}")
        log(f"ANSWER {lat:.1f}s [{gesture or '-'}] {name}: {text[:40]!r}")

    # ---------- quiet-time behavior ----------
    def presenter(self):
        now = time.time()
        if not self.beats or now - self.last_spoke < FILL_AFTER or now - self.last_beat < FILL_AFTER: return
        if now - self.last_reentry > REENTRY_MIN * 60:
            self.say("Joined mid-way? Perfect timing — ask me anything in the chat.", "WAVE", kind="reentry"); self.last_reentry = now; self.last_beat = now; return
        pool = self.beats[1:] if len(self.beats) > 1 else self.beats
        b = pool[self.beat_i % len(pool)]; self.beat_i += 1
        shaped = self.presence.shape(b["text"], intent="pitch")
        self.say(shaped["say"], {"WAVE": "WAVE", "POINT": "POINT", "SHOW": "SHOW"}.get(b.get("gesture", ""), None), kind="beat")
        self.stats["beats"] += 1; self.last_beat = now

    def planted_due(self):
        out, el = [], (time.time() - self.t0) / 60
        for p in self.planted:
            if not p.get("_done") and el >= p["at_min"]:
                p["_done"] = True; out.append({"id": f"pl-{p['at_min']}", "name": p["name"], "text": p["text"], "ts": time.time(), "source": "planted"})
        return out

    def run(self, minutes):
        log(f"host up dry={self.dry} beats={len(self.beats)} planted={len(self.planted)} gestures={GESTURE_AT} video={VIDEO_ID or '(none)'}")
        if not self.dry and TOK and not VIDEO_ID: log("BLOCKED: token set but FB_VIDEO_ID empty — run fb_tool.py live current, re-source env"); sys.exit(2)
        if self.beats: self.say(self.beats[0]["text"], "WAVE", kind="opener")
        end = time.time() + minutes * 60
        while time.time() < end:
            try:
                for c in self.fb.poll() + self.planted_due(): self.handle(c)
                if time.time() - self.last_spoke > 20:
                    line = self.room.tick()
                    if line: self.say(line, "WAVE", kind="room"); self.stats["room"] += 1
                    cc = self.cocreate.tick()
                    if cc: self.say(cc["say"], "POINT", kind=cc["kind"]); self.stats["cocreate"] += 1
                self.presenter()
            except Exception as e:
                log(f"loop error: {e}"); time.sleep(3)
            time.sleep(1.5)
        self.finish()

    def finish(self):
        self.say("That's it for this round — thank you all. Link below, or type ME.", "GOODBYE", kind="close")
        lat = sorted(self.stats["lat"])
        summ = {**{k: v for k, v in self.stats.items() if k != "lat"}, "latency_median_s": round(lat[len(lat) // 2], 2) if lat else None,
                "latency_worst_s": round(lat[-1], 2) if lat else None, "minutes": round((time.time() - self.t0) / 60, 1)}
        json.dump(summ, open(os.path.join(HERE, "last_session_lt.json"), "w"), indent=2); self.lt.dump_timeline(os.path.join(HERE, "lt_timeline.jsonl"))
        log("SUMMARY " + json.dumps(summ))
        if not self.dry and E("FB_LIVE_VIDEO_ID"):
            subprocess.run([sys.executable, os.path.join(HERE, "fb_tool.py"), "live", "end", E("FB_LIVE_VIDEO_ID")], timeout=30)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--minutes", type=float, default=15); ap.add_argument("--planted", default="")
    ap.add_argument("--dry", action="store_true"); ap.add_argument("--beats", default="beats.json")
    Host(ap.parse_args()).run(ap.parse_args().minutes)
