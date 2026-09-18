#!/usr/bin/env python3
"""
presence.py — the "alive" layer. Turns a correct answer into a human one. No GPU, no pod: pure text/timing.

Four organs, all from the behavior skills:
  1. EDGE      — persona polish: contractions, a pause after the name, one playful beat where it fits
  2. NOISE     — micro-imperfections: an occasional "mm", soft laugh, breath — capped so it never reads fake
  3. GAZE/CUE  — emits the gesture + gaze cue that SHOULD fire with this line (SHOW/POINT/WAVE/LISTEN/IDLE)
                 so whatever renderer we use (clip switch, managed avatar, or a future engine) gets it
  4. CALLBACK  — bonding memory on air: "welcome back, Dana", "you asked about texture earlier"

  from presence import Presence
  p = Presence(product_name="Vitamin C Serum")
  out = p.shape(say="Dana — it's 149 shekels live right now.", name="Dana", intent="purchase",
                returning=True, prior_topics=["texture"])
  out -> {"say": "...", "gesture": "POINT", "gaze": "camera", "noise": "mm", "callback": True}

Rules (enforced, not optional):
  · ≤1 noise token per answer, ≤1 per 3 answers overall
  · ≤1 playful beat per answer, never on medical/complaint intents
  · never adds facts — it only reshapes wording the brain already produced
  · callbacks only when memory actually has something
"""
from __future__ import annotations
import random, re, time
from typing import Optional

GESTURE_BY_INTENT = {"purchase": "POINT", "question": "SHOW", "greeting": "WAVE", "medical": "LISTEN", "other": "IDLE",
                     "pitch": "SHOW", "fill": "IDLE", "room": "WAVE", "batch": "SHOW"}
PRODUCT_WORDS = ("serum", "bottle", "drop", "cream", "product")
PRICE_WORDS = ("shekel", "price", "link", "below", "type me", "order", "buy")
NOISE = ["mm", "ha", "okay so", "right"]
PLAYFUL = {
    "purchase": ["Your future glow says thank you.", "Good call.", "That one moves fast."],
    "question": ["Good one.", "People ask me that all day.", "Classic question."],
    "greeting": ["Glad you're here.", "Perfect timing."],
}
BREATH = "…"


