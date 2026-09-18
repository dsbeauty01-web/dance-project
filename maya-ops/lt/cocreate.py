#!/usr/bin/env python3
"""
cocreate.py — viewers STEER the stream. The research's #1 conversion mechanic (paid/priority steering converts
1.59% vs 1.18%/0.83%), implemented without any GPU: polls, VIP questions, type-1 prompts, shout-outs, milestones.

  from cocreate import CoCreate
  cc = CoCreate(products=["Vitamin C Serum", "Night Cream"])
  cc.on_comment(name, text)        -> dict|None   (vote counted / VIP accepted / keyword hit → a line to say)
  cc.tick()                        -> dict|None   (time to open a poll, close one, or nudge)
  cc.state()                       -> current poll + tallies for the on-screen overlay

Mechanics
  POLL       every POLL_EVERY_MIN: "type 1 for X, 2 for Y" → tally → announce winner → next product follows the vote
  TYPE-1     lightweight engagement prompt when chat is quiet ("type 1 if you've used vitamin C before")
  VIP        keyword VIP/!ask → that question jumps the queue (priority 0) and gets a named shout-out
  SHOUTOUT   first-time commenter, or someone who voted → named thank-you (cheap, high bonding)
  MILESTONE  10/25/50 votes or viewers → announce + CTA
All lines are catalog-neutral (no invented facts) and rate-limited so she never spams.
"""
from __future__ import annotations
import os, re, time
from typing import Optional

E = os.environ.get
VIP_RX = re.compile(r"\b(vip|!ask|priority)\b", re.I)
VOTE_RX = re.compile(r"^\s*([12])\s*[!.]*\s*$")


class CoCreate:
    def __init__(self, products: Optional[list] = None, poll_every_min: int = 8, poll_secs: int = 90):
        self.products = products or []
        self.poll_every = int(E("COCREATE_POLL_EVERY_MIN", str(poll_every_min))) * 60
        self.poll_secs = int(E("COCREATE_POLL_SECS", str(poll_secs)))
        self.started = time.time()
        # first poll opens after a warm-up (or immediately when poll_every is 0, e.g. tests)
        self.last_poll_end = time.time() - self.poll_every + (0 if self.poll_every == 0 else 120)
        self.poll = None            # {"opened", "a", "b", "votes": {"1": set(), "2": set()}}
        self.seen_names = set()
        self.voted_names = set()
        self.vip_count = 0
        self.milestones = set()
        self.last_line = 0.0
        self.min_gap = int(E("COCREATE_MIN_GAP_SEC", "25"))

    # ---------- comments ----------
    def on_comment(self, name: str, text: str) -> Optional[dict]:
        first = (name or "friend").split(" ")[0]
        t = (text or "").strip()
        # VIP jumps the queue
        if VIP_RX.search(t):
            self.vip_count += 1
            return self._line(f"{first} — VIP question, you're first in line.", kind="vip", priority=0)
        # poll vote
        m = VOTE_RX.match(t)
        if m and self.poll:
            self.poll["votes"][m.group(1)].add(first)
            n = len(self.poll["votes"]["1"]) + len(self.poll["votes"]["2"])
            if n in (5, 10, 25) and n not in self.milestones:
                self.milestones.add(n)
                return self._line(f"{n} votes in — keep them coming. Right now it's {self._tally()}.", kind="poll_update")
            if first not in self.voted_names:
                self.voted_names.add(first); self.seen_names.add(first)
                return self._line(f"Got it, {first}. Thanks for voting.", kind="shoutout")
            return None
        # first time this person speaks
        if first not in self.seen_names:
            self.seen_names.add(first)
            return None   # the host's own greeting handles this; don't double-speak
        return None

    # ---------- timed ----------
    def tick(self) -> Optional[dict]:
        now = time.time()
        if self.poll:
            if now - self.poll["opened"] >= self.poll_secs:
                return self._close_poll()
            if now - self.poll["opened"] > self.poll_secs / 2 and not self.poll.get("nudged"):
                self.poll["nudged"] = True
                return self._line(f"Still open — {self._prompt()}", kind="poll_nudge")
            return None
        if len(self.products) >= 2 and now - self.last_poll_end >= self.poll_every:
            return self._open_poll()
        return None

    # ---------- polls ----------
    def _open_poll(self) -> dict:
        a, b = self.products[0], self.products[1 % len(self.products)]
        self.poll = {"opened": time.time(), "a": a, "b": b, "votes": {"1": set(), "2": set()}}
        self.milestones.clear()
        return self._line(f"Your turn to steer: {self._prompt()}", kind="poll_open", force=True)

    def _close_poll(self) -> dict:
        p = self.poll; self.poll = None; self.last_poll_end = time.time()
        v1, v2 = len(p["votes"]["1"]), len(p["votes"]["2"])
        if v1 == v2 == 0:
            return self._line("No votes this round — I'll pick: we stay on this one.", kind="poll_close", force=True)
        winner = p["a"] if v1 >= v2 else p["b"]
        voters = ", ".join(sorted(p["votes"]["1" if v1 >= v2 else "2"])[:3])
        line = f"You voted: {winner} wins, {max(v1, v2)} to {min(v1, v2)}." + (f" Thanks {voters}." if voters else "")
        return self._line(line, kind="poll_close", force=True, winner=winner)

    def _prompt(self) -> str:
        return f"type 1 for {self.poll['a']}, 2 for {self.poll['b']}." if self.poll else ""

    def _tally(self) -> str:
        if not self.poll:
            return ""
        return f"{len(self.poll['votes']['1'])} for {self.poll['a']}, {len(self.poll['votes']['2'])} for {self.poll['b']}"

    # ---------- quiet-chat engagement ----------
    def quiet_prompt(self) -> dict:
        return self._line("Type 1 in the chat if you've used vitamin C before — I'll tailor what I show next.", kind="type1")

    def state(self) -> dict:
        if not self.poll:
            return {"poll": None, "vip_count": self.vip_count, "voters": len(self.seen_names)}
        return {"poll": {"a": self.poll["a"], "b": self.poll["b"], "v1": len(self.poll["votes"]["1"]),
                         "v2": len(self.poll["votes"]["2"]), "seconds_left": max(0, int(self.poll_secs - (time.time() - self.poll["opened"])))},
                "vip_count": self.vip_count, "voters": len(self.seen_names)}

    def _line(self, text: str, kind: str, priority: int = 4, force: bool = False, **extra) -> Optional[dict]:
        now = time.time()
        if not force and now - self.last_line < self.min_gap:
            return None
        self.last_line = now
        return {"say": text, "kind": kind, "priority": priority, **extra}


if __name__ == "__main__":
    os.environ["COCREATE_POLL_EVERY_MIN"] = "0"; os.environ["COCREATE_POLL_SECS"] = "2"; os.environ["COCREATE_MIN_GAP_SEC"] = "0"
    cc = CoCreate(products=["Vitamin C Serum", "Night Cream"])
    print(cc.tick())
    for n, t in [("Dana Levi", "1"), ("Tom Cohen", "2"), ("Lior Ben", "1"), ("Noa Katz", "VIP does it suit oily skin?"), ("Sara Gal", "1"), ("Yossi Mor", "1")]:
        r = cc.on_comment(n, t)
        if r:
            print(f"  [{r['kind']}] {r['say']}")
    print("state:", cc.state())
    time.sleep(2.1); print(cc.tick())
