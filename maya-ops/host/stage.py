#!/usr/bin/env python3
"""
stage.py — GESTURES ON DEMAND, without the engine.

The problem: QuickTalk can't switch her body mid-sentence, and stitching poses flickers. So she
sits still while a viewer asks "can I see it closer?" — which is the exact moment a real host moves.

The fix: don't move her body, move the SHOT. A viewer asks to see something → she says yes out
loud → the director cuts to the product clip while her voice keeps talking → back to her. That is
what a human host does, it needs no avatar switching, and every piece already exists
(director.py + the serum cutaways).

  from stage import Stage
  st = Stage(product="Vitamin C Serum", has_clips={"hero","apply","examine"})
  cue = st.read("can i see the bottle closer?")
  # -> {"ack": "Sure — look at this.", "scene": "CUTAWAY", "clip": "hero", "seconds": 9,
  #     "gesture": "SHOW", "kind": "show_product"}

Rules baked in (learned the hard way):
  · she SPEAKS the acknowledgment first, then the shot changes — a silent cut reads as a glitch
  · never cut away for longer than `seconds`; the director always returns to HOST
  · never cut while she is mid-answer to someone else (the host checks `can_cut`)
  · never cut twice within COOLDOWN — rapid cutting looks broken, not lively
  · if the clip doesn't exist, the cue degrades to a spoken answer + gesture, never a black frame
"""
from __future__ import annotations
import os, random, re, time
from typing import Optional

E = os.environ.get
COOLDOWN = int(E("STAGE_COOLDOWN_SEC", "25"))

# viewer intent -> what a host would actually do on camera
CUES = [
    ("show_product", r"\b(show|see|look at|view)\b.{0,18}\b(it|this|product|bottle|serum|cream|pack)\b|\b(can i see|show me|closer|close ?up|zoom)\b",
     ["Sure — look at this.", "Of course, here it is up close.", "Yes — take a look."], "CUTAWAY", "hero", 9, "SHOW"),
    ("show_texture", r"\b(texture|how does it (feel|look)|absorb|sticky|greasy|thick|runny|watery|consistency)\b",
     ["Here's the texture — watch.", "Let me show you how it goes on.", "Look at how it absorbs."], "CUTAWAY", "apply", 10, "SHOW"),
    ("show_usage", r"\b(how (do|to) (i )?(use|apply)|routine|how much do i use|one drop|application)\b",
     ["Easiest if I show you.", "Here's exactly how."], "PIP", "apply", 10, "SHOW"),
    ("show_size", r"\b(how (big|large|small)|size|ml\b|volume|how long (does it )?last)\b",
     ["Here it is in hand, so you can judge the size.", "Let me show you the size."], "PIP", "hero", 7, "SHOW"),
    ("show_label", r"\b(ingredient|what'?s in it|label|percent|concentration|formula)\b",
     ["Let me show you the label.", "Here's what's in it."], "CUTAWAY", "examine", 8, "SHOW"),
    ("show_price", r"\b(price|how much|cost|discount|deal)\b",
     ["Here's today's price on screen.", "Putting the price up for you."], "BANNER", "", 12, "POINT"),
    ("show_link", r"\b(link|where (do|can) i (buy|order)|checkout|buy now|order|send me|dm me)\b",
     ["Link's going up now.", "Here's where to get it."], "BANNER", "", 12, "POINT"),
]
COMPILED = [(k, re.compile(rx, re.I), acks, scene, clip, secs, gest) for k, rx, acks, scene, clip, secs, gest in CUES]

# clip fallbacks: if the ideal clip is missing, use the next best rather than a black frame
FALLBACK = {"hero": ["examine", "apply"], "apply": ["examine", "hero"], "examine": ["hero", "apply"]}


class Stage:
    def __init__(self, product: str = "", has_clips: Optional[set] = None, cooldown: int = COOLDOWN):
        self.product = product
        self.clips = set(has_clips or [])
        self.cooldown = cooldown
        self.last_cut = 0.0
        self.last_kind = ""
        self.counts: dict = {}
        self.rng = random.Random()

    # ---------- the only public call ----------
    def read(self, text: str, can_cut: bool = True) -> Optional[dict]:
        """Viewer text -> a stage cue, or None if this comment doesn't call for a shot change."""
        t = (text or "").strip()
        if not t or len(t) > 200:
            return None
        for kind, rx, acks, scene, clip, secs, gest in COMPILED:
            if not rx.search(t):
                continue
            now = time.time()
            if not can_cut:
                return None
            if now - self.last_cut < self.cooldown and kind == self.last_kind:
                return None                       # asked twice in a row: answer, don't re-cut
            resolved = self._resolve(clip) if clip else ""
            if clip and not resolved:
                # no footage for this: still give the gesture + let her answer normally
                return {"ack": None, "scene": None, "clip": None, "seconds": 0, "gesture": gest,
                        "kind": kind, "note": f"no clip for '{clip}' — spoken answer only"}
            self.last_cut, self.last_kind = now, kind
            self.counts[kind] = self.counts.get(kind, 0) + 1
            return {"ack": self.rng.choice(acks), "scene": scene, "clip": resolved,
                    "seconds": secs, "gesture": gest, "kind": kind}
        return None

    def _resolve(self, clip: str) -> str:
        if clip in self.clips:
            return clip
        for alt in FALLBACK.get(clip, []):
            if alt in self.clips:
                return alt
        return ""

    def stats(self) -> dict:
        return dict(self.counts)


if __name__ == "__main__":
    st = Stage(product="Vitamin C Serum", has_clips={"hero", "apply"}, cooldown=0)
    probes = [
        "can i see the bottle closer?", "show me the serum", "how does it feel on the skin?",
        "how do i use it", "how big is it?", "whats in it", "how much is it?",
        "send me the link", "hi maya", "will it cure my acne?", "do you ship to usa",
    ]
    for p in probes:
        c = st.read(p)
        if c and c.get("scene"):
            print(f"  {p:<32} -> say {c['ack']!r} then {c['scene']}/{c['clip']} {c['seconds']}s [{c['gesture']}]")
        elif c:
            print(f"  {p:<32} -> {c['gesture']} only ({c['note']})")
        else:
            print(f"  {p:<32} -> (no shot change — normal answer)")