class Presence:
    def __init__(self, product_name: str = "", edge: float = 0.35, noise_every: int = 3, seed: Optional[int] = None):
        self.product = product_name
        self.edge = max(0.0, min(1.0, edge))       # chance of a playful beat where allowed
        self.noise_every = max(1, noise_every)     # at most one noise token per N answers
        self.rng = random.Random(seed)
        self._since_noise = 99
        self._said_playful = set()

    # ---------- public ----------
    def shape(self, say: str, name: str = "", intent: str = "other", returning: bool = False,
              prior_topics: Optional[list] = None, quiet_seconds: float = 0.0) -> dict:
        say = (say or "").strip()
        if not say:
            return {"say": "", "gesture": "IDLE", "gaze": "camera", "noise": None, "callback": False, "playful": None}
        first = (name or "").split(" ")[0].strip()
        out_noise = None
        callback = False

        # 1) name + pause (the name IS the engagement; a beat after it reads human)
        say = self._name_pause(say, first)

        # 2) callback (bonding memory) — only if we actually have something
        if first and returning:
            topic = (prior_topics or [None])[0]
            pre = f"Welcome back, {first}" + (f" — you asked about {topic} earlier. " if topic else " — good to see you. ")
            if not say.lower().startswith("welcome back"):
                rest = self._strip_leading_name(say, first).strip()
                rest = rest[0].upper() + rest[1:] if rest else rest
                say = pre + rest
                callback = True

        # 3) noise (micro-imperfection), rate-limited and never on medical
        self._since_noise += 1
        if intent not in ("medical", "purchase") and self._since_noise >= self.noise_every and self.rng.random() < 0.6:
            out_noise = self.rng.choice(NOISE)
            say = self._insert_noise(say, out_noise, first)
            self._since_noise = 0

        # 4) playful beat (edge), never on medical/complaint, never repeat the same line twice
        playful = None
        if intent in PLAYFUL and self.rng.random() < self.edge:
            pool = [p for p in PLAYFUL[intent] if p not in self._said_playful] or PLAYFUL[intent]
            playful = self.rng.choice(pool); self._said_playful.add(playful)
            say = say.rstrip() + " " + playful

        # 5) speakable numbers + contractions
        say = self.speakable(say)

        return {"say": say.strip(), "gesture": self.gesture_for(say, intent), "gaze": self.gaze_for(say, intent),
                "noise": out_noise, "callback": callback, "playful": playful}

    def gesture_for(self, text: str, intent: str) -> str:
        if intent == "medical":
            return "LISTEN"
        t = text.lower()
        if any(w in t for w in PRICE_WORDS):
            return "POINT"
        if any(w in t for w in PRODUCT_WORDS) or (self.product and self.product.lower() in t):
            return "SHOW"
        return GESTURE_BY_INTENT.get(intent, "IDLE")

    def gaze_for(self, text: str, intent: str) -> str:
        if intent == "medical":
            return "camera"
        t = text.lower()
        if any(w in t for w in PRODUCT_WORDS) or (self.product and self.product.lower() in t):
            return "product"          # glance at the product, then back — joint attention
        if intent in ("medical", "other") and "?" in text:
            return "camera"
        return "camera"

    # ---------- helpers ----------
    @staticmethod
    def _strip_leading_name(say: str, first: str) -> str:
        return re.sub(rf"^{re.escape(first)}\s*[—\-,:]\s*", "", say) if first else say

    def _name_pause(self, say: str, first: str) -> str:
        if not first:
            return say
        if first.lower() in say[:40].lower() and not say.lower().startswith(first.lower()):
            return say          # the name is already in the opening clause ("Honest answer, Lior —") — never say it twice
        if say.lower().startswith(first.lower()):
            return re.sub(rf"^{re.escape(first)}\s*[—\-,:]?\s*", f"{first} — ", say, count=1)
        return f"{first} — {say}"

    def _insert_noise(self, say: str, token: str, first: str) -> str:
        """After the name beat (or after a callback clause) — never at the very start, never before a number."""
        if first and say.startswith(f"{first} — "):
            head, rest = f"{first} — ", say[len(f"{first} — "):]
        elif " — " in say[:60]:
            i = say.index(" — ") + 3; head, rest = say[:i], say[i:]
        else:
            head, rest = "", say
        if re.match(r"^\W*\d", rest):      # don't put a filler right before a number
            return say
        rest = rest[0].lower() + rest[1:] if rest[:1].isupper() and not rest.startswith("I ") else rest
        return f"{head}{token}, {rest}"

    @staticmethod
    def speakable(text: str) -> str:
        """Numbers said the way a person says them; light contractions. Never changes the facts."""
        words = {"149": "one-forty-nine", "249": "two-forty-nine", "99": "ninety-nine"}
        def num(m):
            n = m.group(0)
            # already spoken right before it ("one-forty-nine — 149")? leave it alone — never say a number three times
            if n in words and words[n] in text:
                return n
            return f"{words[n]} — {n}" if n in words else n
        text = re.sub(r"\b\d{2,3}\b", num, text, count=1)
        for a, b in ((" it is ", " it's "), ("It is ", "It's "), (" that is ", " that's "), ("That is ", "That's "),
                     (" you will ", " you'll "), ("You will ", "You'll "), (" I will ", " I'll "),
                     (" do not ", " don't "), (" cannot ", " can't "), (" it will ", " it'll ")):
            text = text.replace(a, b)
        return text


if __name__ == "__main__":
    p = Presence(product_name="Vitamin C Serum", seed=7)
    cases = [("Dana — it is 149 shekels live right now. The link is below.", "Dana", "purchase", False, []),
             ("Tom — one drop every morning on clean skin, before your moisturizer.", "Tom", "question", False, []),
             ("Lior — I can't make medical claims, it's a cosmetic serum. A dermatologist is the right address.", "Lior", "medical", False, []),
             ("Dana — light, almost like water. It absorbs in seconds.", "Dana", "question", True, ["texture"]),
             ("Welcome in! Ask me anything about the serum.", "Noa", "greeting", False, [])]
    for say, name, intent, ret, topics in cases:
        o = p.shape(say, name, intent, ret, topics)
        print(f"[{o['gesture']:<6} gaze={o['gaze']:<7} noise={str(o['noise']):<6}] {o['say']}")
