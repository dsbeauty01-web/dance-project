#!/usr/bin/env python3
"""
room_awareness.py — she notices the room. Polls the Facebook live video every ROOM_POLL_SEC and returns spoken
lines for: viewers joining (delta), a burst of reactions/hearts, and milestones. Cheap, high "she's alive" effect.

  from room_awareness import Room; room = Room(video_id, token); line = room.tick()  → str | None
Dry mode (no FB): Room(None, None, dry=True) → simulated joins for QA.
Rules: max one room line per ROOM_MIN_GAP_SEC (default 45s), never while a viewer is being answered (caller decides),
       no numbers when small (<3 viewers) — "someone just joined" not "1 viewer".
"""
import os, random, time
import requests

E = os.environ.get
G = f"https://graph.facebook.com/{E('FB_API_VERSION', 'v21.0')}"


class Room:
    def __init__(self, video_id, token, dry=False):
        self.vid, self.tok, self.dry = video_id, token, dry
        self.poll_sec = int(E("ROOM_POLL_SEC", "30")); self.min_gap = int(E("ROOM_MIN_GAP_SEC", "45"))
        self.last_poll = 0.0; self.last_line = time.time()
        self.viewers = None; self.reactions = 0; self.peak = 0; self.milestones = set()
        self._dry_i = 0

    def _fetch(self):
        if self.dry:
            self._dry_i += 1
            sim = [(2, 0), (5, 1), (5, 6), (9, 7), (10, 12), (10, 12), (14, 15)]
            return sim[min(self._dry_i - 1, len(sim) - 1)]
        r = requests.get(f"{G}/{self.vid}", params={"fields": "live_views", "access_token": self.tok}, timeout=8).json()
        v = r.get("live_views")
        rc = requests.get(f"{G}/{self.vid}/reactions", params={"summary": "total_count", "limit": 1, "access_token": self.tok}, timeout=8).json()
        return (int(v) if v is not None else None, int((rc.get("summary") or {}).get("total_count", 0)))

    def tick(self):
        now = time.time()
        if now - self.last_poll < self.poll_sec:
            return None
        self.last_poll = now
        try:
            viewers, reactions = self._fetch()
        except Exception:
            return None
        line = None
        if viewers is not None:
            if self.viewers is not None:
                delta = viewers - self.viewers
                if delta >= 3:
                    line = random.choice([f"{delta} people just joined — welcome in! Ask me anything.", "Ooh, the room just got bigger — welcome, everyone. I'm Maya, an AI host."])
                elif delta >= 1 and viewers < 3:
                    line = "Someone just joined — welcome in! I'm Maya, ask me anything about the serum."
            for m in (10, 25, 50, 100):
                if viewers >= m and m not in self.milestones:
                    self.milestones.add(m); line = f"{m} of you here right now — thank you! Type ME if you want the link."
            self.viewers = viewers; self.peak = max(self.peak, viewers)
        if reactions - self.reactions >= 5:
            line = line or random.choice(["Thanks for the hearts! Love that.", "I see the reactions — thank you, you're the best room."])
        self.reactions = reactions
        if line and now - self.last_line >= self.min_gap:
            self.last_line = now
            return line
        return None

    def summary(self):
        return {"peak_viewers": self.peak, "reactions": self.reactions}


if __name__ == "__main__":
    os.environ["ROOM_POLL_SEC"] = "0"; os.environ["ROOM_MIN_GAP_SEC"] = "0"
    r = Room(None, None, dry=True)
    for _ in range(7):
        print(r.tick())
    print(r.summary())
